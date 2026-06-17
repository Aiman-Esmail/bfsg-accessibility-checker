"""
pdf_report.py
PDF-Berichtsgenerator fuer den BFSG Accessibility Checker.

Kombiniert die rohen Scan-Daten (scanner.py) und den KI-Erklaerungsbericht
(ai_report.py) zu einem professionellen, kundenfertigen PDF-Bericht.

Verwendung:
    from scanner import scan_url
    from ai_report import generate_report
    from pdf_report import create_pdf_report

    scan = scan_url("https://example.com")
    report = generate_report(scan)
    create_pdf_report(scan, report, "bericht.pdf")
"""

from datetime import datetime
from xml.sax.saxutils import escape as _xml_escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

# Markenfarben
COLOR_PRIMARY = colors.HexColor("#1B4965")   # Dunkelblau, professionell
COLOR_ACCENT = colors.HexColor("#5FA8D3")    # Helleres Blau fuer Akzente
RISK_COLORS = {
    "Hoch": colors.HexColor("#C1121F"),
    "Mittel": colors.HexColor("#E07A12"),
    "Niedrig": colors.HexColor("#2D6A4F"),
    "Unbekannt": colors.HexColor("#6C757D"),
}
IMPACT_ROW_COLORS = {
    "Kritisch": colors.HexColor("#FBE9E7"),
    "Schwerwiegend": colors.HexColor("#FFF3E0"),
    "Mittel": colors.HexColor("#FFFDE7"),
    "Gering": colors.HexColor("#F1F8E9"),
}


def _esc(text) -> str:
    """
    Escaped dynamischen Text (z.B. von der KI generiert) fuer die sichere
    Verwendung in ReportLab Paragraph-Objekten. Ohne dies wuerde Text, der
    HTML-Tags erwaehnt (z.B. "Fuegen Sie dem <img>-Tag ein alt hinzu"),
    den ReportLab Mini-XML-Parser zum Absturz bringen.
    """
    if text is None:
        return ""
    return _xml_escape(str(text))


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", fontSize=20, leading=24, textColor=COLOR_PRIMARY,
        spaceAfter=4, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="SubTitle", fontSize=11, leading=14, textColor=colors.HexColor("#555555"),
        spaceAfter=16,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", fontSize=14, leading=18, textColor=COLOR_PRIMARY,
        spaceBefore=18, spaceAfter=8, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="BodyDE", fontSize=10.5, leading=15, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="IssueTitle", fontSize=11.5, leading=15, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1A1A1A"), spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="IssueMeta", fontSize=9, leading=12, textColor=colors.HexColor("#666666"),
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="FixBox", fontSize=10, leading=14, backColor=colors.HexColor("#EEF6FB"),
        borderPadding=6, spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        name="Disclaimer", fontSize=8.5, leading=12, textColor=colors.HexColor("#777777"),
    ))
    return styles


def _risk_badge(risk_level: str, styles) -> Table:
    color = RISK_COLORS.get(risk_level, RISK_COLORS["Unbekannt"])
    style = ParagraphStyle(
        name="RiskBadgeText", fontSize=12, fontName="Helvetica-Bold",
        textColor=colors.white, alignment=TA_CENTER,
    )
    t = Table([[Paragraph(f"Risikostufe: {risk_level}", style)]], colWidths=[6 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


def _summary_table(scan_result: dict, styles) -> Table:
    summary = scan_result.get("summary", {})
    header = ["Schweregrad", "Anzahl betroffener Elemente"]
    rows = [header]
    for level in ["Kritisch", "Schwerwiegend", "Mittel", "Gering"]:
        rows.append([level, str(summary.get(level, 0))])

    t = Table(rows, colWidths=[8 * cm, 8 * cm])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for i, level in enumerate(["Kritisch", "Schwerwiegend", "Mittel", "Gering"], start=1):
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), IMPACT_ROW_COLORS[level]))
    t.setStyle(TableStyle(style_cmds))
    return t


