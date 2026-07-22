"""
pdf_service.py
===============
Missing assembly layer: builds the final claim-evidence PDF using
SimpleDocTemplate, reusing pdf_section.py's flowables and
classifier_service.py's classify_crop_image().

Section order (fixed):
    1 Farmer Details
    2 Claim Details
    3 Weather Validation
    4 AI Crop Damage Assessment
    5 Uploaded Images
    6 QR Code
    7 Declaration
    8 Signature
    9 Footer

NOTE ON FARMER MODEL: app/models/farmer.py was not included in the
upload, so farmer fields are read defensively via _farmer_field()
below, trying the common attribute-name variants. If your Farmer model
uses different attribute names, adjust the FARMER_FIELD_MAP constant
only -- nothing else needs to change.

Requires `qrcode` in requirements.txt (pip install qrcode[pil]). If it
isn't installed, the QR section is skipped rather than crashing PDF
generation.
"""

import io
import os
from datetime import datetime, timezone
from app.config import settings

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    PageBreak,
)

from app.services.pdf_section import build_ai_assessment_flowables
from app.services.classifier_service import classify_crop_image

try:
    import qrcode
    _QRCODE_AVAILABLE = True
except ImportError:
    _QRCODE_AVAILABLE = False


_styles = getSampleStyleSheet()

_section_heading_style = ParagraphStyle(
    "SectionHeading",
    parent=_styles["Heading1"],
    fontSize=14,
    textColor=colors.HexColor("#1B4332"),
    spaceBefore=14,
    spaceAfter=8,
)

_body_style = ParagraphStyle(
    "Body",
    parent=_styles["Normal"],
    fontSize=10,
    leading=14,
)

_small_style = ParagraphStyle(
    "Small",
    parent=_styles["Normal"],
    fontSize=8,
    textColor=colors.HexColor("#6B7280"),
)

_footer_style = ParagraphStyle(
    "Footer",
    parent=_styles["Normal"],
    fontSize=7,
    textColor=colors.HexColor("#9CA3AF"),
    alignment=1,  # center
)

