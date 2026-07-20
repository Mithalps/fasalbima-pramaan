"""
config.py
=========
Central configuration for the Plant Disease Classification pipeline
(MobileNetV2 + PyTorch).

Every other script (train.py, evaluate.py, utils.py) imports its
settings from here. Edit this file to change hyperparameters, paths,
or runtime behaviour -- nothing else needs to change.
"""

import os
import torch

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

# Root of this project (the folder this file lives in, i.e. "ml/")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Dataset root. Matches the Kaggle layout:
#   ml/dataset/Train/<class>/
#   ml/dataset/Validation/<class>/
#   ml/dataset/Test/<class>/
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
TRAIN_DIR = os.path.join(DATASET_DIR, "Train")
VALIDATION_DIR = os.path.join(DATASET_DIR, "Validation")
TEST_DIR = os.path.join(DATASET_DIR, "Test")

# Output locations (created automatically by utils.create_output_dirs)
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
CHECKPOINT_DIR = os.path.join(OUTPUT_DIR, "checkpoints")
PLOTS_DIR = os.path.join(OUTPUT_DIR, "plots")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")

BEST_MODEL_PATH = os.path.join(CHECKPOINT_DIR, "best_model.pth")
LAST_MODEL_PATH = os.path.join(CHECKPOINT_DIR, "last_model.pth")
CLASS_NAMES_PATH = os.path.join(CHECKPOINT_DIR, "class_names.json")
HISTORY_PATH = os.path.join(CHECKPOINT_DIR, "training_history.json")
CLASSIFICATION_REPORT_PATH = os.path.join(LOGS_DIR, "classification_report.txt")

TRAIN_LOG_FILE = os.path.join(LOGS_DIR, "training.log")
EVAL_LOG_FILE = os.path.join(LOGS_DIR, "evaluation.log")

# --------------------------------------------------------------------------- #
# Data / DataLoader
# --------------------------------------------------------------------------- #

IMAGE_SIZE = 224          # final input size fed to MobileNetV2
RESIZE_SIZE = 256         # size images are resized to before crop
BATCH_SIZE = 32           # configurable
NUM_WORKERS = 0           # configurable (set to 0 on Windows if you hit issues)
PIN_MEMORY = True

# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #

MODEL_NAME = "mobilenet_v2"
PRETRAINED = True         # load ImageNet pretrained weights
FREEZE_FEATURE_EXTRACTOR = True
NUM_CLASSES = 3            # Healthy, Powdery, Rust (auto-verified against ImageFolder at runtime)

# Custom classifier head dimensions
CLASSIFIER_HIDDEN_UNITS = 512
DROPOUT_RATE = 0.3

# --------------------------------------------------------------------------- #
# Training
# --------------------------------------------------------------------------- #

EPOCHS = 10
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4

# ReduceLROnPlateau scheduler
SCHEDULER_MODE = "min"        # watching validation loss
SCHEDULER_FACTOR = 0.5
SCHEDULER_PATIENCE = 3
SCHEDULER_MIN_LR = 1e-6

# EarlyStopping
EARLY_STOPPING_PATIENCE = 7
EARLY_STOPPING_MIN_DELTA = 1e-4

# Reproducibility
SEED = 42

# --------------------------------------------------------------------------- #
# Device
# --------------------------------------------------------------------------- #

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
