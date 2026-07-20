import io
import json
import logging
import time
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms

from app.config import settings
from app.exceptions import (
    ClassifierNotReadyError,
    EmptyImageError,
    ImageTooLargeError,
    InvalidImageError,
    UnsupportedImageTypeError,
)

logger = logging.getLogger("fasalbima.classifier")

# Must match training exactly: 224x224, ImageNet normalization stats.
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

_preprocess = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ]
)

SUPPORTED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}

_device = torch.device("cpu")
_model: nn.Module | None = None
_class_names: list[str] | None = None


def _build_model(num_classes: int) -> nn.Module:
    """
    Reconstructs the exact architecture the checkpoint was trained with:
    torchvision's MobileNetV2 backbone (weights=None — we load our own
    trained weights below, not ImageNet-pretrained ones) with its classifier
    head replaced by Dropout -> Linear(1280,512) -> ReLU -> Dropout ->
    Linear(512, num_classes). This shape was reverse-engineered from the
    checkpoint's own state_dict keys (classifier.1.*, classifier.4.*) to
    guarantee load_state_dict() matches exactly.
    """
    model = models.mobilenet_v2(weights=None)
    model.classifier = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(model.last_channel, 512),
        nn.ReLU(inplace=True),
        nn.Dropout(0.3),
        nn.Linear(512, num_classes),
    )
    return model


def load_model() -> None:
    """
    Loads the trained checkpoint and class names once, at FastAPI startup
    (see main.py's on_startup handler) — not on every request.
    """
    global _model, _class_names

    checkpoint_path = Path(settings.classifier_checkpoint_path)
    class_names_path = Path(settings.classifier_class_names_path)

    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"Classifier checkpoint not found at '{checkpoint_path}'. "
            "Place best_model.pth there before starting the server."
        )
    if not class_names_path.exists():
        raise FileNotFoundError(
            f"class_names.json not found at '{class_names_path}'."
        )

    with open(class_names_path, "r", encoding="utf-8") as f:
        class_names = json.load(f)

    checkpoint = torch.load(checkpoint_path, map_location=_device, weights_only=False)
    state_dict = checkpoint["model_state_dict"]

    checkpoint_class_names = checkpoint.get("class_names")
    if checkpoint_class_names and checkpoint_class_names != class_names:
        logger.warning(
            "class_names.json (%s) differs from class_names embedded in the "
            "checkpoint (%s). Using class_names.json as the source of truth.",
            class_names,
            checkpoint_class_names,
        )

    model = _build_model(num_classes=len(class_names))
    model.load_state_dict(state_dict)
    model.eval()
    model.to(_device)

    _model = model
    _class_names = class_names

    logger.info(
        "Classifier loaded: classes=%s checkpoint_epoch=%s checkpoint_val_acc=%s",
        class_names,
        checkpoint.get("epoch"),
        checkpoint.get("val_acc"),
    )


def is_ready() -> bool:
    return _model is not None and _class_names is not None


def _normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").split(";")[0].strip().lower()


def validate_image_upload(content_type: str | None, size_bytes: int) -> None:
    """
    Validates an uploaded image before it's run through the model. Raises:
      - EmptyImageError            if size_bytes is 0
      - ImageTooLargeError         if size_bytes exceeds the configured limit
      - UnsupportedImageTypeError  if content_type isn't one we accept
    """
    if size_bytes == 0:
        raise EmptyImageError("The uploaded image was empty. Please try again.")

    max_bytes = settings.classifier_max_image_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise ImageTooLargeError(
            f"That image is too large ({size_bytes / (1024 * 1024):.1f} MB). "
            f"The limit is {settings.classifier_max_image_size_mb} MB."
        )

    normalized = _normalize_content_type(content_type)
    if normalized not in SUPPORTED_IMAGE_MIME_TYPES:
        raise UnsupportedImageTypeError(
            f"Unsupported image format ({content_type or 'unknown'}). "
            "Supported formats: JPEG, PNG, WEBP."
        )


def classify_image(image_bytes: bytes) -> tuple[str, float]:
    """
    Runs the loaded model on a single image and returns (predicted_label, confidence).

    Raises:
      - ClassifierNotReadyError  if load_model() hasn't succeeded
      - InvalidImageError        if the bytes can't be decoded as an image
    """
    if not is_ready():
        raise ClassifierNotReadyError(
            "The image classifier is not available right now. Check server "
            "startup logs for a missing or invalid checkpoint."
        )

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise InvalidImageError(
            "Could not read this file as an image. Try a JPEG, PNG, or WEBP."
        ) from exc

    tensor = _preprocess(image).unsqueeze(0).to(_device)

    start = time.perf_counter()
    with torch.no_grad():
        logits = _model(tensor)
        probabilities = torch.softmax(logits, dim=1)[0]
    elapsed = time.perf_counter() - start

    confidence, predicted_index = torch.max(probabilities, dim=0)
    label = _class_names[predicted_index.item()]

    logger.info(
        "Classified image in %.3fs -> %s (confidence=%.4f)",
        elapsed,
        label,
        confidence.item(),
    )

    return label, float(confidence.item())
