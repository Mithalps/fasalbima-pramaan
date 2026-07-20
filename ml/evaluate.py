"""
evaluate.py
===========
Evaluates the trained MobileNetV2 model (outputs/checkpoints/best_model.pth)
on the Test dataset and generates:
    - Confusion matrix (plots/confusion_matrix.png)
    - Classification report (precision, recall, f1-score per class)
    - Overall accuracy

Usage:
    python evaluate.py
"""

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from tqdm import tqdm

import config
import utils


def build_eval_transform():
    imagenet_mean = [0.485, 0.456, 0.406]
    imagenet_std = [0.229, 0.224, 0.225]
    return transforms.Compose([
        transforms.Resize(config.RESIZE_SIZE),
        transforms.CenterCrop(config.IMAGE_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=imagenet_mean, std=imagenet_std),
    ])


def main():
    utils.create_output_dirs()
    logger = utils.setup_logger("evaluate", config.EVAL_LOG_FILE)

    device = config.DEVICE
    print(f"Using device: {device}")
    logger.info(f"Using device: {device}")

    # ---- Load class names (saved during training) ----
    class_names = utils.load_json(config.CLASS_NAMES_PATH)
    logger.info(f"Loaded {len(class_names)} class names: {class_names}")
    print("\nClasses:")
    for name in class_names:
        print(f"  - {name}")

    # ---- Test dataset ----
    eval_transform = build_eval_transform()
    test_dataset = datasets.ImageFolder(config.TEST_DIR, transform=eval_transform)

    # Sanity check: ImageFolder's own class order must match the saved class_names
    detected_order = [cls for cls, _idx in sorted(test_dataset.class_to_idx.items(), key=lambda kv: kv[1])]
    if detected_order != class_names:
        logger.info(
            "WARNING: Test set class order differs from saved class_names.json "
            f"(test={detected_order}, saved={class_names}). Using saved order for reporting."
        )

    test_loader = DataLoader(
        test_dataset,
        batch_size=config.BATCH_SIZE,
        shuffle=False,
        num_workers=config.NUM_WORKERS,
        pin_memory=config.PIN_MEMORY,
    )
    logger.info(f"Test set size: {len(test_dataset)} images")

    # ---- Load model + best checkpoint ----
    model = utils.build_model(num_classes=len(class_names))
    checkpoint = torch.load(config.BEST_MODEL_PATH, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(device)
    model.eval()
    logger.info(f"Loaded checkpoint from {config.BEST_MODEL_PATH} "
                f"(epoch={checkpoint.get('epoch')}, val_loss={checkpoint.get('val_loss'):.4f})")

    # ---- Inference ----
    criterion = nn.CrossEntropyLoss()
    all_preds, all_labels = [], []
    running_loss = 0.0

    with torch.no_grad():
        for inputs, labels in tqdm(test_loader, desc="Evaluating on Test set", unit="batch"):
            inputs = inputs.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)

            outputs = model(inputs)
            loss = criterion(outputs, labels)
            running_loss += loss.item() * inputs.size(0)

            preds = torch.argmax(outputs, dim=1)
            all_preds.extend(preds.cpu().numpy().tolist())
            all_labels.extend(labels.cpu().numpy().tolist())

    test_loss = running_loss / len(test_dataset)
    test_acc = accuracy_score(all_labels, all_preds) * 100.0

    # ---- Confusion matrix ----
    cm = confusion_matrix(all_labels, all_preds, labels=list(range(len(class_names))))
    utils.plot_confusion_matrix(cm, class_names, save_path=f"{config.PLOTS_DIR}/confusion_matrix.png")
    logger.info(f"Saved confusion matrix to {config.PLOTS_DIR}/confusion_matrix.png")

    # ---- Classification report ----
    report_str = classification_report(
        all_labels, all_preds, target_names=class_names, labels=list(range(len(class_names))),
        digits=4, zero_division=0,
    )
    report_dict = classification_report(
        all_labels, all_preds, target_names=class_names, labels=list(range(len(class_names))),
        digits=4, output_dict=True, zero_division=0,
    )

    # ---- Print + log everything ----
    print("\n" + "=" * 70)
    print(" TEST SET EVALUATION")
    print("=" * 70)
    print(f" Test Loss:     {test_loss:.4f}")
    print(f" Test Accuracy: {test_acc:.2f}%")
    print("-" * 70)
    print(" Confusion Matrix (rows = true label, cols = predicted label)")
    print(f" Classes: {class_names}")
    print(cm)
    print("-" * 70)
    print(" Classification Report")
    print(report_str)
    print("=" * 70)

    logger.info(f"Test Loss: {test_loss:.4f} | Test Accuracy: {test_acc:.2f}%")
    logger.info(f"Confusion Matrix:\n{cm}")
    logger.info(f"Classification Report:\n{report_str}")

    # ---- Save classification report + summary to disk ----
    with open(config.CLASSIFICATION_REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("TEST SET EVALUATION\n")
        f.write("=" * 70 + "\n")
        f.write(f"Test Loss: {test_loss:.4f}\n")
        f.write(f"Test Accuracy: {test_acc:.2f}%\n\n")
        f.write("Confusion Matrix (rows = true label, cols = predicted label)\n")
        f.write(f"Classes: {class_names}\n")
        f.write(np.array2string(cm) + "\n\n")
        f.write("Classification Report\n")
        f.write(report_str + "\n")

    utils.save_json(
        {
            "test_loss": test_loss,
            "test_accuracy": test_acc,
            "confusion_matrix": cm.tolist(),
            "class_names": class_names,
            "classification_report": report_dict,
        },
        f"{config.LOGS_DIR}/test_results.json",
    )

    print(f"\nSaved: {config.CLASSIFICATION_REPORT_PATH}")
    print(f"Saved: {config.LOGS_DIR}/test_results.json")
    print(f"Saved: {config.PLOTS_DIR}/confusion_matrix.png")


if __name__ == "__main__":
    main()
