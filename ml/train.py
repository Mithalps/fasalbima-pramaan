"""
train.py
========
Trains a MobileNetV2-based plant disease classifier on the
Healthy / Powdery / Rust dataset.

Usage:
    python train.py

All hyperparameters live in config.py -- this script requires no
command-line arguments and no edits to run out of the box, provided
your dataset sits at ml/dataset/{Train,Validation,Test}/<class>/.
"""

import time

import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from tqdm import tqdm

import config
import utils


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #

def build_transforms():
    """Builds the training and validation/test image transforms."""
    imagenet_mean = [0.485, 0.456, 0.406]
    imagenet_std = [0.229, 0.224, 0.225]

    train_transform = transforms.Compose([
        transforms.Resize(config.RESIZE_SIZE),
        transforms.RandomResizedCrop(config.IMAGE_SIZE),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),
        transforms.ToTensor(),
        transforms.Normalize(mean=imagenet_mean, std=imagenet_std),
    ])

    eval_transform = transforms.Compose([
        transforms.Resize(config.RESIZE_SIZE),
        transforms.CenterCrop(config.IMAGE_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=imagenet_mean, std=imagenet_std),
    ])

    return train_transform, eval_transform


def build_dataloaders(logger):
    """Builds ImageFolder datasets + DataLoaders for train and validation splits."""
    train_transform, eval_transform = build_transforms()

    train_dataset = datasets.ImageFolder(config.TRAIN_DIR, transform=train_transform)
    val_dataset = datasets.ImageFolder(config.VALIDATION_DIR, transform=eval_transform)

    # ImageFolder assigns class indices alphabetically -> class_to_idx is authoritative
    class_names = [cls for cls, _idx in sorted(train_dataset.class_to_idx.items(), key=lambda kv: kv[1])]

    logger.info(f"Detected {len(class_names)} classes: {class_names}")
    print("\nDetected classes (in index order):")
    for name in class_names:
        print(f"  - {name}")
    print()

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.BATCH_SIZE,
        shuffle=True,
        num_workers=config.NUM_WORKERS,
        pin_memory=config.PIN_MEMORY,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.BATCH_SIZE,
        shuffle=False,
        num_workers=config.NUM_WORKERS,
        pin_memory=config.PIN_MEMORY,
    )

    return train_loader, val_loader, class_names


# --------------------------------------------------------------------------- #
# One epoch of training / validation
# --------------------------------------------------------------------------- #

def run_epoch(model, loader, criterion, optimizer, device, train: bool, epoch_num: int, total_epochs: int):
    """Runs a single training or validation epoch. Returns (avg_loss, accuracy_pct)."""
    model.train() if train else model.eval()

    running_loss = 0.0
    running_correct = 0
    total_samples = 0

    phase = "Train" if train else "Val  "
    pbar = tqdm(loader, desc=f"Epoch {epoch_num}/{total_epochs} [{phase}]", unit="batch", leave=False)

    torch.set_grad_enabled(train)
    for inputs, labels in pbar:
        inputs = inputs.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        if train:
            optimizer.zero_grad()

        outputs = model(inputs)
        loss = criterion(outputs, labels)

        if train:
            loss.backward()
            optimizer.step()

        batch_size = inputs.size(0)
        running_loss += loss.item() * batch_size
        preds = torch.argmax(outputs, dim=1)
        running_correct += torch.sum(preds == labels).item()
        total_samples += batch_size

        pbar.set_postfix(loss=f"{loss.item():.4f}")

    avg_loss = running_loss / total_samples
    accuracy = 100.0 * running_correct / total_samples
    return avg_loss, accuracy


# --------------------------------------------------------------------------- #
# Main training routine
# --------------------------------------------------------------------------- #

