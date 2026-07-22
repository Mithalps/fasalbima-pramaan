"""
classifier_service.py
======================
FastAPI-facing service wrapper around the FasalBima Pramaan crop-damage
classifier (EfficientNetB0 / TensorFlow-Keras).

This is a NEW file -- no previous FastAPI classifier service was
included in the uploaded project, so this was written from scratch to
match the standard "service layer" pattern typically used alongside a
FastAPI router (one function per concern, model loaded once at import
time, plain dict/JSON-serializable return values).

DROP-IN INSTRUCTIONS
---------------------
1. Copy this file into your backend, e.g. `backend/app/services/classifier_service.py`.
2. Make sure the `ml/` folder (config.py, inference.py, and the trained
   `outputs/checkpoints/best_model.keras` + `class_names.json`) is
   importable from the backend -- either:
     a) put `ml/` on PYTHONPATH, or
     b) copy ml/config.py + ml/inference.py next to this file and adjust
        the two imports below accordingly.
3. Replace any previous `from .powdery_rust_classifier import predict_disease`
   (or similarly named PlantVillage import) in your claim/router code
   with:
        from app.services.classifier_service import classify_crop_image
4. The response shape below (`prediction`, `confidence`, `all_probabilities`,
   `disclaimer`) is designed to be used directly as (part of) a FastAPI
   response model and dropped straight into the PDF generator.
"""

import io
import sys
import os

from PIL import Image

# --- import the ml/ package -------------------------------------------------
# Adjust this path if you place ml/ somewhere else relative to the backend.
ML_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "..",
        "..",
        "ml"
    )
)
print("ML_DIR =", ML_DIR)
if ML_DIR not in sys.path:
    sys.path.append(ML_DIR)

import config          # noqa: E402  (from ml/)
import inference        # noqa: E402  (from ml/)


DISCLAIMER = (
    "Experimental AI prediction. Used as supplementary evidence only."
)

from app.exceptions import ClassifierServiceError

ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_image_upload(content_type: str, size_bytes: int):
    if content_type not in ALLOWED_TYPES:
        raise ClassifierServiceError(
            status_code=400,
            message="Unsupported image format. Use JPEG, PNG, or WEBP."
        )

    if size_bytes == 0:
        raise ClassifierServiceError(
            status_code=400,
            message="Uploaded image is empty."
        )

    if size_bytes > MAX_IMAGE_SIZE:
        raise ClassifierServiceError(
            status_code=413,
            message="Image exceeds maximum allowed size."
        )

def classify_crop_image(image_bytes: bytes) -> dict:
    """
    Runs the crop-damage classifier on raw image bytes (as received from
    a FastAPI `UploadFile.read()`).

    Args:
        image_bytes: raw bytes of the uploaded image file.

    Returns:
        {
            "prediction": "Flood Damage",
            "prediction_key": "flood",
            "confidence": 94.3,
            "all_probabilities": {
                "Healthy": 1.2,
                "Flood Damage": 94.3,
                "Drought Stress": 2.1,
                "Pest Attack": 2.4
            },
            "disclaimer": "Experimental AI prediction. Used as supplementary evidence only."
        }

    Raises:
        ValueError: if the bytes cannot be decoded as an image.
        FileNotFoundError: if the trained model checkpoint is missing
            (i.e. `python train.py` hasn't been run yet).
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except Exception as e:
        raise ValueError(f"Uploaded file is not a valid image: {e}")

    result = inference.predict_image(image)
    result["disclaimer"] = DISCLAIMER
    return result


def is_model_ready() -> bool:
    """Health-check helper: True if the trained model checkpoint exists."""
    return os.path.exists(config.BEST_MODEL_PATH)

def load_model():
    """
    Preload the TensorFlow model during FastAPI startup.
    """
    inference.get_model()

def classify_image(image_bytes: bytes):
    """
    Compatibility wrapper for the existing router.
    """
    result = classify_crop_image(image_bytes)

    return (
        result["prediction"],
        float(result["confidence"])
    )    