"""
train.py
========
Trains an EfficientNetB0-based crop-damage classifier for FasalBima
Pramaan on the Healthy / Flood Damage / Drought Stress / Pest Attack
dataset.

Usage:
    python train.py

All hyperparameters live in config.py -- this script requires no
command-line arguments and no edits to run out of the box, provided
your dataset sits at ml/dataset/{train,val}/<class>/.

Training strategy (two phases):
    Phase 1 -- frozen backbone warmup: only the classification head
        trains, Adam @ LEARNING_RATE, up to EPOCHS with EarlyStopping.
    Phase 2 -- fine-tuning: the best phase-1 checkpoint is reloaded,
        the top FT_UNFREEZE_LAYERS backbone layers are unfrozen
        (BatchNorm layers stay frozen), and training continues for
        FT_EPOCHS at the much lower FT_LEARNING_RATE.
    Whichever checkpoint (from either phase) has the best val_loss is
    what ends up saved at BEST_MODEL_PATH.

After training: evaluates on the validation set (confusion matrix +
classification report), exports a SavedModel for deployment, and
writes labels.json for inference.py to consume.

Replaces the previous PyTorch/MobileNetV2 PlantVillage
(Healthy/Powdery/Rust) training script.
"""

import time

import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import (
    EarlyStopping,
    ReduceLROnPlateau,
    ModelCheckpoint,
)

import config
import utils
import evaluation


# --------------------------------------------------------------------------- #
# Data (online augmentation only -- no offline duplication of image files)
# --------------------------------------------------------------------------- #

def build_generators(logger):
    """Builds train/val ImageDataGenerators + directory iterators."""
    train_datagen = ImageDataGenerator(
        rotation_range=config.AUGMENTATION["rotation_range"],
        zoom_range=config.AUGMENTATION["zoom_range"],
        horizontal_flip=config.AUGMENTATION["horizontal_flip"],
        brightness_range=config.AUGMENTATION["brightness_range"],
        width_shift_range=config.AUGMENTATION["width_shift_range"],
        height_shift_range=config.AUGMENTATION["height_shift_range"],
        fill_mode="nearest",
    )
    # Validation data: no augmentation, only rescale.
    val_datagen = ImageDataGenerator()

    train_gen = train_datagen.flow_from_directory(
        config.TRAIN_DIR,
        target_size=(config.IMAGE_SIZE, config.IMAGE_SIZE),
        batch_size=config.BATCH_SIZE,
        class_mode="categorical",
        classes=config.CLASS_FOLDER_NAMES,
        shuffle=True,
        seed=config.SEED,
    )
    val_gen = val_datagen.flow_from_directory(
        config.VALIDATION_DIR,
        target_size=(config.IMAGE_SIZE, config.IMAGE_SIZE),
        batch_size=config.BATCH_SIZE,
        class_mode="categorical",
        classes=config.CLASS_FOLDER_NAMES,
        shuffle=False,
    )

    # class_indices maps folder name -> index; must match config order.
    class_names = [None] * len(train_gen.class_indices)
    for folder_name, idx in train_gen.class_indices.items():
        class_names[idx] = folder_name

    logger.info(f"Detected classes (index order): {class_names}")
    print("\nDetected classes (in index order):")
    for name in class_names:
        print(f"  - {name}  ->  {config.CLASS_DISPLAY_NAMES.get(name, name)}")
    print()

    return train_gen, val_gen, class_names


def build_callbacks(monitor_path: str, initial_best: float = None):
    """
    Builds the EarlyStopping / ReduceLROnPlateau / ModelCheckpoint trio.

    `initial_best` seeds ModelCheckpoint's notion of "best so far" (via
    initial_value_threshold). This matters for phase 2: without it, a
    fresh ModelCheckpoint would start comparing from scratch and could
    overwrite a genuinely better phase-1 checkpoint with a worse
    phase-2 epoch, since it wouldn't know phase 1's best val_loss.
    """
    checkpoint_kwargs = dict(
        filepath=monitor_path,
        monitor=config.ES_MONITOR,
        save_best_only=True,
        verbose=1,
    )
    if initial_best is not None:
        checkpoint_kwargs["initial_value_threshold"] = initial_best

    return [
        EarlyStopping(
            monitor=config.ES_MONITOR,
            patience=config.ES_PATIENCE,
            min_delta=config.ES_MIN_DELTA,
            restore_best_weights=True,
            verbose=1,
        ),
        ReduceLROnPlateau(
            monitor=config.RLR_MONITOR,
            factor=config.RLR_FACTOR,
            patience=config.RLR_PATIENCE,
            min_lr=config.RLR_MIN_LR,
            verbose=1,
        ),
        ModelCheckpoint(**checkpoint_kwargs),
    ]


# --------------------------------------------------------------------------- #
# Main training routine
# --------------------------------------------------------------------------- #