def main():
    utils.create_output_dirs()
    utils.set_seed(config.SEED)
    logger = utils.setup_logger("train", config.TRAIN_LOG_FILE)

    logger.info("=" * 70)
    logger.info("FasalBima / Plant Disease Classifier - Training started")
    logger.info("=" * 70)

    device = config.DEVICE
    print(f"Using device: {device}")
    logger.info(f"Using device: {device}")
    if device.type == "cuda":
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")

    # ---- Data ----
    train_loader, val_loader, class_names = build_dataloaders(logger)
    utils.save_json(class_names, config.CLASS_NAMES_PATH)
    logger.info(f"Saved class names to {config.CLASS_NAMES_PATH}")

    num_classes = len(class_names)
    if num_classes != config.NUM_CLASSES:
        logger.info(
            f"NOTE: config.NUM_CLASSES={config.NUM_CLASSES} but {num_classes} classes "
            f"were detected in the dataset. Using the detected value ({num_classes})."
        )

    # ---- Model ----
    model = utils.build_model(num_classes=num_classes)
    model = model.to(device)
    logger.info(f"Model: {config.MODEL_NAME} (pretrained={config.PRETRAINED}, "
                f"frozen_features={config.FREEZE_FEATURE_EXTRACTOR})")

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Trainable parameters: {trainable_params:,} / {total_params:,} total")

    # ---- Loss / Optimizer / Scheduler / Early stopping ----
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=config.LEARNING_RATE,
        weight_decay=config.WEIGHT_DECAY,
    )
    scheduler = ReduceLROnPlateau(
        optimizer,
        mode=config.SCHEDULER_MODE,
        factor=config.SCHEDULER_FACTOR,
        patience=config.SCHEDULER_PATIENCE,
        min_lr=config.SCHEDULER_MIN_LR,
    )
    early_stopping = utils.EarlyStopping(
        patience=config.EARLY_STOPPING_PATIENCE,
        min_delta=config.EARLY_STOPPING_MIN_DELTA,
        logger=logger,
    )

    # ---- Training loop ----
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": [], "lr": []}
    best_val_loss = float("inf")

    start_time = time.time()

    for epoch in range(1, config.EPOCHS + 1):
        epoch_start = time.time()

        train_loss, train_acc = run_epoch(
            model, train_loader, criterion, optimizer, device,
            train=True, epoch_num=epoch, total_epochs=config.EPOCHS,
        )
        val_loss, val_acc = run_epoch(
            model, val_loader, criterion, optimizer, device,
            train=False, epoch_num=epoch, total_epochs=config.EPOCHS,
        )

        current_lr = optimizer.param_groups[0]["lr"]

        # Step scheduler on validation loss
        scheduler.step(val_loss)

        epoch_time = time.time() - epoch_start

        # ---- Print + log metrics ----
        summary = (
            f"Epoch {epoch:03d}/{config.EPOCHS} | "
            f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}% | "
            f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}% | "
            f"LR: {current_lr:.2e} | Time: {epoch_time:.1f}s"
        )
        print(summary)
        logger.info(summary)

        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        history["lr"].append(current_lr)

        # ---- Checkpointing ----
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": val_loss,
                "val_acc": val_acc,
                "class_names": class_names,
            },
            config.LAST_MODEL_PATH,
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_loss": val_loss,
                    "val_acc": val_acc,
                    "class_names": class_names,
                },
                config.BEST_MODEL_PATH,
            )
            logger.info(f"New best model saved (val_loss={val_loss:.4f}) -> {config.BEST_MODEL_PATH}")

        # Save history every epoch so progress isn't lost on a crash
        utils.save_json(history, config.HISTORY_PATH)

        # ---- Early stopping ----
        early_stopping(val_loss)
        if early_stopping.early_stop:
            logger.info(f"Early stopping triggered at epoch {epoch}.")
            print(f"Early stopping triggered at epoch {epoch}.")
            break

    total_time = time.time() - start_time
    logger.info(f"Training complete in {total_time / 60:.1f} minutes.")
    print(f"\nTraining complete in {total_time / 60:.1f} minutes.")

    # ---- Plots ----
    utils.plot_training_curves(history, config.PLOTS_DIR)
    logger.info(f"Saved accuracy.png and loss.png to {config.PLOTS_DIR}")

    print(f"\nBest model:  {config.BEST_MODEL_PATH}")
    print(f"Last model:  {config.LAST_MODEL_PATH}")
    print(f"Class names: {config.CLASS_NAMES_PATH}")
    print(f"History:     {config.HISTORY_PATH}")
    print(f"Log file:    {config.TRAIN_LOG_FILE}")
    print("\nRun 'python evaluate.py' next to evaluate on the Test set.")


if __name__ == "__main__":
    main()
