"""
evaluation.py
=============
Post-training evaluation for the FasalBima Pramaan crop-damage
classifier: confusion matrix + precision/recall/F1 classification
report on the validation split.

Can be run standalone against whatever is currently saved at
outputs/checkpoints/best_model.keras:

    python evaluation.py

...or imported and called directly from train.py right after training
finishes (which is what train.py does, so you don't need to run this
separately unless you want to re-evaluate later without retraining).
"""

import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, classification_report

import config
import utils


def evaluate_model(model, val_gen, class_display_names: list, logger=None) -> dict:
    """
    Runs the model over the full validation set and produces:
        - outputs/evaluation/confusion_matrix.png
        - outputs/evaluation/classification_report.txt   (human-readable)
        - outputs/evaluation/classification_report.json  (machine-readable)

    Args:
        model: a compiled/loaded Keras model.
        val_gen: validation DirectoryIterator (shuffle=False, as built by
            train.build_generators) so predictions line up with labels.
        class_display_names: display labels in class-index order, e.g.
            ["Drought Stress", "Flood Damage", "Healthy", "Pest Attack"].

    Returns:
        The sklearn classification_report as a dict (also what gets
        written to classification_report.json).
    """
    os.makedirs(config.EVAL_DIR, exist_ok=True)

    val_gen.reset()
    y_true = val_gen.classes
    y_pred_probs = model.predict(val_gen, steps=len(val_gen), verbose=0)
    y_pred = np.argmax(y_pred_probs, axis=1)

    # Guard against a partial final batch mismatch (defensive, shouldn't
    # normally trigger since steps=len(val_gen) covers every sample once).
    n = min(len(y_true), len(y_pred))
    y_true, y_pred = y_true[:n], y_pred[:n]

    # ---- Classification report (precision / recall / F1) ----
    report_txt = classification_report(
        y_true, y_pred, target_names=class_display_names, digits=3, zero_division=0,
    )
    report_dict = classification_report(
        y_true, y_pred, target_names=class_display_names, digits=3,
        zero_division=0, output_dict=True,
    )

    with open(config.CLASSIFICATION_REPORT_TXT_PATH, "w", encoding="utf-8") as f:
        f.write("FasalBima Pramaan - Validation Classification Report\n")
        f.write("=" * 55 + "\n\n")
        f.write(report_txt)
    utils.save_json(report_dict, config.CLASSIFICATION_REPORT_JSON_PATH)

    print("\nValidation Classification Report:\n")
    print(report_txt)
    if logger:
        logger.info("Classification report:\n" + report_txt)

    # ---- Confusion matrix ----
    cm = confusion_matrix(y_true, y_pred)
    _plot_confusion_matrix(cm, class_display_names, config.CONFUSION_MATRIX_PATH)

    msg = (f"Saved evaluation artifacts to {config.EVAL_DIR} "
           f"(confusion_matrix.png, classification_report.txt/.json)")
    print(msg)
    if logger:
        logger.info(msg)

    return report_dict


def _plot_confusion_matrix(cm: np.ndarray, class_names: list, out_path: str) -> None:
    """Plots a confusion matrix with counts annotated in each cell."""
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im = ax.imshow(cm, cmap="Blues")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax.set_xticks(range(len(class_names)))
    ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=35, ha="right")
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Predicted label")
    ax.set_ylabel("True label")
    ax.set_title("Validation Confusion Matrix")

    thresh = cm.max() / 2 if cm.max() > 0 else 0.5
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], "d"), ha="center", va="center",
                     color="white" if cm[i, j] > thresh else "black")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    # Standalone re-evaluation of whatever is currently at BEST_MODEL_PATH,
    # without retraining. Rebuilds the validation generator the same way
    # train.py does, using labels.json for class ordering.
    import tensorflow as tf
    from tensorflow.keras.preprocessing.image import ImageDataGenerator

    if not os.path.exists(config.BEST_MODEL_PATH):
        raise FileNotFoundError(
            f"No trained model found at {config.BEST_MODEL_PATH}. Run `python train.py` first."
        )

    model = tf.keras.models.load_model(config.BEST_MODEL_PATH)
    class_folder_names = utils.load_json(config.CLASS_NAMES_PATH)
    display_names = [config.CLASS_DISPLAY_NAMES.get(n, n) for n in class_folder_names]

    val_datagen = ImageDataGenerator()
    val_gen = val_datagen.flow_from_directory(
        config.VALIDATION_DIR,
        target_size=(config.IMAGE_SIZE, config.IMAGE_SIZE),
        batch_size=config.BATCH_SIZE,
        class_mode="categorical",
        classes=class_folder_names,
        shuffle=False,
    )

    evaluate_model(model, val_gen, display_names)
