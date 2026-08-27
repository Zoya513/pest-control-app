"""PDF / Excel report generators."""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from openpyxl import Workbook


DEFAULT_COMPANY_NAME = "Proteksi Pest Control"
DEFAULT_COMPANY_ADDR = "Komplek Pondok Cibubur Blok B2 No.10, Cimanggis, Depok 16452"
DEFAULT_COMPANY_EMAIL = "proteksipestcontrol@gmail.com"

SERVICE_TREATMENTS = [
    "Spraying", "Cold Fogging", "Misting Blower", "Booster Spraying",
    "Hot Fogging", "Insect Gel Baiting", "Flying Insect Trap",
    "Crawling Insect Trap", "Rodent Baiting", "Rodent Trapping", "Other",
]


def _brand_header(brand: dict = None):
    """Header: logo left, company info right, then centered SERVICE REPORT title."""
    b = brand or {}
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenterTitle", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=16, spaceAfter=4))
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="CompanyName", parent=styles["Normal"], fontSize=12, leading=14, textColor=colors.HexColor("#10B981"), fontName="Helvetica-Bold"))

    company_name = b.get("company_name") or DEFAULT_COMPANY_NAME
    company_addr = b.get("company_address") or DEFAULT_COMPANY_ADDR
    company_email = b.get("company_email") or DEFAULT_COMPANY_EMAIL

    # Logo cell (compact)
    logo_cell = ""
    logo_data = b.get("logo_bytes")
    if logo_data:
        try:
            logo_cell = Image(io.BytesIO(logo_data), width=20 * mm, height=20 * mm)
        except Exception:
            logo_cell = Paragraph(f"<b>{company_name.split()[0]}</b>", styles["CompanyName"])
    else:
        logo_cell = Paragraph(f"<b>{company_name.split()[0].upper()}</b>", styles["CompanyName"])

    info_cell = [
        Paragraph(f"<b>{company_name}</b>", styles["CompanyName"]),
        Paragraph(company_addr, styles["Small"]),
        Paragraph(f"E-mail: {company_email}", styles["Small"]),
    ]

    header_tbl = Table([[logo_cell, info_cell]], colWidths=[28 * mm, 150 * mm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [header_tbl,
            Table([[""]], colWidths=[178 * mm], style=TableStyle([("LINEABOVE", (0, 0), (-1, 0), 1.5, colors.HexColor("#10B981"))])),
            Spacer(1, 4 * mm)]


def generate_service_report_pdf(sr: dict, task: dict, customer: dict, technician: dict,
                                brand: dict = None, sig_bytes: dict = None) -> bytes:
    """Follows Proteksi Pest Control reference template layout.
    sig_bytes = {'tech': b'...', 'client': b'...', 'photos': [(bytes, caption), ...]}
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=12 * mm, bottomMargin=12 * mm,
                            leftMargin=15 * mm, rightMargin=15 * mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=15, spaceAfter=4))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading4"], fontSize=10, textColor=colors.HexColor("#10B981"), spaceAfter=2))
    styles.add(ParagraphStyle(name="Cell", parent=styles["Normal"], fontSize=9, leading=11))
    story = _brand_header(brand)

    # Centered title
    story.append(Paragraph("<b>SERVICE REPORT</b>", styles["ReportTitle"]))
    story.append(Spacer(1, 2 * mm))

    # Date / Time / Report No
    meta = Table([
        ["DATE", sr.get("date", ""), "TIME", sr.get("time", ""), "REPORT NO", sr.get("report_number", "")],
    ], colWidths=[18 * mm, 30 * mm, 15 * mm, 25 * mm, 22 * mm, 68 * mm])
    meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, 0), "Helvetica-Bold"),
        ("FONTNAME", (4, 0), (4, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F3F4F6")),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#F3F4F6")),
        ("BACKGROUND", (4, 0), (4, 0), colors.HexColor("#F3F4F6")),
    ]))
    story.append(meta)
    story.append(Spacer(1, 3 * mm))

    # CLIENT INFORMATION
    story.append(Paragraph("<b>CLIENT INFORMATION</b>", styles["Section"]))
    client_rows = [
        ["NAME", ":", customer.get("company_name", "")],
        ["POSITION", ":", customer.get("project_name") or customer.get("contact_person", "")],
        ["LOCATION", ":", customer.get("address", "")],
    ]
    ct = Table(client_rows, colWidths=[25 * mm, 5 * mm, 148 * mm])
    ct.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold")]))
    story.append(ct)
    story.append(Spacer(1, 3 * mm))

    # AUTHORIZED PERSONNEL
    story.append(Paragraph("<b>AUTHORIZED PERSONNEL</b>", styles["Section"]))
    pers = Table([
        ["NAME", ":", technician.get("full_name", "")],
        ["POSITION", ":", technician.get("position", "")],
    ], colWidths=[25 * mm, 5 * mm, 148 * mm])
    pers.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold")]))
    story.append(pers)
    story.append(Spacer(1, 3 * mm))

    # SCOPE OF AREAS
    story.append(Paragraph("<b>SCOPE OF AREAS</b>", styles["Section"]))
    story.append(Paragraph(sr.get("scope_of_area", "") or "-", styles["Cell"]))
    story.append(Spacer(1, 3 * mm))

    # KIND OF PEST
    story.append(Paragraph("<b>KIND OF PEST</b>", styles["Section"]))
    findings = sr.get("pest_findings") or []
    fmap = {f["code"]: f for f in findings}
    rows = [["KODE", "JENIS HAMA", "KETERANGAN HAMA", "JUMLAH TEMUAN (EKOR)"]]
    for code, name in [("F", "Fly"), ("M", "Mosquito"), ("C", "Cockroach"), ("A", "Ant"), ("R", "Rat"), ("O", "Other")]:
        f = fmap.get(code, {})
        rows.append([code, name, f.get("description", ""), str(f.get("quantity", "") or "")])
    pt = Table(rows, colWidths=[18 * mm, 32 * mm, 88 * mm, 40 * mm])
    pt.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
    ]))
    story.append(pt)
    story.append(Spacer(1, 3 * mm))

    # INSPECTION
    story.append(Paragraph("<b>INSPECTION</b>", styles["Section"]))
    story.append(Paragraph(sr.get("service_area", "") or sr.get("pest_description", "") or "-", styles["Cell"]))
    story.append(Spacer(1, 3 * mm))

    # SERVICE TREATMENT
    story.append(Paragraph("<b>SERVICE TREATMENT</b>", styles["Section"]))
    treatments = sr.get("service_treatments") or []
    tmap = {t.get("name"): t.get("area_description", "") for t in treatments if isinstance(t, dict)}
    tr_rows = [["SERVICE TREATMENT", "SERVICE AREA"]]
    for name in SERVICE_TREATMENTS:
        tr_rows.append([name, tmap.get(name, "")])
    tt = Table(tr_rows, colWidths=[55 * mm, 123 * mm])
    tt.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(tt)
    story.append(Spacer(1, 3 * mm))

    # RECOMMENDATION
    story.append(Paragraph("<b>RECOMMENDATION</b>", styles["Section"]))
    story.append(Paragraph(sr.get("recommendation", "") or "-", styles["Cell"]))
    story.append(Spacer(1, 8 * mm))

    # SIGNATURE BLOCK
    tech_sig_cell = ""
    client_sig_cell = ""
    if sig_bytes and sig_bytes.get("tech"):
        try:
            tech_sig_cell = Image(io.BytesIO(sig_bytes["tech"]), width=50 * mm, height=18 * mm)
        except Exception:
            pass
    if sig_bytes and sig_bytes.get("client"):
        try:
            client_sig_cell = Image(io.BytesIO(sig_bytes["client"]), width=50 * mm, height=18 * mm)
        except Exception:
            pass

    sig_rows = [
        ["SERVICE TECHNICIAN", "ACKNOWLEDGE BY USER"],
        [tech_sig_cell, client_sig_cell],
        [technician.get("full_name", ""), customer.get("contact_person", "")],
    ]
    st = Table(sig_rows, colWidths=[89 * mm, 89 * mm], rowHeights=[8 * mm, 22 * mm, 8 * mm])
    st.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 1), (-1, 1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
    ]))
    story.append(st)

    # PAGE 2: Photo documentation
    photos = sig_bytes.get("photos", []) if sig_bytes else []
    if photos:
        story.append(PageBreak())
        story.extend(_brand_header(brand))
        story.append(Paragraph("<b>PHOTO DOCUMENTATION</b>", styles["ReportTitle"]))
        story.append(Spacer(1, 3 * mm))
        # 2-col grid of photos with captions
        rows = []
        for i in range(0, len(photos), 2):
            row_cells = []
            for j in range(2):
                if i + j < len(photos):
                    pb, cap = photos[i + j]
                    try:
                        img = Image(io.BytesIO(pb), width=80 * mm, height=55 * mm)
                    except Exception:
                        img = Paragraph("(image error)", styles["Cell"])
                    cell = [img, Paragraph(f"<b>Foto - {i + j + 1}:</b> {cap or ''}", styles["Cell"])]
                    row_cells.append(cell)
                else:
                    row_cells.append("")
            rows.append(row_cells)
        pgrid = Table(rows, colWidths=[89 * mm, 89 * mm])
        pgrid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story.append(pgrid)

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


def generate_simple_pdf(title: str, headers: list, rows: list, brand: dict = None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=12 * mm, bottomMargin=12 * mm,
                            leftMargin=15 * mm, rightMargin=15 * mm)
    styles = getSampleStyleSheet()
    story = _brand_header(brand)
    story.append(Paragraph(f"<b>{title}</b>", ParagraphStyle("t", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=14)))
    story.append(Spacer(1, 4 * mm))
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
