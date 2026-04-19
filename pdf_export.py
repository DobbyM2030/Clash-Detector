from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_clash_report(output_path, clash_run):
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        rightMargin=0.4 * inch,
        leftMargin=0.4 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#0b1f3a"),
        fontSize=22,
        leading=26,
        spaceAfter=12,
    )
    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=styles["Normal"],
        textColor=colors.HexColor("#334155"),
        fontSize=9,
        leading=12,
    )

    summary = clash_run["summary"]
    clashes = clash_run["clashes"]
    story = [
        Paragraph("BIM Clash Detection Report", title_style),
        Paragraph(f"Source file: {clash_run['filename']}", meta_style),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", meta_style),
        Spacer(1, 0.18 * inch),
    ]

    summary_table = Table(
        [
            ["Critical", "Warning", "Info", "Total"],
            [summary.get("Critical", 0), summary.get("Warning", 0), summary.get("Info", 0), len(clashes)],
        ],
        colWidths=[1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b1f3a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#eef4ff")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([summary_table, Spacer(1, 0.24 * inch)])

    table_data = [["Clash ID", "Severity", "Description", "Location", "Element A", "Element B"]]
    for clash in clashes:
        table_data.append(
            [
                clash["id"],
                clash["severity"],
                Paragraph(clash["description"], styles["BodyText"]),
                clash["location"],
                Paragraph(clash["elementA"], styles["BodyText"]),
                Paragraph(clash["elementB"], styles["BodyText"]),
            ]
        )

    results_table = Table(
        table_data,
        repeatRows=1,
        colWidths=[0.8 * inch, 0.9 * inch, 2.7 * inch, 1.5 * inch, 2.2 * inch, 2.2 * inch],
    )
    results_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b1f3a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d8e0ea")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(results_table)
    document.build(story)
