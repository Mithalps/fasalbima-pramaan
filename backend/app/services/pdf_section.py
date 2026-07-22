"""
pdf_section.py
==============
Builds the "AI Crop Damage Assessment" section for the evidence PDF,
replacing the previous "AI Plant Disease Detection" (Healthy/Powdery/
Rust) section.

Your existing PDF generation module was not included in the upload, so
this is written as a standalone, framework-typical ReportLab
(Platypus) section -- the most common library for structured PDF
reports in Python/FastAPI projects. Two integration paths are given
below depending on how your generator is built.

OUTPUT LOOKS LIKE
-----------------
    AI Crop Damage Assessment

    Prediction:     Flood Damage
    Confidence:     94.3%

    Disclaimer: Experimental AI prediction. Used as supplementary
    evidence only.
"""

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

_styles = getSampleStyleSheet()

_heading_style = ParagraphStyle(
    "AICropHeading",
    parent=_styles["Heading2"],
    textColor=colors.HexColor("#1B4332"),
    spaceAfter=6,
)

_disclaimer_style = ParagraphStyle(
    "AICropDisclaimer",
    parent=_styles["Normal"],
    fontSize=8,
    textColor=colors.HexColor("#6B7280"),
    fontName="Helvetica-Oblique",
    spaceBefore=6,
)


def build_ai_assessment_flowables(classifier_result: dict) -> list:
    """
    Returns a list of ReportLab flowables (Paragraph/Table/Spacer) for
    the "AI Crop Damage Assessment" section.

    Args:
        classifier_result: the dict returned by
            classifier_service.classify_crop_image(), e.g.:
            {
                "prediction": "Flood Damage",
                "confidence": 94.3,
                "all_probabilities": {...},
                "disclaimer": "Experimental AI prediction. ..."
            }

    Usage (Platypus / SimpleDocTemplate-based generators):
        story = [...]  # your existing flowables
        story += build_ai_assessment_flowables(classifier_result)
        doc.build(story)
    """
    prediction = classifier_result["prediction"]
    confidence = classifier_result["confidence"]
    disclaimer = classifier_result.get(
        "disclaimer",
        "Experimental AI prediction. Used as supplementary evidence only.",
    )

    flowables = [
        Paragraph("AI Crop Damage Assessment", _heading_style),
        Spacer(1, 4),
    ]

    table_data = [
        ["Prediction:", prediction],
        ["Confidence:", f"{confidence:.1f}%"],
    ]
    table = Table(table_data, colWidths=[35 * mm, 90 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    flowables.append(table)
    flowables.append(Paragraph(f"Disclaimer: {disclaimer}", _disclaimer_style))
    flowables.append(Spacer(1, 10))

    return flowables


# --------------------------------------------------------------------------- #
# Alternative integration: if your PDF generator uses a low-level Canvas
# (canvas.Canvas(...).drawString(...)) instead of Platypus, use this
# instead -- it draws directly at an (x, y) position you control.
# --------------------------------------------------------------------------- #

def draw_ai_assessment_canvas(c, x: float, y: float, classifier_result: dict) -> float:
    """
    Draws the AI Crop Damage Assessment block directly on a
    reportlab.pdfgen.canvas.Canvas at the given (x, y) top-left position.

    Returns the new y position (below the block) so the caller can
    continue drawing further down the page.
    """
    prediction = classifier_result["prediction"]
    confidence = classifier_result["confidence"]
    disclaimer = classifier_result.get(
        "disclaimer",
        "Experimental AI prediction. Used as supplementary evidence only.",
    )

    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(colors.HexColor("#1B4332"))
    c.drawString(x, y, "AI Crop Damage Assessment")
    y -= 18

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.black)
    c.drawString(x, y, "Prediction:")
    c.setFont("Helvetica", 10)
    c.drawString(x + 80, y, prediction)
    y -= 14

    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, "Confidence:")
    c.setFont("Helvetica", 10)
    c.drawString(x + 80, y, f"{confidence:.1f}%")
    y -= 16

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawString(x, y, f"Disclaimer: {disclaimer}")
    y -= 14

    c.setFillColor(colors.black)
    return y
