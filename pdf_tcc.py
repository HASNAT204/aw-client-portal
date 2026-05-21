"""
TCC (Total Client Chart) PDF generator.

Layout (landscape Letter):
  - Top: Green client info ovals for Client 1 and Client 2
  - Left column: Client 1 retirement account bubbles + gray total
  - Right column: Client 2 retirement account bubbles + gray total
  - Center: Trust bubble (Zillow value)
  - Bottom: Non-retirement joint accounts + gray total
  - Bottom-right: Liabilities + gray total
  - Top-center: Grand Total net worth box
"""

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas
import db

# ── Brand colours ─────────────────────────────────────────────────────────────
BRAND_BLUE  = colors.HexColor("#1B3F6E")
GREEN       = colors.HexColor("#2E7D32")
GREEN_LIGHT = colors.HexColor("#E8F5E9")
GREEN_MID   = colors.HexColor("#43A047")
BLUE_ACCENT = colors.HexColor("#1565C0")
BLUE_LIGHT  = colors.HexColor("#E3F2FD")
GRAY_BOX    = colors.HexColor("#EEEEEE")
GRAY_STROKE = colors.HexColor("#9E9E9E")
GRAY_MID    = colors.HexColor("#757575")
GRAY_DARK   = colors.HexColor("#424242")
RED         = colors.HexColor("#C62828")
RED_LIGHT   = colors.HexColor("#FFEBEE")
GOLD        = colors.HexColor("#F57F17")
GOLD_LIGHT  = colors.HexColor("#FFF8E1")
WHITE       = colors.white
BLACK       = colors.black


def _fmt(n):
    if n is None:
        return "—"
    return f"${n:,.0f}"


def _rounded_rect(c, x, y, w, h, r, fill_color, stroke_color=None, lw=1.5):
    c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(lw)
    else:
        c.setStrokeColor(fill_color)
        c.setLineWidth(0)
    c.roundRect(x, y, w, h, r, fill=1, stroke=1)


def _header(c, client, report, page_w, page_h):
    h = 50
    c.setFillColor(BRAND_BLUE)
    c.rect(0, page_h - h, page_w, h, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(0.35 * inch, page_h - 22, "TOTAL CLIENT CHART")
    c.setFont("Helvetica", 9)
    c.drawString(0.35 * inch, page_h - 37, client["name1"].upper() + (" & " + client["name2"].upper() if client["name2"] else ""))
    c.setFont("Helvetica", 9)
    c.drawRightString(page_w - 0.35 * inch, page_h - 22, f"Date: {report['report_date']}")
    c.drawRightString(page_w - 0.35 * inch, page_h - 37, report["quarter"])


def _footer(c, page_w):
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY_MID)
    c.drawCentredString(page_w / 2, 14, "EF Financial Planning  |  Confidential  |  Total Client Chart")


def _client_info_bubble(c, x, y, w, h, name, dob, age, ssn_last4, label):
    """Green oval with client identity info."""
    r = min(w, h) * 0.18
    _rounded_rect(c, x, y, w, h, r, GREEN_LIGHT, GREEN, 2)
    cy = y + h
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x + w / 2, cy - 14, label)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(BRAND_BLUE)
    c.drawCentredString(x + w / 2, cy - 28, name or "—")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(GRAY_DARK)
    line2 = f"DOB: {dob or '—'}   Age: {age if age is not None else '—'}"
    c.drawCentredString(x + w / 2, cy - 42, line2)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(x + w / 2, cy - 54, f"SSN: ***-**-{ssn_last4 or '????'}")


def _account_bubble(c, x, y, w, h, acc_type, last4, balance, cash_bal=None,
                    fill_col=BLUE_LIGHT, stroke_col=BLUE_ACCENT):
    r = 10
    _rounded_rect(c, x, y, w, h, r, fill_col, stroke_col, 1.5)
    cy = y + h
    c.setFillColor(stroke_col)
    c.setFont("Helvetica-Bold", 8)
    disp_type = acc_type if len(acc_type) <= 18 else acc_type[:16] + "…"
    c.drawCentredString(x + w / 2, cy - 14, disp_type)
    if last4:
        c.setFont("Helvetica", 7)
        c.setFillColor(GRAY_MID)
        c.drawCentredString(x + w / 2, cy - 24, f"···· {last4}")
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(BLACK)
    bal_y = cy - 38 if last4 else cy - 28
    c.drawCentredString(x + w / 2, bal_y, _fmt(balance))
    if cash_bal is not None and cash_bal > 0:
        c.setFont("Helvetica", 7)
        c.setFillColor(GRAY_MID)
        c.drawCentredString(x + w / 2, y + 10, f"Cash: {_fmt(cash_bal)}")


def _total_box(c, x, y, w, h, label, amount, fill=GRAY_BOX, stroke=GRAY_STROKE):
    _rounded_rect(c, x, y, w, h, 8, fill, stroke, 1.5)
    c.setFillColor(GRAY_DARK)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x + w / 2, y + h - 14, label)
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(BRAND_BLUE)
    c.drawCentredString(x + w / 2, y + 10, _fmt(amount))


