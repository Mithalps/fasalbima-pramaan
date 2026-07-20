import logging

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.exceptions import ClassifierServiceError
from app.schemas.classifier import ClassifyResponse
from app.services import classifier_service

logger = logging.getLogger("fasalbima.classifier.router")

router = APIRouter(prefix="/api", tags=["classifier"])


@router.post(
    "/classify",
    response_model=ClassifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Classify crop-damage severity from a photo",
)
async def classify(image: UploadFile):
    """
    Accepts a crop photo (JPEG, PNG, or WEBP) and returns the predicted
    class and confidence from the trained MobileNetV2 checkpoint.
    """
    image_bytes = await image.read()

    logger.info(
        "Received classification request filename=%s content_type=%s size_bytes=%d",
        image.filename,
        image.content_type,
        len(image_bytes),
    )

    try:
        classifier_service.validate_image_upload(
            content_type=image.content_type, size_bytes=len(image_bytes)
        )
        prediction, confidence = classifier_service.classify_image(image_bytes)
    except ClassifierServiceError as exc:
        logger.warning(
            "Classification request failed filename=%s reason=%s",
            image.filename,
            exc.message,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return ClassifyResponse(prediction=prediction, confidence=confidence)
