"""
example_router_usage.py
========================
Illustrates how to wire classifier_service.py into a FastAPI route.
This is a REFERENCE snippet -- merge it into your existing claims
router rather than running it standalone, since your actual router
(with Whisper transcription, weather validation, DB writes, etc.)
was not included in the upload.

Replace your previous PlantVillage classify endpoint body with the
`classify_crop_image(...)` call shown below; everything else in your
claim workflow (auth, DB writes, weather check, PDF trigger) stays
the same.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.classifier_service import classify_crop_image, is_model_ready

router = APIRouter()


@router.post("/claims/{claim_id}/classify-image")
async def classify_claim_image(claim_id: str, file: UploadFile = File(...)):
    if not is_model_ready():
        raise HTTPException(
            status_code=503,
            detail="Crop-damage model is not trained yet. Run `python train.py` in ml/.",
        )

    image_bytes = await file.read()

    try:
        result = classify_crop_image(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # --- existing claim workflow continues here, e.g.: ---
    # claim = get_claim(claim_id)
    # claim.ai_prediction = result["prediction"]
    # claim.ai_confidence = result["confidence"]
    # save_claim(claim)
    # generate_evidence_pdf(claim, classifier_result=result)

    return {
        "claim_id": claim_id,
        "prediction": result["prediction"],
        "confidence": result["confidence"],
        "all_probabilities": result["all_probabilities"],
        "disclaimer": result["disclaimer"],
    }
