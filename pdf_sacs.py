"""
SACS (Simple Automated Cash Flow System) PDF generator.

Page 1: Cashflow bubble diagram — Inflow → Outflow (red X transfer) → Private Reserve
Page 2: Private Reserve detail (balance vs. target) + Schwab investment balance
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
import db

# ── Brand colours ─────────────────────────────────────────────────────────────
BRAND_BLUE   = colors.HexColor("#1B3F6E")
BRAND_LIGHT  = colors.HexColor("#E8EEF7")
GREEN        = colors.HexColor("#2E7D32")
GREEN_LIGHT  = colors.HexColor("#E8F5E9")
RED          = colors.HexColor("#C62828")
RED_LIGHT    = colors.HexColor("#FFEBEE")
BLUE_ACCENT  = colors.HexColor("#1565C0")
BLUE_LIGHT   = colors.HexColor("#E3F2FD")
ARROW_GREEN  = colors.HexColor("#43A047")
ARROW_BLUE   = colors.HexColor("#1E88E5")
GRAY_LIGHT   = colors.HexColor("#F5F5F5")
GRAY_MID     = colors.HexColor("#9E9E9E")
WHITE        = colors.white


def _fmt(n):
    """Format as $X,XXX"""
    return f"${n:,.0f}"


def _fmt_mo(n):
    """Format as $X,XXX/mo"""
    return f"${n:,.0f}/mo"


def _rounded_rect(c, x, y, w, h, r, fill_color, stroke_color=None, stroke_width=1.5):
    c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)
    else:
        c.setStrokeColor(fill_color)
    c.roundRect(x, y, w, h, r, fill=1, stroke=1 if stroke_color else 0)


def _draw_arrow_down(c, x, y_top, length, color, label="", label_color=None):
    """Draw a vertical downward arrow."""
    shaft_w = 4
    head_w = 14
    head_h = 10

    c.setFillColor(color)
    c.setStrokeColor(color)
    c.setLineWidth(0)

    # Shaft
    shaft_top = y_top
    shaft_bot = y_top - length + head_h
    c.rect(x - shaft_w / 2, shaft_bot, shaft_w, shaft_top - shaft_bot, fill=1, stroke=0)

    # Arrowhead (triangle pointing down)
    path = c.beginPath()
    path.moveTo(x, y_top - length)
    path.lineTo(x - head_w / 2, shaft_bot)
    path.lineTo(x + head_w / 2, shaft_bot)
    path.close()
    c.drawPath(path, fill=1, stroke=0)

    if label:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(label_color or color)
        c.drawCentredString(x + 38, y_top - length / 2 - 4, label)


def _draw_arrow_right(c, x_left, y, length, color, label=""):
    """Draw a horizontal rightward arrow with an X (transfer symbol)."""
    shaft_h = 4
    head_w = 10
    head_h = 12

    c.setFillColor(color)
    c.setStrokeColor(color)
    c.setLineWidth(0)

    shaft_right = x_left + length - head_w
    c.rect(x_left, y - shaft_h / 2, shaft_right - x_left, shaft_h, fill=1, stroke=0)

    path = c.beginPath()
    path.moveTo(x_left + length, y)
    path.lineTo(shaft_right, y + head_h / 2)
    path.lineTo(shaft_right, y - head_h / 2)
    path.close()
    c.drawPath(path, fill=1, stroke=0)

    # X symbol in the middle of arrow
    mid_x = x_left + length / 2 - 6
    mid_y = y + 8
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(color)
    c.drawCentredString(mid_x, mid_y, "✕")

    if label:
        c.setFont("Helvetica", 8)
        c.setFillColor(color)
        c.drawCentredString(x_left + length / 2 - 6, y - 18, label)


def _header(c, client, report, page_w, page_h):
    """Blue header band."""
    h = 54
    c.setFillColor(BRAND_BLUE)
    c.rect(0, page_h - h, page_w, h, fill=1, stroke=0)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(0.4 * inch, page_h - 22, "SIMPLE AUTOMATED CASH FLOW SYSTEM")

    c.setFont("Helvetica", 9)
    c.drawString(0.4 * inch, page_h - 38, client["name1"].upper())

    c.setFont("Helvetica", 9)
    c.drawRightString(page_w - 0.4 * inch, page_h - 22, f"Date: {report['report_date']}")
    c.drawRightString(page_w - 0.4 * inch, page_h - 38, report["quarter"])


def _footer(c, page_w, page_num):
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY_MID)
    c.drawCentredString(page_w / 2, 20, f"EF Financial Planning  |  Confidential  |  Page {page_num}")


def _account_bubble(c, x, y, w, h, r, label, amount_line, sublabel, fill_col, stroke_col, text_col=None):
    _rounded_rect(c, x, y, w, h, r, fill_col, stroke_col, 2)
    tc = text_col or stroke_col
    c.setFillColor(tc)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(x + w / 2, y + h - 18, label)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(x + w / 2, y + h / 2 - 2, amount_line)
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY_MID)
    c.drawCentredString(x + w / 2, y + 10, sublabel)


def generate_sacs_pdf(buf, client, report, sacs_data):
    c = rl_canvas.Canvas(buf, pagesize=letter)
    page_w, page_h = letter

    # ── PAGE 1 ────────────────────────────────────────────────────────────────
    _header(c, client, report, page_w, page_h)
    _footer(c, page_w, 1)

    # Layout constants
    bub_w = 170
    bub_h = 90
    bub_r = 14
    center_x = page_w / 2
    top_y = page_h - 120      # top of inflow bubble

    inflow  = sacs_data["inflow"]
    outflow = sacs_data["outflow"]
    excess  = sacs_data["excess"]

    # ── INFLOW bubble (green, top-left area) ─────────────────────────────────
    inf_x = center_x - bub_w - 30
    inf_y = top_y - bub_h
    _rounded_rect(c, inf_x, inf_y, bub_w, bub_h, bub_r, GREEN_LIGHT, GREEN, 2.5)
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(inf_x + bub_w / 2, inf_y + bub_h - 16, "INFLOW ACCOUNT")
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(inf_x + bub_w / 2, inf_y + bub_h / 2 - 2, _fmt_mo(inflow))
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY_MID)
    c.drawCentredString(inf_x + bub_w / 2, inf_y + 10, f"$1,000 floor")

    # ── OUTFLOW bubble (red, top-right area) ─────────────────────────────────
    out_x = center_x + 30
    out_y = inf_y
    _rounded_rect(c, out_x, out_y, bub_w, bub_h, bub_r, RED_LIGHT, RED, 2.5)
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(out_x + bub_w / 2, out_y + bub_h - 16, "OUTFLOW ACCOUNT")
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(out_x + bub_w / 2, out_y + bub_h / 2 - 2, _fmt_mo(outflow))
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY_MID)
    c.drawCentredString(out_x + bub_w / 2, out_y + 10, "$1,000 floor")

    # ── Transfer arrow (red, left→right between bubbles) ─────────────────────
    arr_y = inf_y + bub_h / 2
    arr_x_start = inf_x + bub_w + 4
    arr_length = out_x - arr_x_start - 4
    _draw_arrow_right(c, arr_x_start, arr_y, arr_length, RED)

    # Transfer label above arrow
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(RED)
    c.drawCentredString(center_x, arr_y + 16, f"Monthly Transfer: {_fmt_mo(outflow)}")

    # ── Excess arrow (blue-green, down from inflow bubble) ────────────────────
    exc_x = inf_x + bub_w / 2
    exc_y_top = inf_y - 4
    exc_length = 80
    _draw_arrow_down(c, exc_x, exc_y_top, exc_length, ARROW_BLUE)

    # Excess label to the right of arrow
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(ARROW_BLUE)
    c.drawString(exc_x + 16, exc_y_top - exc_length / 2 - 5, f"Excess:  {_fmt_mo(excess)}")

    # ── PRIVATE RESERVE bubble (blue, bottom-left) ────────────────────────────
    pr_bub_w = bub_w + 20
    pr_bub_h = bub_h + 10
    pr_x = inf_x - 10
    pr_y = exc_y_top - exc_length - pr_bub_h - 4
    _rounded_rect(c, pr_x, pr_y, pr_bub_w, pr_bub_h, bub_r, BLUE_LIGHT, BLUE_ACCENT, 2.5)
    c.setFillColor(BLUE_ACCENT)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(pr_x + pr_bub_w / 2, pr_y + pr_bub_h - 18, "PRIVATE RESERVE")
    c.setFont("Helvetica", 8)
    c.drawCentredString(pr_x + pr_bub_w / 2, pr_y + pr_bub_h - 30, "(High-Yield Savings)")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY_MID)
    c.drawCentredString(pr_x + pr_bub_w / 2, pr_y + 10, "$1,000 floor")

    # ── Salary / Paycheck source label ────────────────────────────────────────
    src_y = top_y + 14
    c.setFont("Helvetica", 9)
    c.setFillColor(BRAND_BLUE)
    c.drawCentredString(inf_x + bub_w / 2, src_y, "PAYCHECK / SALARY")
    _draw_arrow_down(c, inf_x + bub_w / 2, src_y - 2, top_y - inf_y - bub_h - src_y + inf_y + bub_h + 2 + 2, ARROW_GREEN)

    # ── Info box (right side) ─────────────────────────────────────────────────
    info_x = out_x
    info_y = pr_y
    info_w = bub_w
    info_h = pr_bub_h

    _rounded_rect(c, info_x, info_y, info_w, info_h, bub_r, GRAY_LIGHT, colors.HexColor("#BDBDBD"), 1)
    c.setFillColor(BRAND_BLUE)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(info_x + info_w / 2, info_y + info_h - 18, "MONTHLY SUMMARY")

    rows = [
        ("Monthly Inflow", _fmt_mo(inflow)),
        ("Monthly Outflow", _fmt_mo(outflow)),
        ("Monthly Excess", _fmt_mo(excess)),
    ]
    row_y = info_y + info_h - 36
    for label, val in rows:
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.black)
        c.drawString(info_x + 12, row_y, label)
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(info_x + info_w - 12, row_y, val)
        row_y -= 16

    # Divider
    c.setStrokeColor(colors.HexColor("#BDBDBD"))
    c.setLineWidth(0.5)
    c.line(info_x + 10, row_y + 8, info_x + info_w - 10, row_y + 8)

    c.setFont("Helvetica", 7.5)
    c.setFillColor(GRAY_MID)
    c.drawString(info_x + 12, row_y - 6, "Excess flows to Private Reserve")

    # ── Section title ─────────────────────────────────────────────────────────
    title_y = top_y + 44
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(BRAND_BLUE)
    c.drawCentredString(center_x, title_y, "Cash Flow Architecture")
    c.setStrokeColor(BRAND_BLUE)
    c.setLineWidth(1)
    c.line(0.5 * inch, title_y - 6, page_w - 0.5 * inch, title_y - 6)

    c.showPage()

    # ── PAGE 2 ────────────────────────────────────────────────────────────────
    _header(c, client, report, page_w, page_h)
    _footer(c, page_w, 2)

    p2_title_y = page_h - 80
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(BRAND_BLUE)
    c.drawCentredString(center_x, p2_title_y, "Account Balances & Savings Target")
    c.setStrokeColor(BRAND_BLUE)
    c.setLineWidth(1)
    c.line(0.5 * inch, p2_title_y - 6, page_w - 0.5 * inch, p2_title_y - 6)

    card_w = (page_w - 3 * 0.5 * inch) / 2
    card_h = 160
    card_r = 12
    card_y = p2_title_y - card_h - 30

    # Private Reserve card
    pr_card_x = 0.5 * inch
    _rounded_rect(c, pr_card_x, card_y, card_w, card_h, card_r, BLUE_LIGHT, BLUE_ACCENT, 2)

    c.setFillColor(BLUE_ACCENT)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(pr_card_x + card_w / 2, card_y + card_h - 20, "PRIVATE RESERVE")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY_MID)
    c.drawCentredString(pr_card_x + card_w / 2, card_y + card_h - 33, "High-Yield Savings Account")

    c.setFont("Helvetica", 8)
    c.setFillColor(BRAND_BLUE)
    c.drawString(pr_card_x + 16, card_y + card_h - 55, "Current Balance")
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(pr_card_x + card_w / 2, card_y + card_h - 78, _fmt(sacs_data["pr_balance"]))

    c.setStrokeColor(colors.HexColor("#90CAF9"))
    c.setLineWidth(0.5)
    c.line(pr_card_x + 16, card_y + card_h - 88, pr_card_x + card_w - 16, card_y + card_h - 88)

    c.setFont("Helvetica", 8)
    c.setFillColor(BRAND_BLUE)
    c.drawString(pr_card_x + 16, card_y + card_h - 104, "Target Balance")
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(GREEN)
    c.drawCentredString(pr_card_x + card_w / 2, card_y + card_h - 124, _fmt(sacs_data["pr_target"]))

    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY_MID)
    c.drawCentredString(pr_card_x + card_w / 2, card_y + 14, "6 months expenses + insurance deductibles")

    # Schwab / Investment card
    sw_card_x = pr_card_x + card_w + 0.5 * inch
    _rounded_rect(c, sw_card_x, card_y, card_w, card_h, card_r, GREEN_LIGHT, GREEN, 2)

    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(sw_card_x + card_w / 2, card_y + card_h - 20, "INVESTMENT ACCOUNT")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY_MID)
    c.drawCentredString(sw_card_x + card_w / 2, card_y + card_h - 33, "Charles Schwab")

    c.setFont("Helvetica", 8)
    c.setFillColor(GREEN)
    c.drawString(sw_card_x + 16, card_y + card_h - 55, "Current Balance")
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.black)
    c.drawCentredString(sw_card_x + card_w / 2, card_y + card_h - 82, _fmt(sacs_data["schwab_balance"]))

    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY_MID)
    c.drawCentredString(sw_card_x + card_w / 2, card_y + 14, "As of " + report["report_date"])

    # ── How We Got Here note ──────────────────────────────────────────────────
    note_y = card_y - 30
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(BRAND_BLUE)
    c.drawString(0.5 * inch, note_y, "Private Reserve Target Calculation")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.black)
    ded_total = sacs_data.get("pr_target", 0) - sacs_data["outflow"] * 6
    c.drawString(0.5 * inch, note_y - 14,
                 f"6 months of expenses ({_fmt(sacs_data['outflow'])} × 6 = {_fmt(sacs_data['outflow'] * 6)})"
                 f"  +  Insurance deductibles ({_fmt(ded_total)})  =  {_fmt(sacs_data['pr_target'])}")

    c.save()