_LABEL_VALUE_TABLE_STYLE = TableStyle(
    [
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
)


# --------------------------------------------------------------------------- #
# Farmer field access (defensive -- Farmer model wasn't uploaded)
# --------------------------------------------------------------------------- #

FARMER_FIELD_MAP = {
    "Name": ["name", "full_name", "farmer_name"],
    "Phone": ["phone", "phone_number", "mobile_number", "mobile"],
    "Aadhaar Number": ["aadhaar_number", "aadhar_number", "aadhaar", "aadhar"],
    "Address": ["address", "address_line", "full_address"],
    "District": ["district"],
    "Village": ["village"],
    "Land Area": ["land_area", "land_area_acres", "land_size"],
}


def _farmer_field(farmer, attr_candidates):
    for attr in attr_candidates:
        if hasattr(farmer, attr):
            value = getattr(farmer, attr)
            if value not in (None, ""):
                return str(value)
    return "N/A"


def _label_value_table(rows, col_widths=(40 * mm, 110 * mm)):
    table = Table(rows, colWidths=list(col_widths), hAlign="LEFT")
    table.setStyle(_LABEL_VALUE_TABLE_STYLE)
    return table


# --------------------------------------------------------------------------- #
# Section builders
# --------------------------------------------------------------------------- #

def _build_farmer_section(claim) -> list:
    farmer = claim.farmer
    flowables = [Paragraph("1. Farmer Details", _section_heading_style)]

    if farmer is None:
        flowables.append(Paragraph("Farmer record not found.", _body_style))
        return flowables

    rows = []
    for label, candidates in FARMER_FIELD_MAP.items():
        rows.append([f"{label}:", _farmer_field(farmer, candidates)])

    flowables.append(_label_value_table(rows))
    flowables.append(Spacer(1, 6))
    return flowables


def _build_claim_section(claim) -> list:
    flowables = [Paragraph("2. Claim Details", _section_heading_style)]

    damage_type = getattr(claim.damage_type, "value", claim.damage_type)
    status = getattr(claim.status, "value", claim.status)

    rows = [
        ["Claim ID:", claim.claim_id],
        ["Crop Type:", claim.crop_type],
        ["Damage Type:", str(damage_type).replace("_", " ").title()],
        ["Damage Date:", claim.damage_date.isoformat()],
        ["District:", claim.district],
        ["Village:", claim.village],
        ["Status:", str(status).replace("_", " ").title()],
        ["Submitted On:", claim.created_at.strftime("%d %b %Y, %H:%M")],
    ]
    flowables.append(_label_value_table(rows))
    flowables.append(Spacer(1, 6))
    return flowables


def _build_weather_section(claim) -> list:
    flowables = [Paragraph("3. Weather Validation", _section_heading_style)]

    if claim.weather_verified is None and claim.weather_reason is None:
        flowables.append(
            Paragraph(
                "Weather validation was not applicable or unavailable for this claim.",
                _body_style,
            )
        )
        flowables.append(Spacer(1, 6))
        return flowables

    verified_label = {
        True: "Verified",
        False: "Not Corroborated",
        None: "Inconclusive",
    }[claim.weather_verified]

    rows = [["Result:", verified_label]]
    if claim.weather_reason:
        rows.append(["Reason:", claim.weather_reason])
    if claim.precipitation is not None:
        rows.append(["Precipitation (mm):", f"{claim.precipitation:.1f}"])
    if claim.temperature_max is not None:
        rows.append(["Max Temperature (°C):", f"{claim.temperature_max:.1f}"])
    if claim.temperature_min is not None:
        rows.append(["Min Temperature (°C):", f"{claim.temperature_min:.1f}"])
    if claim.windspeed is not None:
        rows.append(["Max Windspeed (km/h):", f"{claim.windspeed:.1f}"])

    flowables.append(_label_value_table(rows))
    flowables.append(Spacer(1, 6))
    return flowables

def _resolve_image_path(evidence):
    path = evidence.file_path

    # Already an absolute path
    if os.path.isabs(path):
        return path

    # Relative to upload directory
    return os.path.join(settings.upload_dir, path)

def _classify_evidence_items(evidence_items) -> list:
    """
    Runs the classifier on each evidence image once and returns a list of
    (evidence, classifier_result_or_None) tuples. classifier_result is None
    if classification failed for that image (e.g. corrupt file) -- the PDF
    still gets built, just without an AI section for that item.
    """
    results = []
    for evidence in evidence_items:
        try:
            image_path = _resolve_image_path(evidence)

            with open(image_path, "rb") as f:
                image_bytes = f.read()
            result = classify_crop_image(image_bytes)
        except Exception:
            import traceback

            print("=" * 80)
            print("AI CLASSIFICATION FAILED")
            print("Image:", image_path)
            traceback.print_exc()
            print("=" * 80)

            result = None
        results.append((evidence, result))
    return results


def _build_ai_assessment_section(classified_evidence) -> list:
    flowables = [Paragraph("4. AI Crop Damage Assessment", _section_heading_style)]

    if not classified_evidence:
        flowables.append(Paragraph("No evidence images were uploaded for this claim.", _body_style))
        flowables.append(Spacer(1, 6))
        return flowables

    for evidence, result in classified_evidence:
        if result is None:
            flowables.append(
                Paragraph(
                    f"Could not classify image: {evidence.file_name}",
                    _small_style,
                )
            )
            flowables.append(Spacer(1, 6))
            continue

        section_flowables = build_ai_assessment_flowables(result)

        thumbnail = None
        try:
            thumbnail = RLImage(_resolve_image_path(evidence), width=30 * mm, height=30 * mm)
        except Exception:
            thumbnail = None

        if thumbnail is not None:
            row_table = Table(
                [[thumbnail, section_flowables]],
                colWidths=[35 * mm, 120 * mm],
            )
            row_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            flowables.append(row_table)
        else:
            flowables.extend(section_flowables)

        flowables.append(Spacer(1, 8))

    return flowables


def _build_images_section(evidence_items) -> list:
    flowables = [Paragraph("5. Uploaded Images", _section_heading_style)]

    if not evidence_items:
        flowables.append(Paragraph("No images uploaded.", _body_style))
        flowables.append(Spacer(1, 6))
        return flowables

    for evidence in evidence_items:
        try:
            img = RLImage(_resolve_image_path(evidence), width=90 * mm, height=67 * mm)
        except Exception:
            flowables.append(
                Paragraph(f"Image unavailable: {evidence.file_name}", _small_style)
            )
            continue

        flowables.append(img)
        flowables.append(Paragraph(evidence.file_name, _small_style))
        flowables.append(
            Paragraph(
                f"Uploaded on {evidence.uploaded_at.strftime('%d %b %Y, %H:%M')}",
                _small_style,
            )
        )
        flowables.append(Spacer(1, 10))

    return flowables


def _build_qr_section(claim) -> list:
    flowables = [Paragraph("6. QR Code", _section_heading_style)]

    if not _QRCODE_AVAILABLE:
        flowables.append(
            Paragraph(
                "QR verification unavailable (qrcode package not installed).",
                _small_style,
            )
        )
        flowables.append(Spacer(1, 6))
        return flowables

    qr_payload = (
        f"FasalBima Pramaan Claim\n"
        f"Claim ID: {claim.claim_id}\n"
        f"Farmer ID: {claim.farmer_id}\n"
        f"Damage Date: {claim.damage_date.isoformat()}"
    )
    qr_img = qrcode.make(qr_payload)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)

    flowables.append(RLImage(buf, width=30 * mm, height=30 * mm))
    flowables.append(
        Paragraph(
            "Scan to verify claim ID and submission details.",
            _small_style,
        )
    )
    flowables.append(Spacer(1, 6))
    return flowables