def main():
    utils.create_output_dirs()
    utils.set_seed(config.SEED)
    logger = utils.setup_logger("train", config.TRAIN_LOG_FILE)

    logger.info("=" * 70)
    logger.info("FasalBima Pramaan - Crop Damage Classifier - Training started")
    logger.info("=" * 70)

    gpus = tf.config.list_physical_devices("GPU")
    device_msg = f"Using device: {'GPU' if gpus else 'CPU'} ({len(gpus)} GPU(s) found)"
    print(device_msg)
    logger.info(device_msg)

    # ---- Data ----
    train_gen, val_gen, class_names = build_generators(logger)
    utils.save_json(class_names, config.CLASS_NAMES_PATH)
    logger.info(f"Saved class names to {config.CLASS_NAMES_PATH}")

    display_names = [config.CLASS_DISPLAY_NAMES.get(n, n) for n in class_names]

    # Class weights: the dataset is imbalanced (23-33 images per class),
    # so under-represented classes get proportionally more weight in the loss.
    class_weights = utils.compute_class_weights(train_gen, logger=logger)

    # ---- Model (phase 1: frozen backbone) ----
    model, weights_used = utils.build_model(
        num_classes=len(class_names), logger=logger,
    )
    logger.info(f"Backbone: EfficientNetB0 (weights={weights_used}, "
                f"frozen_base={config.FREEZE_BASE})")

    model.compile(
        optimizer=Adam(learning_rate=config.LEARNING_RATE),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.summary(print_fn=lambda line: logger.info(line))

    callbacks_p1 = build_callbacks(config.BEST_MODEL_PATH)

    # ---- Phase 1: train classification head only ----
    start_time = time.time()
    history_p1 = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=config.EPOCHS,
        callbacks=callbacks_p1,
        class_weight=class_weights,
        verbose=1,
    )
    phase1_time = time.time() - start_time
    logger.info(f"Phase 1 (frozen backbone) complete in {phase1_time / 60:.1f} minutes.")

    best_val_loss_p1 = min(history_p1.history["val_loss"])
    logger.info(f"Phase 1 best val_loss: {best_val_loss_p1:.4f}")

    # ---- Phase 2: fine-tune the top of the backbone ----
    # Reload the best phase-1 checkpoint before unfreezing anything, so
    # fine-tuning starts from the best weights, not just the last epoch's.
    print(f"\nReloading best phase-1 checkpoint from {config.BEST_MODEL_PATH} for fine-tuning...")
    model = tf.keras.models.load_model(config.BEST_MODEL_PATH)

    utils.unfreeze_top_layers(
        model, n_layers=config.FT_UNFREEZE_LAYERS,
        backbone_layer_name=config.BACKBONE_LAYER_NAME, logger=logger,
    )

    # Re-compile is required after changing .trainable on existing layers.
    model.compile(
        optimizer=Adam(learning_rate=config.FT_LEARNING_RATE),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    # Seed ModelCheckpoint with phase 1's best val_loss so fine-tuning
    # only overwrites BEST_MODEL_PATH if it actually improves on it.
    callbacks_p2 = build_callbacks(config.BEST_MODEL_PATH, initial_best=best_val_loss_p1)

    start_time = time.time()
    history_p2 = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=config.FT_EPOCHS,
        callbacks=callbacks_p2,
        class_weight=class_weights,
        verbose=1,
    )
    phase2_time = time.time() - start_time
    logger.info(f"Phase 2 (fine-tuning) complete in {phase2_time / 60:.1f} minutes.")

    best_val_loss_p2 = min(history_p2.history["val_loss"]) if history_p2.history["val_loss"] else None
    if best_val_loss_p2 is not None:
        logger.info(f"Phase 2 best val_loss: {best_val_loss_p2:.4f} "
                    f"(overall best kept at {config.BEST_MODEL_PATH})")

    total_time = phase1_time + phase2_time
    print(f"\nTraining complete in {total_time / 60:.1f} minutes "
          f"(phase 1: {phase1_time / 60:.1f} min, phase 2: {phase2_time / 60:.1f} min).")

    # ---- Save last-epoch model + merged history + plots ----
    model.save(config.LAST_MODEL_PATH)

    merged_history = {
        key: history_p1.history[key] + history_p2.history[key]
        for key in history_p1.history
        if key in history_p2.history
    }
    utils.save_json(merged_history, config.HISTORY_PATH)
    utils.plot_training_curves(
        merged_history, config.PLOTS_DIR,
        fine_tune_start_epoch=len(history_p1.history["loss"]),
    )

    # ---- Reload the true best checkpoint for evaluation + export ----
    # (model in memory may be phase-2's last epoch, which isn't
    # necessarily the epoch ModelCheckpoint judged best overall.)
    best_model = tf.keras.models.load_model(config.BEST_MODEL_PATH)

    # ---- Evaluation: confusion matrix + classification report ----
    evaluation.evaluate_model(best_model, val_gen, display_names, logger=logger)

    # ---- Labels for inference (index -> display name, no hardcoding) ----
    labels = utils.save_labels_json(class_names, config.LABELS_PATH)
    logger.info(f"Saved labels.json to {config.LABELS_PATH}: {labels}")

    # ---- SavedModel export for deployment ----
    utils.export_saved_model(best_model, config.SAVEDMODEL_DIR, logger=logger)

    print(f"\nBest model:   {config.BEST_MODEL_PATH}")
    print(f"Last model:   {config.LAST_MODEL_PATH}")
    print(f"SavedModel:   {config.SAVEDMODEL_DIR}")
    print(f"Class names:  {config.CLASS_NAMES_PATH}")
    print(f"Labels:       {config.LABELS_PATH}")
    print(f"History:      {config.HISTORY_PATH}")
    print(f"Evaluation:   {config.EVAL_DIR}")
    print(f"Log file:     {config.TRAIN_LOG_FILE}")


if __name__ == "__main__":
    main()
