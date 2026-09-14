import win32print
import win32gui
import win32con
import requests
import time
import sys
import traceback

printer = win32print.GetDefaultPrinter()

BASE_URL = "https://api.blino.ir/api/company/get-load/"

PAGE_WIDTH = 560
ROW_H = 48
FONT_SIZE = 25
SMALL_FONT_SIZE = 16
SMALL_ROW_H = 30


def get_font(size, weight=400):
    lf = win32gui.LOGFONT()
    lf.lfHeight = -size
    lf.lfWidth = 0
    lf.lfWeight = weight
    lf.lfItalic = 0
    lf.lfUnderline = 0
    lf.lfStrikeOut = 0
    lf.lfCharSet = win32con.DEFAULT_CHARSET
    lf.lfOutPrecision = win32con.OUT_DEFAULT_PRECIS
    lf.lfClipPrecision = win32con.CLIP_DEFAULT_PRECIS
    lf.lfQuality = win32con.DEFAULT_QUALITY
    lf.lfPitchAndFamily = win32con.DEFAULT_PITCH | win32con.FF_DONTCARE
    lf.lfFaceName = "Tahoma"
    return win32gui.CreateFontIndirect(lf)


def line(hdc, x1, y1, x2, y2):
    win32gui.MoveToEx(hdc, x1, y1)
    win32gui.LineTo(hdc, x2, y2)


