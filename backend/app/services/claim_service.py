import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ClaimNotFoundError
from app.models.claim import Claim
from app.models.farmer import Farmer
from app.schemas.claim import ClaimCreate, ClaimUpdate
from app.schemas.farmer import FarmerCreate

logger = logging.getLogger("fasalbima.claims")


def get_or_create_farmer(db: Session, farmer_data: FarmerCreate) -> Farmer:
    """
    Looks up a farmer by mobile number (the natural dedup key for this
    domain — one phone number per farmer) and reuses that row if found,
    so a returning farmer filing a second claim doesn't create a duplicate
    farmer record. Creates a new farmer row otherwise.
    """
    existing = db.execute(
        select(Farmer).where(Farmer.mobile_number == farmer_data.mobile_number)
    ).scalar_one_or_none()

    if existing is not None:
        logger.info("Reusing existing farmer id=%s", existing.farmer_id)
        return existing

    farmer = Farmer(
        farmer_name=farmer_data.farmer_name,
        mobile_number=farmer_data.mobile_number,
    )
    db.add(farmer)
    db.flush()  # assigns farmer.farmer_id without committing the transaction yet
    logger.info("Created new farmer id=%s", farmer.farmer_id)
    return farmer


def create_claim(db: Session, claim_data: ClaimCreate) -> Claim:
    farmer = get_or_create_farmer(db, claim_data.farmer)

    claim = Claim(
        farmer_id=farmer.farmer_id,
        crop_type=claim_data.crop_type,
        damage_type=claim_data.damage_type,
        damage_date=claim_data.damage_date,
        district=claim_data.district,
        village=claim_data.village,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    logger.info(
        "Claim created id=%s farmer_id=%s damage_type=%s",
        claim.claim_id,
        farmer.farmer_id,
        claim.damage_type.value,
    )
    return claim


def list_claims(db: Session, skip: int = 0, limit: int = 50) -> list[Claim]:
    result = db.execute(
        select(Claim).order_by(Claim.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


def get_claim(db: Session, claim_id: str) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None:
        logger.warning("Claim lookup failed id=%s", claim_id)
        raise ClaimNotFoundError(claim_id)
    return claim


def update_claim(db: Session, claim_id: str, update_data: ClaimUpdate) -> Claim:
    claim = get_claim(db, claim_id)

    # Only overwrite fields the caller actually sent (exclude_unset=True),
    # so an omitted field keeps its current value rather than being reset.
    changes = update_data.model_dump(exclude_unset=True)
    for field_name, value in changes.items():
        setattr(claim, field_name, value)

    db.commit()
    db.refresh(claim)
    logger.info("Claim updated id=%s fields=%s", claim_id, list(changes.keys()))
    return claim


def delete_claim(db: Session, claim_id: str) -> None:
    claim = get_claim(db, claim_id)
    db.delete(claim)
    db.commit()
    logger.info("Claim deleted id=%s", claim_id)
