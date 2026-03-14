from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def build_exp_items_pdf(out_path: Path, shop_name: str, info_date: str, exp_items: list[dict]):
    out_path = Path(out_path)
    c = canvas.Canvas(str(out_path), pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w / 2, h - 25 * mm, shop_name)

    c.setFont("Helvetica", 11)
    c.drawCentredString(w / 2, h - 33 * mm, f"Information Date: {info_date}")

    left = 20 * mm
    top = h - 45 * mm
    row_h = 8 * mm
    col1 = 85 * mm
    col2 = 45 * mm
    col3 = 35 * mm

    c.setFont("Helvetica-Bold", 11)
    c.rect(left, top, col1, row_h)
    c.rect(left + col1, top, col2, row_h)
    c.rect(left + col1 + col2, top, col3, row_h)

    c.drawString(left + 2 * mm, top + 2.2 * mm, "Name")
    c.drawString(left + col1 + 2 * mm, top + 2.2 * mm, "EXP.D")
    c.drawString(left + col1 + col2 + 2 * mm, top + 2.2 * mm, "AMOUNT")

    c.setFont("Helvetica", 10)
    y = top - row_h

    for i in range(25):
        item = exp_items[i] if i < len(exp_items) else None

        c.rect(left, y, col1, row_h)
        c.rect(left + col1, y, col2, row_h)
        c.rect(left + col1 + col2, y, col3, row_h)

        if item:
            name = str(item.get("name", ""))[:45]
            exp_d = str(item.get("exp_d", ""))[:15]
            amt = str(item.get("amount", ""))

            c.drawString(left + 2 * mm, y + 2.2 * mm, name)
            c.drawString(left + col1 + 2 * mm, y + 2.2 * mm, exp_d)
            c.drawRightString(left + col1 + col2 + col3 - 2 * mm, y + 2.2 * mm, amt)

        y -= row_h

    c.setFont("Helvetica", 11)
    c.drawString(left, 18 * mm, "Checked By: ________________________________")

    c.showPage()
    c.save()
    return out_path


def build_fast_items_pdf(
    out_path: Path,
    shop_name: str,
    date_str: str,
    time_str: str,
    inspector: str,
    fast_items: list[dict],
    message: str
):
    out_path = Path(out_path)
    c = canvas.Canvas(str(out_path), pagesize=A4)
    w, h = A4

    left = 18 * mm
    right = w - 18 * mm

    # Header
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(w / 2, h - 20 * mm, "FAST ITEMS / MESSAGE REPORT")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, h - 32 * mm, "Shop :")
    c.drawString(left, h - 40 * mm, "Date :")
    c.drawString(left, h - 48 * mm, "Time :")
    c.drawString(left, h - 56 * mm, "Inspector :")

    c.setFont("Helvetica", 11)
    c.drawString(left + 24 * mm, h - 32 * mm, str(shop_name))
    c.drawString(left + 24 * mm, h - 40 * mm, str(date_str))
    c.drawString(left + 24 * mm, h - 48 * mm, str(time_str))
    c.drawString(left + 24 * mm, h - 56 * mm, str(inspector))

    # Table
    top = h - 72 * mm
    row_h = 8 * mm
    col1 = 70 * mm
    col2 = 45 * mm
    col3 = 30 * mm
    col4 = 30 * mm

    c.setFont("Helvetica-Bold", 10.5)
    c.rect(left, top, col1, row_h)
    c.rect(left + col1, top, col2, row_h)
    c.rect(left + col1 + col2, top, col3, row_h)
    c.rect(left + col1 + col2 + col3, top, col4, row_h)

    c.drawString(left + 2 * mm, top + 2.2 * mm, "Fast Item")
    c.drawString(left + col1 + 2 * mm, top + 2.2 * mm, "Brand")
    c.drawString(left + col1 + col2 + 2 * mm, top + 2.2 * mm, "Discount")
    c.drawString(left + col1 + col2 + col3 + 2 * mm, top + 2.2 * mm, "Price")

    c.setFont("Helvetica", 10)
    y = top - row_h

    # 9 rows
    for i in range(9):
        item = fast_items[i] if i < len(fast_items) else None

        c.rect(left, y, col1, row_h)
        c.rect(left + col1, y, col2, row_h)
        c.rect(left + col1 + col2, y, col3, row_h)
        c.rect(left + col1 + col2 + col3, y, col4, row_h)

        if item:
            item_name = str(item.get("item_name", ""))[:35]
            brand_name = str(item.get("brand_name", ""))[:20]
            discount = str(item.get("discount", ""))[:12]
            price = str(item.get("price", ""))

            c.drawString(left + 2 * mm, y + 2.2 * mm, item_name)
            c.drawString(left + col1 + 2 * mm, y + 2.2 * mm, brand_name)
            c.drawString(left + col1 + col2 + 2 * mm, y + 2.2 * mm, discount)
            c.drawRightString(left + col1 + col2 + col3 + col4 - 2 * mm, y + 2.2 * mm, price)

        y -= row_h

    # Message title
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y - 6 * mm, "Message")

    # Big message box
    msg_top = y - 10 * mm
    msg_h = 42 * mm
    msg_w = right - left
    c.rect(left, msg_top - msg_h, msg_w, msg_h)

    c.setFont("Helvetica", 10)
    text = c.beginText(left + 3 * mm, msg_top - 5 * mm)
    text.setLeading(13)

    message_lines = (message or "").splitlines() or [""]
    for line in message_lines:
        text.textLine(line[:120])
    c.drawText(text)

    # Checked By
    c.setFont("Helvetica", 11)
    c.drawString(left, 16 * mm, "Checked By: ________________________________")

    c.showPage()
    c.save()
    return out_path