def cell(hdc, text, x_left, x_right, y, h, align=None):
    try:
        if align is None:
            align = win32con.DT_CENTER
        rect = (x_left, y, x_right, y + h)
        win32gui.DrawText(hdc, str(text) if text is not None else "-", -1, rect,
                          align | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
    except Exception as e:
        print("Draw error:", e)


def row_border(hdc, x_left, x_right, y, h, col_xs):
    line(hdc, x_left, y, x_right, y)
    line(hdc, x_left, y + h, x_right, y + h)
    line(hdc, x_left, y, x_left, y + h)
    line(hdc, x_right, y, x_right, y + h)
    for x in col_xs:
        line(hdc, x, y, x, y + h)


def draw_pair_row(hdc, y, label1, value1, label2=None, value2=None, h=ROW_H):
    x0, xm, x1 = 0, PAGE_WIDTH // 2, PAGE_WIDTH
    cols = [] if label2 is None else [xm]
    row_border(hdc, x0, x1, y, h, cols)
    cell(hdc, f"{label1}: {value1}", xm if label2 is not None else x0, x1, y, h)
    if label2 is not None:
        cell(hdc, f"{label2}: {value2}", x0, xm, y, h)
    return y + h


def draw_full_row(hdc, y, text, h=ROW_H, align=None):
    x0, x1 = 0, PAGE_WIDTH
    row_border(hdc, x0, x1, y, h, [])
    cell(hdc, text, x0, x1, y, h, align=align or win32con.DT_RIGHT)
    return y + h


def text_width(hdc, text):
    return win32gui.GetTextExtentPoint32(hdc, str(text))[0]


def draw_fields(hdc, y, fields, h=ROW_H, padding=20):
    half = PAGE_WIDTH // 2
    i = 0
    n = len(fields)
    while i < n:
        label1, value1 = fields[i]
        text1 = f"{label1}: {value1}"
        w1 = text_width(hdc, text1) + padding

        if i + 1 < n:
            label2, value2 = fields[i + 1]
            text2 = f"{label2}: {value2}"
            w2 = text_width(hdc, text2) + padding
            if w1 <= half and w2 <= half:
                y = draw_pair_row(hdc, y, label1, value1, label2, value2, h)
                i += 2
                continue

        y = draw_full_row(hdc, y, text1, h)
        i += 1

    return y


def print_packages_table(hdc, ticket, y):
    x0, x1 = 0, PAGE_WIDTH
    col1 = PAGE_WIDTH * 2 // 3
    col2 = PAGE_WIDTH * 1 // 3

    row_border(hdc, x0, x1, y, ROW_H, [col2, col1])
    cell(hdc, "تعداد", col1, x1, y, ROW_H)
    cell(hdc, "ردیف", col2, col1, y, ROW_H)
    cell(hdc, "نوع", x0, col2, y, ROW_H)
    y += ROW_H

    for item in ticket["packages"]:
        row_border(hdc, x0, x1, y, ROW_H, [col2, col1])
        cell(hdc, item['count'], col1, x1, y, ROW_H)
        cell(hdc, item['id'], col2, col1, y, ROW_H)
        cell(hdc, item['type'], x0, col2, y, ROW_H)
        y += ROW_H

    return y


def print_prices_table(hdc, ticket, y, fonts):
    fields = [
        ("ارزش محصول", f"{ticket['marsoolPrice']} ر"),
        ("روش پرداخت", ticket['paymentMethod']),
        ("تخفیف", f"{ticket['discountPrecentage']}%"),
        ("مبلغ کل", f"{ticket['priceKoll']} ر"),
    ]
    y = draw_fields(hdc, y, fields)

    description = ticket.get('description')
    if description:
        win32gui.SelectObject(hdc, fonts["small"])
        y = draw_full_row(hdc, y, description, h=SMALL_ROW_H)
        win32gui.SelectObject(hdc, fonts["main"])

    win32gui.SelectObject(hdc, fonts["small"])
    y = draw_full_row(hdc, y, "فرستنده با اطلاع از قوانین، مرسوله را تحویل و رسید را دریافت نموده.", h=SMALL_ROW_H)
    y = draw_full_row(hdc, y, "پشتیبانی: 5910-923-0999", h=SMALL_ROW_H, align=win32con.DT_CENTER)
    win32gui.SelectObject(hdc, fonts["main"])
    return y


def draw_header(hdc, y, fonts, copy_label):
    win32gui.SelectObject(hdc, fonts["header"])
    y = draw_full_row(hdc, y, "انبار ارسال کالای مهاجر", align=win32con.DT_CENTER)
    y = draw_full_row(hdc, y, copy_label, align=win32con.DT_CENTER)
    win32gui.SelectObject(hdc, fonts["main"])
    return y


def create_printer_dc():
    hdc = win32gui.CreateDC("WINSPOOL", printer, None)
    win32print.StartDoc(hdc, ("Ticket", None, None, 0))
    win32print.StartPage(hdc)
    fonts = {
        "main": get_font(FONT_SIZE),
        "small": get_font(SMALL_FONT_SIZE),
        "header": get_font(FONT_SIZE, weight=700),
    }
    old_font = win32gui.SelectObject(hdc, fonts["main"])
    return hdc, fonts, old_font


def finish_print(hdc, fonts, old_font):
    win32gui.SelectObject(hdc, old_font)
    for f in fonts.values():
        win32gui.DeleteObject(f)
    win32print.EndPage(hdc)
    win32print.EndDoc(hdc)
    win32gui.DeleteDC(hdc)


def print_ticket(ticket):
    hdc, fonts, old_font = create_printer_dc()
    y = 20

    copy_label = ticket.get('copyLabel', 'نسخه انبار')
    y = draw_header(hdc, y, fonts, copy_label)

    fields = [
        ("زمان ثبت", ticket['created_at']),
        ("کد مرسوله", ticket['id']),
        ("فرستنده", ticket['senderName']),
        ("موبایل فرستنده", ticket['senderPhoneNumber']),
        ("گیرنده", ticket['recieverName']),
        ("موبایل گیرنده", ticket['recieverPhoneNumber']),
        ("شهر مقصد", ticket['maghsadCity']),
        ("راننده", ticket['driverName']),
        ("موبایل راننده", ticket['driverPhoneNumber']),
    ]
    y = draw_fields(hdc, y, fields)
    y = draw_full_row(hdc, y, f"آدرس: {ticket['address']}")

    y = draw_full_row(hdc, y, "مرسولات", align=win32con.DT_CENTER)
    y = print_packages_table(hdc, ticket, y)
    y = print_prices_table(hdc, ticket, y, fonts)

    finish_print(hdc, fonts, old_font)


def get_ticket(ticket_id, headers, copy_label=None):
    try:
        url = f"{BASE_URL}{ticket_id}/"
        r = requests.get(url, headers=headers)
        data = r.json()

        if data.get("print", False):
            ticket = data["tickets"]
            ticket["copyLabel"] = COPY_LABELS.get(copy_label, "نسخه انبار")
            print_ticket(ticket)
        else:
            print(data.get("code"))
            print(data.get("error") or data.get("message") or "something is wrong in api")

    except Exception:
        print("error in recive or print data")
        print(traceback.format_exc())
        time.sleep(5)


COPY_LABELS = {
    "1": "نسخه انبار",
    "2": "نسخه فرستنده",
    "3": "نسخه گیرنده",
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ticket_printer.exe <TicketPrint://print/id/token>")
        print("       ticket_printer.exe <TicketPrint://print/id/token/copy_label>")
        time.sleep(5)
        sys.exit(1)

    raw_arg = sys.argv[1]
    cleaned = raw_arg.replace('"', "").replace("'", "").strip()

    if "://" in cleaned:
        after_protocol = cleaned.split("://", 1)[1] 
        parts = after_protocol.split("/", 2)
        try:
            ticket_id = parts[1]
            rest = parts[2]
            if "/" in rest:
                last_slash = rest.rfind("/")
                token = rest[:last_slash]
                copy_label = rest[last_slash + 1:]
            else:
                token = rest
                copy_label = None
        except Exception:
            print("url format invalid")
            time.sleep(5)
            sys.exit(1)
    else:
        print("protocol not valid")
        time.sleep(5)
        sys.exit(1)

    print("ticket_id:", ticket_id)
    if copy_label:
        print("copy_label:", copy_label)

    headers = {"Authorization": f"Bearer {token}"}
    get_ticket(ticket_id, headers, copy_label)

    print("print successful")
    time.sleep(5)