def create_pdf_report(scan_result: dict, ai_report: dict, output_path: str) -> str:
    """
    Erstellt einen PDF-Bericht aus den Scan-Ergebnissen und dem KI-Bericht.

    Args:
        scan_result: Ergebnis von scanner.scan_url()
        ai_report: Ergebnis von ai_report.generate_report()
        output_path: Pfad, unter dem die PDF-Datei gespeichert wird

    Returns:
        Der output_path (zur Verkettung)
    """
    styles = _build_styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )
    story = []

    # --- Kopfbereich ---
    story.append(Paragraph("Barrierefreiheits-Bericht (BFSG)", styles["ReportTitle"]))
    story.append(Paragraph(
        f"Gepruefte Seite: {_esc(scan_result.get('url', '-'))}<br/>"
        f"Datum: {datetime.now().strftime('%d.%m.%Y')}",
        styles["SubTitle"],
    ))
    story.append(_risk_badge(ai_report.get("risk_level", "Unbekannt"), styles))
    story.append(Spacer(1, 16))

    # --- Management Summary ---
    story.append(Paragraph("Zusammenfassung", styles["SectionHeading"]))
    story.append(Paragraph(_esc(ai_report.get("executive_summary", "")), styles["BodyDE"]))
    if ai_report.get("estimated_effort"):
        story.append(Paragraph(
            f"<b>Geschaetzter Aufwand:</b> {_esc(ai_report['estimated_effort'])}",
            styles["BodyDE"],
        ))

    # --- Uebersichtstabelle ---
    story.append(Paragraph("Uebersicht nach Schweregrad", styles["SectionHeading"]))
    story.append(_summary_table(scan_result, styles))
    story.append(Spacer(1, 10))

    # --- Detaillierte Befunde ---
    issues = ai_report.get("issues", [])
    if issues:
        story.append(Paragraph("Detaillierte Befunde", styles["SectionHeading"]))
        for issue in issues:
            story.append(Paragraph(
                f"{_esc(issue.get('priority', '-'))}. {_esc(issue.get('title_de', issue.get('id', '')))}",
                styles["IssueTitle"],
            ))
            story.append(Paragraph(
                f"Betroffene Elemente: {_esc(issue.get('affected_elements_count', '-'))} "
                f"&nbsp;|&nbsp; Technische ID: {_esc(issue.get('id', '-'))}",
                styles["IssueMeta"],
            ))
            story.append(Paragraph(_esc(issue.get("why_it_matters_de", "")), styles["BodyDE"]))
            story.append(Paragraph(
                f"<b>Empfohlene Massnahme:</b> {_esc(issue.get('fix_suggestion_de', ''))}",
                styles["FixBox"],
            ))
        story.append(Spacer(1, 6))

    # --- Disclaimer ---
    story.append(HRFlowable(width="100%", color=colors.HexColor("#CCCCCC"), spaceBefore=8, spaceAfter=8))
    story.append(Paragraph(
        "Dieser Bericht basiert auf einem automatisierten technischen Scan (axe-core, "
        "WCAG 2.1 AA) und stellt keine rechtliche Bestaetigung der vollstaendigen BFSG-"
        "Konformitaet dar. Automatisierte Tests erkennen einen relevanten Teil der "
        "WCAG-Kriterien, jedoch nicht alle - eine zusaetzliche manuelle Pruefung wird "
        "empfohlen.",
        styles["Disclaimer"],
    ))

    doc.build(story)
    return output_path


if __name__ == "__main__":
    import sys
    import json
    from scanner import scan_url
    from ai_report import generate_report

    target = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/test_page.html"
    out = sys.argv[2] if len(sys.argv) > 2 else "bericht.pdf"

    scan = scan_url(target)
    report = generate_report(scan)
    path = create_pdf_report(scan, report, out)
    print(f"PDF erstellt: {path}")
