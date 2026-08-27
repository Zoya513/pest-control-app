"""PDF / Excel report generators."""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from openpyxl import Workbook


COMPANY_NAME = "Proteksi Pest Control"
COMPANY_ADDR = "Komplek Pondok Cibubur Blok B2 No.10, Cimanggis, Depok 16452"


def _header_para(title: str):
    styles = getSampleStyleSheet()
    return [
        Paragraph(f"<b>{COMPANY_NAME}</b>", styles["Title"]),
        Paragraph(COMPANY_ADDR, styles["Normal"]),
        Paragraph(f"<b>{title}</b>", styles["Heading2"]),
        Spacer(1, 6 * mm),
    ]


def generate_service_report_pdf(sr: dict, task: dict, customer: dict, technician: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8)
    story = _header_para("SERVICE REPORT")

    # Metadata
    meta = [
        ["Report No", sr.get("report_number", ""), "Date", sr.get("date", "")],
        ["Task ID", task.get("id", "")[:8], "Time", sr.get("time", "")],
    ]
    t = Table(meta, colWidths=[30 * mm, 60 * mm, 25 * mm, 60 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(t)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>CLIENT INFORMATION</b>", styles["Heading4"]))
    client_tbl = Table([
        ["Name", customer.get("company_name", "")],
        ["Contact Person", customer.get("contact_person", "")],
        ["Location", customer.get("address", "")],
    ], colWidths=[35 * mm, 140 * mm])
    client_tbl.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(client_tbl)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>AUTHORIZED PERSONNEL</b>", styles["Heading4"]))
    p_tbl = Table([
        ["Technician", technician.get("full_name", "")],
        ["Position", technician.get("position", "")],
    ], colWidths=[35 * mm, 140 * mm])
    p_tbl.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(p_tbl)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>SCOPE OF AREAS</b>", styles["Heading4"]))
    story.append(Paragraph(sr.get("scope_of_area", "") or "-", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    # Pest findings
    story.append(Paragraph("<b>KIND OF PEST / PEST FINDINGS</b>", styles["Heading4"]))
    findings = sr.get("pest_findings") or []
    fmap = {f["code"]: f for f in findings}
    rows = [["Code", "Pest Type", "Description", "Quantity"]]
    for code, name in [("F", "Fly"), ("M", "Mosquito"), ("C", "Cockroach"), ("A", "Ant"), ("R", "Rodent"), ("O", "Other")]:
        f = fmap.get(code, {})
        rows.append([code, name, f.get("description", ""), str(f.get("quantity", ""))])
    pt = Table(rows, colWidths=[15 * mm, 30 * mm, 90 * mm, 30 * mm])
    pt.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(pt)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>INSPECTION / SERVICE AREA</b>", styles["Heading4"]))
    story.append(Paragraph(sr.get("service_area", "") or "-", styles["Normal"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("<b>PEST DESCRIPTION</b>", styles["Heading4"]))
    story.append(Paragraph(sr.get("pest_description", "") or "-", styles["Normal"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("<b>RECOMMENDATION</b>", styles["Heading4"]))
    story.append(Paragraph(sr.get("recommendation", "") or "-", styles["Normal"]))
    story.append(Spacer(1, 8 * mm))

    sig_rows = [["SERVICE TECHNICIAN", "ACKNOWLEDGE BY USER"],
                [technician.get("full_name", ""), customer.get("contact_person", "")]]
    st = Table(sig_rows, colWidths=[87 * mm, 87 * mm], rowHeights=[8 * mm, 20 * mm])
    st.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 9), ("VALIGN", (0, 1), (-1, 1), "BOTTOM")]))
    story.append(st)

    doc.build(story)
    return buf.getvalue()


def generate_attendance_excel(rows: list) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance"
    ws.append(["Employee", "Check-in Date", "Check-in Time", "Check-out Date", "Check-out Time", "Working Hours", "Location"])
    for r in rows:
        ws.append([
            r.get("employee_name", ""),
            r.get("checkin_date", ""), r.get("checkin_time", ""),
            r.get("checkout_date", ""), r.get("checkout_time", ""),
            r.get("working_hours", ""), r.get("location", ""),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def generate_simple_pdf(title: str, headers: list, rows: list) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    story = _header_para(title)
    data = [headers] + rows
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    doc.build(story)
    return buf.getvalue()


def generate_simple_excel(sheet_name: str, headers: list, rows: list) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]
    ws.append(headers)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
