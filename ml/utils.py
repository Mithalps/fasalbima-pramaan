"""
utils.py
========
Shared utilities used by train.py, evaluation.py and inference.py:
    - reproducibility (seeding)
    - output folder creation
    - logging setup
    - EfficientNetB0 model construction (with graceful degradation if
      ImageNet weights can't be downloaded)
    - fine-tuning helpers (unfreezing the top backbone layers)
    - class-weight computation for the class imbalance in the dataset
    - JSON / labels.json save/load helpers
    - plotting (accuracy/loss curves, with an optional fine-tune marker)
"""

import json
import logging
import os
import random
import sys

import matplotlib
matplotlib.use("Agg")  # headless backend, safe for servers / no display
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.utils.class_weight import compute_class_weight

import config


# --------------------------------------------------------------------------- #
# Reproducibility
# --------------------------------------------------------------------------- #

def set_seed(seed: int = config.SEED) -> None:
    """Seeds python, numpy and tensorflow for reproducible runs."""
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)


# --------------------------------------------------------------------------- #
# Folder setup
# --------------------------------------------------------------------------- #

def create_output_dirs() -> None:
    """Creates outputs/, checkpoints/, plots/, logs/ if they don't exist yet."""
    for d in [config.OUTPUT_DIR, config.CHECKPOINT_DIR, config.PLOTS_DIR, config.LOGS_DIR]:
        os.makedirs(d, exist_ok=True)


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

