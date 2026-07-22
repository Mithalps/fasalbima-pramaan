"""
config.py
=========
Central configuration for the FasalBima Pramaan crop-damage classifier
(EfficientNetB0 + TensorFlow/Keras).

Every other script (train.py, inference.py) imports its settings from
here. Edit this file to change hyperparameters, paths, or class labels
-- nothing else needs to change.

NOTE: This replaces the previous PyTorch / MobileNetV2 / PlantVillage
(Healthy, Powdery, Rust) pipeline. The classifier is now trained on
crop-insurance-relevant damage classes for PMFBY claim assistance.

Training is two-phase: (1) frozen-backbone warmup, (2) fine-tuning with
the top FT_UNFREEZE_LAYERS backbone layers unfrozen at a lower LR. See
train.py for the full flow and utils.py for the supporting functions.
"""

import os

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

# Root of this project (the folder this file lives in, i.e. "ml/")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Dataset root. Matches the cleaned dataset layout:
#   ml/dataset/train/<class>/
#   ml/dataset/val/<class>/
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
TRAIN_DIR = os.path.join(DATASET_DIR, "train")
VALIDATION_DIR = os.path.join(DATASET_DIR, "val")

# Output locations (created automatically by utils.create_output_dirs)
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
CHECKPOINT_DIR = os.path.join(OUTPUT_DIR, "checkpoints")
PLOTS_DIR = os.path.join(OUTPUT_DIR, "plots")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")

BEST_MODEL_PATH = os.path.join(CHECKPOINT_DIR, "best_model.keras")
LAST_MODEL_PATH = os.path.join(CHECKPOINT_DIR, "last_model.keras")
CLASS_NAMES_PATH = os.path.join(CHECKPOINT_DIR, "class_names.json")
HISTORY_PATH = os.path.join(CHECKPOINT_DIR, "training_history.json")

# index (as string) -> farmer/claim-facing display label, e.g. {"0": "Drought
# Stress", ...}. This is the file inference.py reads at load time so class
# labels are never hardcoded in code -- see utils.save_labels_json().
LABELS_PATH = os.path.join(CHECKPOINT_DIR, "labels.json")

# TensorFlow SavedModel export (for serving, e.g. TF Serving / TFLite convert)
SAVEDMODEL_DIR = os.path.join(OUTPUT_DIR, "saved_model")

# Evaluation artifacts (confusion matrix, classification report)
EVAL_DIR = os.path.join(OUTPUT_DIR, "evaluation")
CONFUSION_MATRIX_PATH = os.path.join(EVAL_DIR, "confusion_matrix.png")
CLASSIFICATION_REPORT_TXT_PATH = os.path.join(EVAL_DIR, "classification_report.txt")
CLASSIFICATION_REPORT_JSON_PATH = os.path.join(EVAL_DIR, "classification_report.json")

TRAIN_LOG_FILE = os.path.join(LOGS_DIR, "training.log")

# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #

IMAGE_SIZE = 224          # final input size fed to EfficientNetB0
BATCH_SIZE = 8
SEED = 42

# NOTE: current dataset is small (112 train / 28 val images, smallest class
# = 23 train / 6 val for "drought"). Class weighting (see
# utils.compute_class_weights) and heavier augmentation are used to
# compensate, but treat evaluation metrics as indicative rather than
# statistically robust -- grow the dataset post-hackathon for real use.

# --------------------------------------------------------------------------- #
# Classes
# --------------------------------------------------------------------------- #
# Folder names on disk (alphabetical -> matches Keras' flow_from_directory /
# image_dataset_from_directory ordering) mapped to farmer/claim-facing labels
# used everywhere in the API, PDF report, and frontend.
#
# Folder order: drought, flood, healthy, pest  (alphabetical)

CLASS_FOLDER_NAMES = ["drought", "flood", "healthy", "pest"]

CLASS_DISPLAY_NAMES = {
    "drought": "Drought Stress",
    "flood": "Flood Damage",
    "healthy": "Healthy",
    "pest": "Pest Attack",
}

NUM_CLASSES = len(CLASS_FOLDER_NAMES)

# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #

MODEL_NAME = "efficientnetb0"
PRETRAINED = True                # load ImageNet pretrained weights
FREEZE_BASE = True                # freeze the pretrained backbone for phase 1

# Preferred name for locating the EfficientNetB0 sub-model inside the
# functional model during fine-tuning (utils.find_backbone_layer). Keras
# layer names aren't guaranteed to survive a save/reload round trip, so
# this is a first-try hint only -- there's a type-based fallback lookup
# that works regardless of what the layer ends up named.
BACKBONE_LAYER_NAME = "backbone"

DROPOUT_RATE = 0.3
DENSE_UNITS = 256

# --------------------------------------------------------------------------- #
# Training (phase 1 -- frozen backbone)
# --------------------------------------------------------------------------- #

EPOCHS = 30
LEARNING_RATE = 1e-4

# ReduceLROnPlateau
RLR_MONITOR = "val_loss"
RLR_FACTOR = 0.5
RLR_PATIENCE = 3
RLR_MIN_LR = 1e-6

# EarlyStopping
ES_MONITOR = "val_loss"
ES_PATIENCE = 7
ES_MIN_DELTA = 1e-4

# --------------------------------------------------------------------------- #
# Fine-tuning (phase 2 -- unfreeze top of the backbone)
# --------------------------------------------------------------------------- #
# After phase 1 converges, the best checkpoint is reloaded and the top
# FT_UNFREEZE_LAYERS layers of the EfficientNetB0 backbone are unfrozen
# (BatchNormalization layers are always kept frozen, even if they fall
# inside that range, to avoid corrupting pretrained batch statistics on
# such a small dataset). Training then continues at a much lower LR.

FT_UNFREEZE_LAYERS = 25     # within the requested 20-30 range
FT_EPOCHS = 5
FT_LEARNING_RATE = 1e-5

# --------------------------------------------------------------------------- #
# Online augmentation (train split only; no offline duplication)
# --------------------------------------------------------------------------- #

AUGMENTATION = {
    "rotation_range": 20,
    "zoom_range": 0.2,
    "horizontal_flip": True,
    "brightness_range": [0.8, 1.2],
    "width_shift_range": 0.15,
    "height_shift_range": 0.15,
}