def _section_label(c, x, y, text, col=BRAND_BLUE):
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(col)
    c.drawString(x, y, text)


def generate_tcc_pdf(buf, client, report, accounts, balances, tcc_data):
    c = rl_canvas.Canvas(buf, pagesize=landscape(letter))
    page_w, page_h = landscape(letter)

    _header(c, client, report, page_w, page_h)
    _footer(c, page_w)

    # Build lookup: account_id → balance dict
    bal_map = {b["account_id"]: dict(b) for b in balances}

    # Convert accounts to dicts for .get() support
    accounts = [dict(a) for a in accounts]

    # Split accounts by type
    c1_ret = [a for a in accounts if a["owner"] == "client1" and a["category"] == "retirement"]
    c2_ret = [a for a in accounts if a["owner"] == "client2" and a["category"] == "retirement"]
    non_ret = [a for a in accounts if a["category"] == "non_retirement"]
    trusts = [a for a in accounts if a["category"] == "trust"]
    liabs = [a for a in accounts if a["category"] == "liability"]

    # ── Layout geometry ───────────────────────────────────────────────────────
    margin = 0.35 * inch
    content_top = page_h - 68       # below header
    content_bot = 28                # above footer
    usable_h = content_top - content_bot
    usable_w = page_w - 2 * margin

    # Column widths (5 columns: C1, gap, center, gap, C2, gap, non-ret+liab)
    col_w = 148
    center_w = 130
    gap = 14
    # C1 col: margin .. margin+col_w
    # center: after C1+gap
    # C2: after center+gap
    # non-ret+liab: right side
    c1_x = margin
    cen_x = c1_x + col_w + gap
    c2_x = cen_x + center_w + gap
    right_x = c2_x + col_w + gap
    right_w = page_w - margin - right_x   # non-ret + liabilities

    # ── CLIENT INFO BUBBLES ───────────────────────────────────────────────────
    cib_h = 70
    cib_w = col_w
    cib_y = content_top - cib_h - 4

    age1 = db.calc_age(client["dob1"])
    _client_info_bubble(c, c1_x, cib_y, cib_w, cib_h,
                        client["name1"], client["dob1"], age1, client["ssn_last4_1"],
                        "CLIENT 1")

    if client["name2"]:
        age2 = db.calc_age(client["dob2"])
        _client_info_bubble(c, c2_x, cib_y, cib_w, cib_h,
                            client["name2"], client["dob2"], age2, client["ssn_last4_2"],
                            "CLIENT 2")

    # ── GRAND TOTAL BOX (center top) ─────────────────────────────────────────
    gt_w = center_w
    gt_h = 52
    gt_x = cen_x
    gt_y = cib_y + (cib_h - gt_h) / 2
    _rounded_rect(c, gt_x, gt_y, gt_w, gt_h, 10, BRAND_BLUE, BRAND_BLUE, 0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(gt_x + gt_w / 2, gt_y + gt_h - 14, "GRAND TOTAL NET WORTH")
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(gt_x + gt_w / 2, gt_y + 12, _fmt(tcc_data["grand_total"]))

    # ── RETIREMENT COLUMNS ────────────────────────────────────────────────────
    bub_w = col_w
    bub_h = 62
    bub_gap = 8
    total_box_h = 38

    # Retirement section starts below client bubbles
    ret_section_top = cib_y - 14

    _section_label(c, c1_x, ret_section_top + 2, "RETIREMENT — CLIENT 1", GREEN)
    _section_label(c, c2_x, ret_section_top + 2, "RETIREMENT — CLIENT 2", GREEN)

    def _draw_ret_column(accounts_list, col_x, start_y):
        y = start_y - bub_h
        for acc in accounts_list:
            bid = acc["id"]
            bal = bal_map.get(bid, {})
            b_val = bal.get("balance", 0) or 0
            cb_val = bal.get("cash_balance", 0) or 0
            _account_bubble(c, col_x, y, bub_w, bub_h, acc["account_type"], acc.get("account_last4"),
                            b_val, cb_val if cb_val else None,
                            fill_col=GREEN_LIGHT, stroke_col=GREEN)
            y -= (bub_h + bub_gap)
        # Total box
        c1r_total = tcc_data["client1_retirement_total"] if col_x == c1_x else tcc_data["client2_retirement_total"]
        tot_label = "CLIENT 1 RETIREMENT TOTAL" if col_x == c1_x else "CLIENT 2 RETIREMENT TOTAL"
        _total_box(c, col_x, y - total_box_h + bub_h, bub_w, total_box_h,
                   tot_label, c1r_total)
        return y - bub_gap

    c1_ret_bot = _draw_ret_column(c1_ret, c1_x, ret_section_top - 14)
    if client["name2"]:
        c2_ret_bot = _draw_ret_column(c2_ret, c2_x, ret_section_top - 14)
    else:
        # No spouse — show placeholder
        c.setFont("Helvetica", 8)
        c.setFillColor(GRAY_MID)
        c.drawCentredString(c2_x + col_w / 2, ret_section_top - 40, "N/A — Single Client")

    # ── TRUST (center column) ─────────────────────────────────────────────────
    trust_top = ret_section_top - 14
    trust_section_h = content_top - cib_y - cib_h - 14 - 6

    if trusts:
        acc = trusts[0]
        trust_bub_h = 80
        trust_bub_y = trust_top - trust_bub_h

        _rounded_rect(c, cen_x, trust_bub_y, center_w, trust_bub_h, 12,
                      GOLD_LIGHT, GOLD, 2)
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(cen_x + center_w / 2, trust_bub_y + trust_bub_h - 14, "TRUST")
        c.setFont("Helvetica", 7)
        c.setFillColor(GRAY_MID)
        addr = acc.get("property_address") or "—"
        # Wrap address if too long
        if len(addr) > 22:
            addr = addr[:20] + "…"
        c.drawCentredString(cen_x + center_w / 2, trust_bub_y + trust_bub_h - 26, addr)
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(BLACK)
        c.drawCentredString(cen_x + center_w / 2, trust_bub_y + trust_bub_h - 48, _fmt(report["zillow_value"]))
        c.setFont("Helvetica", 7)
        c.setFillColor(GRAY_MID)
        c.drawCentredString(cen_x + center_w / 2, trust_bub_y + 10, "Zillow Zestimate")
    else:
        c.setFont("Helvetica", 8)
        c.setFillColor(GRAY_MID)
        c.drawCentredString(cen_x + center_w / 2, trust_top - 40, "No Trust")

    # ── NON-RETIREMENT (right column — upper half) ────────────────────────────
    nr_bub_w = right_w
    nr_bub_h = 62

    _section_label(c, right_x, ret_section_top + 2, "NON-RETIREMENT (JOINT)", BLUE_ACCENT)
    nr_y = ret_section_top - 14 - nr_bub_h

    for acc in non_ret:
        bid = acc["id"]
        bal = bal_map.get(bid, {})
        b_val = bal.get("balance", 0) or 0
        cb_val = bal.get("cash_balance", 0) or 0
        _account_bubble(c, right_x, nr_y, nr_bub_w, nr_bub_h,
                        acc["account_type"], acc.get("account_last4"),
                        b_val, cb_val if cb_val else None)
        nr_y -= (nr_bub_h + bub_gap)

    # Non-ret total box
    _total_box(c, right_x, nr_y - total_box_h + nr_bub_h, nr_bub_w, total_box_h,
               "NON-RETIREMENT TOTAL", tcc_data["non_retirement_total"])
    nr_bot = nr_y - bub_gap

    # ── LIABILITIES (right column — lower half) ───────────────────────────────
    liab_top = nr_bot - 20
    _section_label(c, right_x, liab_top + 2, "LIABILITIES", RED)

    liab_bub_h = 58
    lb_y = liab_top - 14 - liab_bub_h

    for acc in liabs:
        bid = acc["id"]
        bal = bal_map.get(bid, {})
        b_val = bal.get("balance", 0) or 0
        rate = acc.get("interest_rate")
        rate_str = f"{rate:.2f}% APR" if rate else ""

        _rounded_rect(c, right_x, lb_y, nr_bub_w, liab_bub_h, 10, RED_LIGHT, RED, 1.5)
        c.setFillColor(RED)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(right_x + nr_bub_w / 2, lb_y + liab_bub_h - 14, acc["account_type"])
        if acc.get("account_last4"):
            c.setFont("Helvetica", 7)
            c.setFillColor(GRAY_MID)
            c.drawCentredString(right_x + nr_bub_w / 2, lb_y + liab_bub_h - 24, f"···· {acc['account_last4']}")
        if rate_str:
            c.setFont("Helvetica", 7.5)
            c.setFillColor(RED)
            c.drawCentredString(right_x + nr_bub_w / 2, lb_y + liab_bub_h - 36, rate_str)
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(BLACK)
        c.drawCentredString(right_x + nr_bub_w / 2, lb_y + 10, _fmt(b_val))
        lb_y -= (liab_bub_h + bub_gap)

    # Liabilities total box
    _total_box(c, right_x, lb_y - total_box_h + liab_bub_h, nr_bub_w, total_box_h,
               "LIABILITIES TOTAL", tcc_data["liabilities_total"],
               fill=RED_LIGHT, stroke=RED)

    # ── DISCLAIMER NOTE ───────────────────────────────────────────────────────
    c.setFont("Helvetica", 6.5)
    c.setFillColor(GRAY_MID)
    c.drawString(margin, 20,
                 "* Liabilities shown separately and are NOT subtracted from Net Worth total.  "
                 "Non-Retirement total excludes Trust value.  Grand Total = C1 Retirement + C2 Retirement + Non-Retirement + Trust.")

    c.save()