def setup_logger(name: str, log_file: str) -> logging.Logger:
    """Creates a logger that writes to both the console and a log file."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.INFO)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    ch.setLevel(logging.INFO)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #

def build_model(num_classes: int = config.NUM_CLASSES,
                 pretrained: bool = config.PRETRAINED,
                 freeze_base: bool = config.FREEZE_BASE,
                 logger: logging.Logger = None):
    """
    Builds an EfficientNetB0 transfer-learning model with a custom
    classification head:

        GlobalAveragePooling2D -> Dropout -> Dense(DENSE_UNITS, relu)
        -> Dropout -> Dense(num_classes, softmax)

    Graceful ImageNet-weights fallback: if the pretrained weights can't
    be downloaded (e.g. no internet access at train time), the model
    KEEPS the EfficientNetB0 architecture -- only the weight
    initialization changes, from ImageNet to random (He/Glorot) init.
    This is a deliberate change from swapping to a different backbone
    (e.g. MobileNetV2) on failure: silently changing architectures would
    violate "use EfficientNetB0" and would make the frozen-backbone /
    fine-tuning steps below inconsistent depending on network luck.
    The fallback is always logged loudly so it's never silent.

    The backbone can be located later via utils.find_backbone_layer()
    for fine-tuning -- see that function's docstring for why it isn't
    simply looked up by a fixed name.

    Returns:
        (model, weights_used) where weights_used is "imagenet" or "random_init"
    """
    input_shape = (config.IMAGE_SIZE, config.IMAGE_SIZE, 3)
    preprocess_fn = tf.keras.applications.efficientnet.preprocess_input

    weights_used = "imagenet" if pretrained else "random_init"
    try:
        base = tf.keras.applications.EfficientNetB0(
            include_top=False,
            weights="imagenet" if pretrained else None,
            input_shape=input_shape,
        )
    except Exception as e:
        msg = (f"Could not download ImageNet weights for EfficientNetB0 ({e}). "
               f"Falling back to EfficientNetB0 with random weight initialization -- "
               f"architecture is unchanged, but expect noticeably lower accuracy "
               f"without transfer learning, especially on a dataset this small.")
        if logger:
            logger.warning(msg)
        print(f"WARNING: {msg}")
        weights_used = "random_init"
        base = tf.keras.applications.EfficientNetB0(
            include_top=False, weights=None, input_shape=input_shape,
        )

    base.trainable = not freeze_base

    inputs = layers.Input(shape=input_shape)
    x = preprocess_fn(inputs)
    x = base(x, training=False if freeze_base else None)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(config.DROPOUT_RATE)(x)
    x = layers.Dense(config.DENSE_UNITS, activation="relu")(x)
    x = layers.Dropout(config.DROPOUT_RATE)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)

    model = models.Model(inputs, outputs, name="fasalbima_efficientnetb0")
    return model, weights_used


def find_backbone_layer(model, preferred_name: str = config.BACKBONE_LAYER_NAME):
    """
    Locates the EfficientNetB0 backbone sub-model inside `model`.

    Keras layer names aren't guaranteed to survive a save/reload round
    trip through the .keras format (renaming via `layer._name` before
    the model is built doesn't reliably persist), so this tries the
    expected name first and falls back to finding the sub-model by
    type -- the backbone is the only nested tf.keras.Model layer in
    this architecture (see utils.build_model), so this is unambiguous.
    """
    try:
        return model.get_layer(preferred_name)
    except ValueError:
        pass
    for layer in model.layers:
        if isinstance(layer, models.Model):
            return layer
    raise ValueError(
        "Could not locate the EfficientNetB0 backbone layer inside the model "
        "(expected a nested tf.keras.Model layer, found none)."
    )


def unfreeze_top_layers(model, n_layers: int = config.FT_UNFREEZE_LAYERS,
                         backbone_layer_name: str = config.BACKBONE_LAYER_NAME,
                         logger: logging.Logger = None):
    """
    Fine-tuning step: unfreezes only the top `n_layers` layers of the
    EfficientNetB0 backbone inside `model`, keeping everything below
    frozen. BatchNormalization layers are always re-frozen afterwards
    (even if they land inside the unfrozen range) so their running
    statistics -- learned on the full ImageNet dataset -- aren't
    disturbed by a training set of only ~100 images.

    Must be called AFTER reloading the phase-1 best checkpoint, and the
    model must be re-compiled (lower LR) after calling this, since
    changing `.trainable` on already-built layers requires a recompile
    to take effect.

    Returns the same model (mutated in place) for convenience chaining.
    """
    base = find_backbone_layer(model, backbone_layer_name)
    base.trainable = True

    freeze_until = max(0, len(base.layers) - n_layers)
    bn_refrozen = 0
    for i, layer in enumerate(base.layers):
        if i < freeze_until:
            layer.trainable = False
        else:
            layer.trainable = True
        if isinstance(layer, layers.BatchNormalization):
            layer.trainable = False
            bn_refrozen += 1

    msg = (f"Fine-tuning: unfroze top {n_layers} of {len(base.layers)} backbone layers "
           f"(BatchNormalization layers kept frozen -- {bn_refrozen} affected).")
    if logger:
        logger.info(msg)
    print(msg)
    return model


# --------------------------------------------------------------------------- #
# Class imbalance
# --------------------------------------------------------------------------- #

def compute_class_weights(train_gen, logger: logging.Logger = None) -> dict:
    """
    Computes balanced class weights from a Keras DirectoryIterator using
    sklearn.utils.class_weight.compute_class_weight, so under-represented
    classes (e.g. "drought" with only 23 train images vs "pest" with 33)
    contribute proportionally more to the loss.

    Returns:
        {class_index: weight} -- ready to pass as model.fit(class_weight=...)
    """
    y = train_gen.classes  # integer label per training sample, index order
    class_indices = np.unique(y)
    weights = compute_class_weight(class_weight="balanced", classes=class_indices, y=y)
    class_weights = {int(idx): float(w) for idx, w in zip(class_indices, weights)}

    msg = f"Computed class weights: {class_weights}"
    if logger:
        logger.info(msg)
    print(msg)
    return class_weights


# --------------------------------------------------------------------------- #
# JSON helpers
# --------------------------------------------------------------------------- #

def save_json(data, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_labels_json(class_folder_names: list, path: str = config.LABELS_PATH) -> dict:
    """
    Builds and saves labels.json: {"0": "Drought Stress", "1": "Flood Damage", ...}
    -- index (as string) -> farmer/claim-facing display label, in the exact
    index order produced by flow_from_directory (saved alongside as
    class_names.json for the underlying folder names).

    This is the single source of truth inference.py reads to turn model
    output indices into display labels, so display names are never
    hardcoded in inference.py itself.
    """
    labels = {
        str(idx): config.CLASS_DISPLAY_NAMES.get(folder_name, folder_name)
        for idx, folder_name in enumerate(class_folder_names)
    }
    save_json(labels, path)
    return labels


# --------------------------------------------------------------------------- #
# Model export
# --------------------------------------------------------------------------- #

def export_saved_model(model, export_dir: str = config.SAVEDMODEL_DIR,
                        logger: logging.Logger = None) -> bool:
    """
    Exports `model` as a TensorFlow SavedModel for deployment (e.g. TF
    Serving, TFLite/TF.js conversion) -- separate from the .keras
    checkpoint format used for resuming training.

    Handles both API generations since this differs by TF/Keras version:
      - Keras 3 (TF >= 2.16): Model.export(dir) -- inference-only SavedModel
      - Keras 2 (TF < 2.16):  Model.save(dir, save_format="tf")

    Returns True on success, False if export failed (training/eval
    artifacts are still valid either way, so this is non-fatal).
    """
    import shutil
    if os.path.exists(export_dir):
        shutil.rmtree(export_dir)  # export() refuses to write into a non-empty dir

    try:
        model.export(export_dir)          # Keras 3 API
    except AttributeError:
        try:
            model.save(export_dir, save_format="tf")   # Keras 2 API
        except Exception as e:
            msg = f"SavedModel export failed ({e}). best_model.keras is still available."
            if logger:
                logger.warning(msg)
            print(f"WARNING: {msg}")
            return False
    except Exception as e:
        msg = f"SavedModel export failed ({e}). best_model.keras is still available."
        if logger:
            logger.warning(msg)
        print(f"WARNING: {msg}")
        return False

    msg = f"Exported TensorFlow SavedModel to {export_dir}"
    if logger:
        logger.info(msg)
    print(msg)
    return True


# --------------------------------------------------------------------------- #
# Plotting
# --------------------------------------------------------------------------- #

def plot_training_curves(history: dict, plots_dir: str = config.PLOTS_DIR,
                          fine_tune_start_epoch: int = None) -> None:
    """
    Saves accuracy.png and loss.png from a (merged) Keras History.history
    dict covering both training phases.

    If `fine_tune_start_epoch` is given, a dashed vertical line marks
    where phase 2 (fine-tuning, unfrozen backbone) began -- useful for a
    hackathon demo to visually call out the two-phase strategy.
    """
    epochs = range(1, len(history["loss"]) + 1)

    def _mark_fine_tune():
        if fine_tune_start_epoch is not None:
            plt.axvline(x=fine_tune_start_epoch, color="gray", linestyle="--", alpha=0.6,
                        label="Fine-tuning starts")

    # --- Loss curve ---
    plt.figure(figsize=(8, 6))
    plt.plot(epochs, history["loss"], label="Train Loss", marker="o")
    plt.plot(epochs, history["val_loss"], label="Validation Loss", marker="o")
    _mark_fine_tune()
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("Training vs Validation Loss")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "loss.png"), dpi=150)
    plt.close()

    # --- Accuracy curve ---
    plt.figure(figsize=(8, 6))
    plt.plot(epochs, history["accuracy"], label="Train Accuracy", marker="o")
    plt.plot(epochs, history["val_accuracy"], label="Validation Accuracy", marker="o")
    _mark_fine_tune()
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.title("Training vs Validation Accuracy")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "accuracy.png"), dpi=150)
    plt.close()
