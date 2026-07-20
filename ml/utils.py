"""
utils.py
========
Shared utilities used by both train.py and evaluate.py:
    - reproducibility (seeding)
    - output folder creation
    - logging setup
    - MobileNetV2 model construction (with custom classifier head)
    - EarlyStopping
    - JSON save/load helpers
    - plotting (accuracy/loss curves, confusion matrix)
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
import seaborn as sns
import torch
import torch.nn as nn
from torchvision import models

import config


# --------------------------------------------------------------------------- #
# Reproducibility
# --------------------------------------------------------------------------- #

def set_seed(seed: int = config.SEED) -> None:
    """Seeds python, numpy and torch (CPU + CUDA) for reproducible runs."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


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

def build_model(num_classes: int, pretrained: bool = config.PRETRAINED,
                 freeze_features: bool = config.FREEZE_FEATURE_EXTRACTOR) -> nn.Module:
    """
    Builds a MobileNetV2 with a custom classification head:

        Dropout(0.3) -> Linear(1280, 512) -> ReLU -> Dropout(0.3) -> Linear(512, num_classes)

    The convolutional feature extractor is loaded with ImageNet-pretrained
    weights and frozen by default; only the new classifier head is trained.
    """
    if pretrained:
        weights = models.MobileNet_V2_Weights.IMAGENET1K_V1
        model = models.mobilenet_v2(weights=weights)
    else:
        model = models.mobilenet_v2(weights=None)

    if freeze_features:
        for param in model.features.parameters():
            param.requires_grad = False

    in_features = model.last_channel  # 1280 for MobileNetV2

    model.classifier = nn.Sequential(
        nn.Dropout(p=config.DROPOUT_RATE),
        nn.Linear(in_features, config.CLASSIFIER_HIDDEN_UNITS),
        nn.ReLU(inplace=True),
        nn.Dropout(p=config.DROPOUT_RATE),
        nn.Linear(config.CLASSIFIER_HIDDEN_UNITS, num_classes),
    )
    # classifier layers are newly created -> requires_grad=True by default

    return model


# --------------------------------------------------------------------------- #
# EarlyStopping
# --------------------------------------------------------------------------- #

class EarlyStopping:
    """
    Stops training when the monitored validation loss stops improving.

    Args:
        patience: number of epochs to wait after the last improvement.
        min_delta: minimum decrease in validation loss to qualify as an improvement.
    """

    def __init__(self, patience: int = config.EARLY_STOPPING_PATIENCE,
                 min_delta: float = config.EARLY_STOPPING_MIN_DELTA,
                 logger: logging.Logger = None):
        self.patience = patience
        self.min_delta = min_delta
        self.logger = logger

        self.best_loss = None
        self.counter = 0
        self.early_stop = False

    def __call__(self, val_loss: float) -> None:
        if self.best_loss is None:
            self.best_loss = val_loss
            return

        if val_loss < (self.best_loss - self.min_delta):
            self.best_loss = val_loss
            self.counter = 0
        else:
            self.counter += 1
            msg = f"EarlyStopping: no improvement for {self.counter}/{self.patience} epochs"
            if self.logger:
                self.logger.info(msg)
            if self.counter >= self.patience:
                self.early_stop = True


# --------------------------------------------------------------------------- #
# JSON helpers
# --------------------------------------------------------------------------- #

def save_json(data, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# Plotting
# --------------------------------------------------------------------------- #

def plot_training_curves(history: dict, plots_dir: str = config.PLOTS_DIR) -> None:
    """Saves accuracy.png and loss.png from the training history dict."""
    epochs = range(1, len(history["train_loss"]) + 1)

    # --- Loss curve ---
    plt.figure(figsize=(8, 6))
    plt.plot(epochs, history["train_loss"], label="Train Loss", marker="o")
    plt.plot(epochs, history["val_loss"], label="Validation Loss", marker="o")
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
    plt.plot(epochs, history["train_acc"], label="Train Accuracy", marker="o")
    plt.plot(epochs, history["val_acc"], label="Validation Accuracy", marker="o")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy (%)")
    plt.title("Training vs Validation Accuracy")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "accuracy.png"), dpi=150)
    plt.close()


def plot_confusion_matrix(cm: np.ndarray, class_names: list,
                           save_path: str = os.path.join(config.PLOTS_DIR, "confusion_matrix.png")) -> None:
    """Saves a heatmap confusion matrix image."""
    plt.figure(figsize=(7, 6))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=class_names, yticklabels=class_names,
        cbar=True, square=True,
    )
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.title("Confusion Matrix")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
