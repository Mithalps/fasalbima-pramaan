"""
inference.py
=============
Loads the trained FasalBima Pramaan crop-damage classifier
(EfficientNetB0 / TensorFlow-Keras) and runs predictions on a single
image. Designed to be imported directly by the FastAPI backend
(see backend_integration/classifier_service.py), and also runnable
standalone for quick manual checks:

    python inference.py path/to/image.jpg

Class labels are never hardcoded here -- they're loaded at runtime
from outputs/checkpoints/labels.json (index -> display name), which
train.py generates automatically to match the trained model's output
order. If you retrain with different classes, this file needs no edits.

Replaces the previous PlantVillage (Healthy/Powdery/Rust) inference
script.
"""

import os
import sys

import numpy as np
from PIL import Image
import tensorflow as tf

import config
import utils

_MODEL = None
_LABELS = None  # {"0": "Drought Stress", "1": "Flood Damage", ...}


def _load_model():
    """Lazily loads and caches the Keras model + labels.json (singleton)."""
    global _MODEL, _LABELS
    if _MODEL is None:
        if not os.path.exists(config.BEST_MODEL_PATH):
            raise FileNotFoundError(
                f"No trained model found at {config.BEST_MODEL_PATH}. "
                f"Run `python train.py` first."
            )
        _MODEL = tf.keras.models.load_model(config.BEST_MODEL_PATH)

        if os.path.exists(config.LABELS_PATH):
            _LABELS = utils.load_json(config.LABELS_PATH)
        elif os.path.exists(config.CLASS_NAMES_PATH):
            # Fallback for older runs that predate labels.json: derive it
            # from class_names.json + config.CLASS_DISPLAY_NAMES instead.
            folder_names = utils.load_json(config.CLASS_NAMES_PATH)
            _LABELS = utils.save_labels_json(folder_names, config.LABELS_PATH)
        else:
            raise FileNotFoundError(
                f"Neither {config.LABELS_PATH} nor {config.CLASS_NAMES_PATH} found. "
                f"Run `python train.py` first."
            )

    return _MODEL, _LABELS


def preprocess_image(image: Image.Image) -> np.ndarray:
    """
    Converts a PIL image into a (1, IMAGE_SIZE, IMAGE_SIZE, 3) float32 batch.

    NOTE: pixel values are kept in raw [0, 255] range -- EfficientNetB0's
    Rescaling + Normalization layers are baked into the model graph itself
    (see utils.build_model), matching the training ImageDataGenerator
    (no rescale in build_generators). Do NOT scale here; doing so
    double-normalizes the input and silently breaks predictions.
    """
    image = image.convert("RGB")
    image = image.resize((config.IMAGE_SIZE, config.IMAGE_SIZE))
    arr = np.asarray(image, dtype=np.float32)
    return np.expand_dims(arr, axis=0)


def predict_image(image: Image.Image) -> dict:
    """
    Runs inference on a single PIL image.

    Returns:
        {
            "prediction": "Flood Damage",
            "confidence": 94.2,
            "probabilities": {
                "Flood Damage": 94.2,
                "Healthy": 2.1,
                "Drought Stress": 2.0,
                "Pest Attack": 1.7
            },
            # kept for backend_integration/ backward compatibility:
            "prediction_key": "flood",
            "all_probabilities": { ... same as "probabilities" ... }
        }
    """
    model, labels = _load_model()

    batch = preprocess_image(image)
    probs = model.predict(batch, verbose=0)[0]  # shape: (num_classes,), index order == labels.json

    top_idx = int(np.argmax(probs))
    top_label = labels[str(top_idx)]

    probabilities = {
        labels[str(i)]: round(float(p) * 100, 2) for i, p in enumerate(probs)
    }

    return {
        "prediction": top_label,
        "confidence": round(float(probs[top_idx]) * 100, 2),
        "probabilities": probabilities,
        # Backward-compatible extras used by backend_integration/*.py:
        "prediction_key": config.CLASS_FOLDER_NAMES[top_idx]
            if top_idx < len(config.CLASS_FOLDER_NAMES) else str(top_idx),
        "all_probabilities": probabilities,
    }


def predict_image_path(image_path: str) -> dict:
    """Convenience wrapper: loads an image from disk and predicts on it."""
    with Image.open(image_path) as img:
        return predict_image(img)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python inference.py path/to/image.jpg")
        sys.exit(1)

    result = predict_image_path(sys.argv[1])
    print(f"Prediction: {result['prediction']}")
    print(f"Confidence: {result['confidence']}%")
    print("All class probabilities:")
    for label, pct in sorted(result["probabilities"].items(), key=lambda kv: -kv[1]):
        print(f"  {label}: {pct}%")