DECLARATION_TEXT = (
    "I hereby declare that the information and evidence submitted in this "
    "document are true and accurate to the best of my knowledge, and are "
    "provided for the purpose of claim assessment under the Pradhan Mantri "
    "Fasal Bima Yojana (PMFBY). I understand that the AI-based crop damage "
    "assessment included in this document is supplementary evidence only, "
    "and that final claim settlement remains subject to verification by "
    "the insurer and/or an authorized surveyor."
)


def _build_declaration_section() -> list:
    return [
        Paragraph("7. Declaration", _section_heading_style),
        Paragraph(DECLARATION_TEXT, _body_style),
        Spacer(1, 6),
    ]


def _build_signature_section(claim) -> list:
    flowables = [Paragraph("8. Signature", _section_heading_style)]

    rows = [
        ["Farmer Signature:", "____________________________"],
        ["Date:", datetime.now(timezone.utc).strftime("%d %b %Y")],
        ["Insurer / Surveyor Signature:", "____________________________"],
    ]
    flowables.append(_label_value_table(rows))
    flowables.append(Spacer(1, 6))
    return flowables


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#9CA3AF"))
    footer_text = (
        f"FasalBima Pramaan | Auto-generated on "
        f"{datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')} | Page {doc.page}"
    )
    canvas.drawCentredString(A4[0] / 2, 15 * mm, footer_text)
    canvas.restoreState()


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #

def generate_claim_pdf(claim) -> bytes:
    """
    Builds the full evidence PDF for a claim and returns the raw PDF bytes.

    Args:
        claim: a Claim ORM instance with `.farmer` and `.evidence_items`
            relationships already loaded (use joinedload/selectinload in
            the router/service that fetches it to avoid lazy-load issues
            outside the DB session).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=25 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title=f"FasalBima Pramaan Claim {claim.claim_id}",
    )

    evidence_items = list(claim.evidence_items or [])
    classified_evidence = _classify_evidence_items(evidence_items)

    story = []
    story += _build_farmer_section(claim)
    story += _build_claim_section(claim)
    story += _build_weather_section(claim)
    story += _build_ai_assessment_section(classified_evidence)
    story += _build_images_section(evidence_items)
    story += _build_qr_section(claim)
    story += _build_declaration_section()
    story += _build_signature_section(claim)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)

    return buffer.getvalue()

def _resolve_image_path(evidence):
    if os.path.isabs(evidence.file_path):
        return evidence.file_path

    return os.path.join(settings.upload_dir, evidence.file_path)