"""Minimal pure-Python PDF writer (core fonts only) used for invoices and payslips."""

import io
from datetime import date
from decimal import Decimal

PAGE_W = 595.0
PAGE_H = 842.0
MARGIN = 48.0

STUDIO_NAME = "Offsitearch"
STUDIO_TAGLINE = "Architecture & Interiors"
STUDIO_MONOGRAM = "OA"
STUDIO_ADDRESS_LINES = (
    "42 Studio Lane, Block C",
    "Bengaluru, Karnataka 560001",
)
DEFAULT_GSTIN = "29AAAAA0000A1Z5"


def _escape_text(value: str) -> str:
    out: list[str] = []
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == "(":
            out.append("\\(")
        elif ch == ")":
            out.append("\\)")
        elif ord(ch) <= 255:
            out.append(ch)
        else:
            out.append("?")
    return "".join(out)


def _wrap(value: str, width: float, size: float) -> list[str]:
    char_w = size * 0.55
    max_chars = max(1, int(width // char_w))
    if len(value) <= max_chars:
        return [value]
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class PdfBuilder:
    """Builds a simple single/multi-page PDF using top-left (x, y) coordinates."""

    def __init__(self) -> None:
        self.pages: list[list[str]] = [[]]
        self.y = MARGIN
        self._fill_color = "0 0 0"
        self._stroke_color = "0 0 0"

    def _new_page(self) -> None:
        self.pages.append([])
        self.y = MARGIN

    def _ensure_room(self, needed: float = 36.0) -> None:
        if self.y + needed > PAGE_H - MARGIN:
            self._new_page()

    def set_fill_color(self, r: int, g: int, b: int) -> None:
        """Set fill color (0-255 range)."""
        self._fill_color = f"{r / 255:.3f} {g / 255:.3f} {b / 255:.3f}"

    def set_stroke_color(self, r: int, g: int, b: int) -> None:
        """Set stroke color."""
        self._stroke_color = f"{r / 255:.3f} {g / 255:.3f} {b / 255:.3f}"

    def draw_rect(
        self, x: float, y: float, w: float, h: float, fill: bool = True, stroke: bool = False
    ) -> None:
        """Draw a rectangle. Coordinates are top-left origin."""
        op = ""
        if fill:
            self.pages[-1].append(f"{self._fill_color} rg")
            op += "f"
        if stroke:
            self.pages[-1].append(f"{self._stroke_color} RG")
            op += "S" if not fill else "B"
        y_pdf = PAGE_H - y - h
        self.pages[-1].append(f"{x:.2f} {y_pdf:.2f} {w:.2f} {h:.2f} re {op}")

    def draw_line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Draw a line using the current stroke color."""
        self.pages[-1].append(f"{self._stroke_color} RG")
        self.pages[-1].append(f"{x1:.2f} {PAGE_H - y1:.2f} m {x2:.2f} {PAGE_H - y2:.2f} l S")

    def fixed(
        self, x: float, y_top: float, value: str, size: float = 10, bold: bool = False
    ) -> None:
        font = "F2" if bold else "F1"
        y_pdf = PAGE_H - y_top
        self.pages[-1].append(
            f"BT /{font} {size:.1f} Tf {x:.1f} {y_pdf:.1f} Td ({_escape_text(value)}) Tj ET"
        )

    def fixed_color(
        self,
        x: float,
        y_top: float,
        value: str,
        size: float = 10,
        bold: bool = False,
        color: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """Draw text with a specific color."""
        font = "F2" if bold else "F1"
        y_pdf = PAGE_H - y_top
        self.pages[-1].append(f"{_rgb(color)} rg")
        self.pages[-1].append(
            f"BT /{font} {size:.1f} Tf {x:.1f} {y_pdf:.1f} Td ({_escape_text(value)}) Tj ET"
        )

    def text(
        self, x: float, value: str, size: float = 10, bold: bool = False, width: float | None = None
    ) -> None:
        font = "F2" if bold else "F1"
        lines = _wrap(value, width, size) if width else [value]
        for line in lines:
            self._ensure_room(size * 1.45)
            y_pdf = PAGE_H - self.y
            self.pages[-1].append(
                f"BT /{font} {size:.1f} Tf {x:.1f} {y_pdf:.1f} Td ({_escape_text(line)}) Tj ET"
            )
            self.y += size * 1.45

    def text_color(
        self,
        x: float,
        value: str,
        size: float = 10,
        bold: bool = False,
        width: float | None = None,
        color: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """Draw (possibly wrapped) text with a specific color. Advances pdf.y like text()."""
        font = "F2" if bold else "F1"
        lines = _wrap(value, width, size) if width else [value]
        for line in lines:
            self._ensure_room(size * 1.45)
            y_pdf = PAGE_H - self.y
            self.pages[-1].append(f"{_rgb(color)} rg")
            self.pages[-1].append(
                f"BT /{font} {size:.1f} Tf {x:.1f} {y_pdf:.1f} Td ({_escape_text(line)}) Tj ET"
            )
            self.y += size * 1.45

    def line(self, x1: float, y1: float, x2: float, y2: float, width: float = 0.7) -> None:
        self.pages[-1].append(
            f"{width:.2f} w {x1:.1f} {PAGE_H - y1:.1f} m {x2:.1f} {PAGE_H - y2:.1f} l S"
        )

    def hline(self, y: float, x1: float | None = None, x2: float | None = None) -> None:
        self.line(x1 or MARGIN, y, x2 or (PAGE_W - MARGIN), y)

    def money(self, value: Decimal | float) -> str:
        return f"{Decimal(value):,.2f}"

    def _render_page_numbers(self) -> None:
        """Add 'Page X of Y' to every page footer."""
        total = len(self.pages)
        for i in range(total):
            self.pages[i].append(f"{self._fill_color} rg")
            y_pdf = PAGE_H - (PAGE_H - 24)
            self.pages[i].append(
                f"BT /F1 8.0 Tf {PAGE_W / 2:.1f} {y_pdf:.1f} Td "
                f"({_escape_text(f'Page {i + 1} of {total}')}) Tj ET"
            )

    def render(self) -> bytes:
        self._render_page_numbers()
        n_pages = len(self.pages)
        kids = " ".join(f"{6 + 2 * i} 0 R" for i in range(n_pages))
        objects: list[bytes] = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objects.append(
            b"<< /Type /Pages /Kids ["
            + kids.encode()
            + b"] /Count "
            + str(n_pages).encode()
            + b" >>"
        )
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        for i, page in enumerate(self.pages):
            content = "\n".join(page).encode("latin-1")
            content_obj = (
                b"<< /Length "
                + str(len(content)).encode()
                + b" >>\nstream\n"
                + content
                + b"\nendstream"
            )
            objects.append(content_obj)
            page_obj = (
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                b"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
                b"/Contents " + str(5 + 2 * i).encode() + b" 0 R >>"
            )
            objects.append(page_obj)

        buf = io.BytesIO()
        buf.write(b"%PDF-1.4\n")
        offsets: list[int] = []
        for idx, obj in enumerate(objects, start=1):
            offsets.append(buf.tell())
            buf.write(f"{idx} 0 obj\n".encode())
            buf.write(obj)
            buf.write(b"\nendobj\n")
        xref_pos = buf.tell()
        buf.write(f"xref\n0 {len(objects) + 1}\n".encode())
        buf.write(b"0000000000 65535 f \n")
        for off in offsets:
            buf.write(f"{off:010d} 00000 n \n".encode())
        buf.write(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
        )
        return buf.getvalue()


# -- Color palette (matches frontend design system) -----------------------------------
# The document stays black-and-white; color appears only on the status badge
# so a stack of invoices can be scanned at a glance (Phase-3 spec).
_GRAY_LINE = (0xC8, 0xC8, 0xC8)
_DARK_TEXT = (0x1A, 0x1A, 0x1A)
_MUTED_TEXT = (0x66, 0x66, 0x66)
_WHITE = (0xFF, 0xFF, 0xFF)
_GREEN = (0x15, 0x80, 0x3D)
_RED = (0xB9, 0x1C, 0x1C)
_AMBER = (0xB4, 0x53, 0x09)

# mode, ink color — filled boxes use white text
_STATUS_STYLES = {
    "draft": ("outline", _MUTED_TEXT),
    "sent": ("outline", _DARK_TEXT),
    "partial": ("outline", _AMBER),
    "paid": ("filled", _GREEN),
    "overdue": ("outline", _RED),
    "cancelled": ("outline", _RED),
}

# -- Font metrics -----------------------------------------------------------------------
# Conservative Helvetica fractions (of font size), used to keep rules/borders
# clear of glyphs. Text draw calls position at the BASELINE; anything drawn
# near text must offset by these amounts or it will strike through letters.
_ASC = 0.76  # ascender/cap height above baseline
_DESC = 0.24  # descender depth below baseline


def _box_baseline(box_top: float, box_h: float, size: float) -> float:
    """Top-origin baseline that vertically centers `size`-point text in a box."""
    text_h = size * (_ASC + _DESC)
    return box_top + (box_h - text_h) / 2 + size * _ASC


def _rule_above(baseline: float, size: float, pad: float = 3.0) -> float:
    """Y for a horizontal rule that clears the tops of glyphs."""
    return baseline - size * _ASC - pad


def _rule_below(baseline: float, size: float, pad: float = 3.5) -> float:
    """Y for a horizontal rule that clears descenders."""
    return baseline + size * _DESC + pad


def _rgb(color: tuple[int, int, int]) -> str:
    return f"{color[0] / 255:.3f} {color[1] / 255:.3f} {color[2] / 255:.3f}"


def format_inr(value: Decimal | float | int) -> str:
    """Format a decimal amount with Indian digit grouping (lakhs/crores), e.g. 12,34,567.89."""
    d = Decimal(value).quantize(Decimal("0.01"))
    sign = "-" if d < 0 else ""
    whole = abs(int(d))
    frac = f"{int(abs(d) % 1 * 100):02d}"
    s = str(whole)
    if len(s) > 3:
        head, last3 = s[:-3], s[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join([*groups, last3])
    return f"{sign}{s}.{frac}"


def _right_x(text: str, size: float, right_edge: float) -> float:
    """Approximate x coordinate to right-align text ending at right_edge."""
    return right_edge - len(text) * size * 0.53


def _stamp_page_footers(pdf: PdfBuilder, studio_name: str, gstin: str | None) -> None:
    """Stamp the company footer (rule + thank-you + GSTIN + generated-by) on every page."""
    footer_rule_y = PAGE_H - 38
    text_y = PAGE_H - 30
    sub_y = PAGE_H - 21
    thanks = f"Thank you for partnering with {studio_name}."
    generated = "This is a computer-generated invoice."
    for page in pdf.pages:
        page.append(f"{_rgb(_DARK_TEXT)} RG")
        page.append(
            f"0.7 w {MARGIN:.1f} {PAGE_H - footer_rule_y:.1f} m "
            f"{PAGE_W - MARGIN:.1f} {PAGE_H - footer_rule_y:.1f} l S"
        )
        page.append(f"{_rgb(_MUTED_TEXT)} rg")
        page.append(
            f"BT /F1 8.0 Tf {MARGIN:.1f} {PAGE_H - text_y:.1f} Td ({_escape_text(thanks)}) Tj ET"
        )
        page.append(
            f"BT /F1 7.0 Tf {MARGIN:.1f} {PAGE_H - sub_y:.1f} Td ({_escape_text(generated)}) Tj ET"
        )
        gst_text = f"GSTIN: {gstin}" if gstin else ""
        if gst_text:
            gx = _right_x(gst_text, 7.0, PAGE_W - MARGIN)
            page.append(
                f"BT /F1 7.0 Tf {gx:.1f} {PAGE_H - sub_y:.1f} Td ({_escape_text(gst_text)}) Tj ET"
            )


# -- Brand mark: "Skyline Bars" (vector reproduction of frontend OffsiteMark) --------
# Five prefab modules side by side; geometry from the 40x40 viewBox in BrandLogo.tsx.
_BRAND_BARS = [
    (2, 24, 6, 14),
    (9.5, 16, 6, 22),
    (17, 20, 6, 18),
    (24.5, 8, 6, 30),
    (32, 26, 6, 12),
]


def _draw_brand_mark(pdf: PdfBuilder, x: float, y_top: float, size: float) -> None:
    """Draw the Offsite skyline mark as flat dark bars (no background)."""
    scale = size / 40
    pdf.set_fill_color(*_DARK_TEXT)
    for bx, by, bw, bh in _BRAND_BARS:
        # draw_rect is top-left origin, same as the SVG viewBox — pass through.
        pdf.draw_rect(x + bx * scale, y_top + by * scale, bw * scale, bh * scale, fill=True)


def _draw_status_badge(pdf: PdfBuilder, right_edge: float, y_top: float, status: str) -> None:
    """Status pill, styled per status (outline for most, filled green for PAID)."""
    mode, color = _STATUS_STYLES.get(status.lower(), ("outline", _DARK_TEXT))
    w, h = 84, 18
    x = right_edge - w
    if mode == "filled":
        pdf.set_fill_color(*color)
        pdf.draw_rect(x, y_top, w, h, fill=True)
        ink = _WHITE
    else:
        pdf.set_stroke_color(*color)
        pdf.draw_rect(x, y_top, w, h, fill=False, stroke=True)
        ink = color
    label = status.upper()
    tx = x + (w - len(label) * 8 * 0.60) / 2
    pdf.fixed_color(tx, _box_baseline(y_top, h, 8), label, 8, bold=True, color=ink)


def _format_qty(value) -> str:
    """1.00 -> '1', 2.50 -> '2.5' — no trailing zeros on quantities."""
    d = Decimal(str(value)).normalize()
    return f"{d:f}"


def invoice_pdf(
    invoice_number: str,
    client_name: str,
    invoice_date: date,
    due_date: date,
    status: str,
    items: list[dict],
    subtotal: Decimal,
    tax_percent: Decimal,
    tax_amount: Decimal,
    total: Decimal,
    paid_amount: Decimal,
    notes: str | None = None,
    terms: str | None = None,
    studio_info: dict | None = None,
    project_code: str | None = None,
    project_name: str | None = None,
    client_address: str | None = None,
    client_gstin: str | None = None,
    tax_lines: list[tuple[str, Decimal]] | None = None,
    payment_details: dict | None = None,
) -> bytes:
    """Client-facing GST invoice.

    Currency note: PDF core fonts cannot render the rupee glyph, so amounts
    follow the "INR" convention used across the app's documents; values are
    always Indian-grouped and rounded to 2 decimals (format_inr).

    tax_lines: precomputed [(label, amount)] from the service — CGST+SGST for
    intra-state supply, a single IGST line otherwise (see _tax_breakup).
    payment_details: optional {bank_name, account_name, account_number,
    ifsc_code, upi_id} sourced from Company Settings.
    """
    # Resolve studio info ---------------------------------------------------------
    info = studio_info or {}
    studio_name = info.get("name", STUDIO_NAME)
    tagline = info.get("tagline", STUDIO_TAGLINE)
    gstin = info.get("gstin", DEFAULT_GSTIN)

    raw_address = info.get("address")
    if isinstance(raw_address, str):
        address_lines = [raw_address] if raw_address.strip() else []
    elif isinstance(raw_address, (list, tuple)):
        address_lines = [str(a) for a in raw_address if str(a).strip()]
    else:
        address_lines = list(STUDIO_ADDRESS_LINES)
    contact_bits = [
        bit
        for bit in (
            info.get("phone"),
            info.get("email"),
            info.get("website"),
        )
        if bit
    ]

    pdf = PdfBuilder()

    # -- Company header (monochrome, line-based) ------------------------------------
    # Left upper: skyline brand mark (no background) + wordmark + contact block.
    # Right: document title, invoice number, dates.
    content_top = MARGIN

    mark_size = 30
    _draw_brand_mark(pdf, MARGIN, content_top, mark_size)

    wordmark_x = MARGIN + mark_size + 10
    pdf.fixed_color(
        wordmark_x, content_top + 11, studio_name.upper(), 15, bold=True, color=_DARK_TEXT
    )
    left_y = content_top + 26
    if tagline:
        pdf.fixed_color(wordmark_x, left_y, tagline, 8, color=_MUTED_TEXT)
        left_y += 12
    for line in address_lines[:2]:
        pdf.fixed_color(MARGIN, left_y, line, 8, color=_MUTED_TEXT)
        left_y += 10.5
    if contact_bits:
        pdf.fixed_color(MARGIN, left_y, "  ·  ".join(contact_bits), 8, color=_MUTED_TEXT)
        left_y += 10.5
    if gstin:
        pdf.fixed_color(MARGIN, left_y, f"GSTIN: {gstin}", 8, color=_MUTED_TEXT)
        left_y += 10.5

    right_x = PAGE_W - MARGIN
    inv_title_w = len("INVOICE") * 20 * 0.62
    title_x = right_x - inv_title_w
    pdf.fixed_color(title_x, content_top + 14, "INVOICE", 20, bold=True, color=_DARK_TEXT)
    pdf.set_stroke_color(*_DARK_TEXT)
    pdf.draw_line(title_x, content_top + 21, right_x, content_top + 21)
    num_text = invoice_number
    pdf.fixed_color(
        _right_x(num_text, 11, right_x), content_top + 31, num_text, 11, bold=True, color=_DARK_TEXT
    )
    issue_text = f"Issue: {invoice_date.strftime('%d %b %Y')}"
    due_text = f"Due:   {due_date.strftime('%d %b %Y')}"
    pdf.fixed_color(
        _right_x(issue_text, 8, right_x), content_top + 46, issue_text, 8, color=_MUTED_TEXT
    )
    pdf.fixed_color(
        _right_x(due_text, 8, right_x), content_top + 57, due_text, 8, color=_MUTED_TEXT
    )
    right_bottom = content_top + 65

    # Horizontal rule after ~2 blank lines of breathing room
    rule_y = max(left_y, right_bottom) + 16
    pdf.set_stroke_color(*_DARK_TEXT)
    pdf.draw_line(MARGIN, rule_y, PAGE_W - MARGIN, rule_y)

    # -- Bill To (client billing block) + status badge -------------------------------
    label_y = rule_y + 20
    name_y = label_y + 15
    pdf.fixed_color(MARGIN, label_y, "BILL TO", 8, bold=True, color=_MUTED_TEXT)
    pdf.fixed_color(MARGIN, name_y, client_name, 13, bold=True, color=_DARK_TEXT)
    left_y = name_y + 18
    if client_address:
        for addr_line in _wrap(client_address.replace("\n", ", "), 300, 9):
            pdf.fixed_color(MARGIN, left_y, addr_line, 9, color=_MUTED_TEXT)
            left_y += 12
    if client_gstin:
        pdf.fixed_color(MARGIN, left_y, f"GSTIN: {client_gstin}", 9, color=_MUTED_TEXT)
        left_y += 12
    if project_code or project_name:
        what_for = "For · " + "  ".join(p for p in (project_code, project_name) if p)
        pdf.fixed_color(MARGIN, left_y + 2, what_for, 9, color=_MUTED_TEXT)
        left_y += 16
    pdf.y = left_y + 8

    _draw_status_badge(pdf, PAGE_W - MARGIN, label_y - 3, status)

    # -- Items table: Description | HSN/SAC | Qty | Rate | Amount --------------------
    col_desc = MARGIN + 4
    desc_width = 245
    col_hsn = MARGIN + 260
    qty_right = MARGIN + 340
    rate_right = MARGIN + 435
    amount_right = PAGE_W - MARGIN - 4
    desc_line_h = 9 * 1.45

    def _table_header_row() -> None:
        top_rule_y = pdf.y
        baseline = top_rule_y + 4 + 8 * _ASC
        pdf.set_stroke_color(*_DARK_TEXT)
        pdf.draw_line(MARGIN, top_rule_y, PAGE_W - MARGIN, top_rule_y)
        pdf.fixed_color(col_desc, baseline, "DESCRIPTION", 8, bold=True, color=_DARK_TEXT)
        pdf.fixed_color(col_hsn, baseline, "HSN/SAC", 8, bold=True, color=_DARK_TEXT)
        pdf.fixed_color(
            _right_x("QTY", 8, qty_right), baseline, "QTY", 8, bold=True, color=_DARK_TEXT
        )
        pdf.fixed_color(
            _right_x("RATE", 8, rate_right), baseline, "RATE", 8, bold=True, color=_DARK_TEXT
        )
        pdf.fixed_color(
            _right_x("AMOUNT", 8, amount_right), baseline, "AMOUNT", 8, bold=True, color=_DARK_TEXT
        )
        under_rule_y = _rule_below(baseline, 8)
        pdf.set_stroke_color(*_GRAY_LINE)
        pdf.draw_line(MARGIN, under_rule_y, PAGE_W - MARGIN, under_rule_y)
        pdf.y = under_rule_y + 8

    pdf.y += 6
    _table_header_row()
    last_baseline = pdf.y

    for idx, item in enumerate(items):
        desc = str(item.get("description", ""))
        desc_lines = _wrap(desc, desc_width, 9)
        content_h = max(len(desc_lines) * desc_line_h, 18)
        row_total = content_h + 8

        # Explicit pagination: never let a row straddle the bottom margin.
        if pdf.y + row_total > PAGE_H - MARGIN:
            pdf._new_page()
            pdf.y += 6
            _table_header_row()

        line_start_y = pdf.y
        baseline = line_start_y
        for dl in desc_lines:
            pdf.fixed_color(col_desc, baseline, dl, 9, color=_DARK_TEXT)
            baseline += desc_line_h
        last_baseline = line_start_y + (len(desc_lines) - 1) * desc_line_h
        hsn_text = str(item.get("hsn_sac") or "")
        if hsn_text:
            pdf.fixed_color(col_hsn, line_start_y, hsn_text, 9, color=_MUTED_TEXT)
        qty_text = _format_qty(item.get("quantity", 1))
        pdf.fixed_color(
            _right_x(qty_text, 9, qty_right), line_start_y, qty_text, 9, color=_DARK_TEXT
        )
        rate_text = format_inr(item.get("rate", 0))
        pdf.fixed_color(
            _right_x(rate_text, 9, rate_right), line_start_y, rate_text, 9, color=_DARK_TEXT
        )
        amount_text = format_inr(item.get("amount", 0))
        pdf.fixed_color(
            _right_x(amount_text, 9, amount_right), line_start_y, amount_text, 9, color=_DARK_TEXT
        )
        pdf.y = line_start_y + row_total
        if idx < len(items) - 1:
            sep_y = _rule_below(last_baseline, 9)
            pdf.set_stroke_color(*_GRAY_LINE)
            pdf.draw_line(MARGIN, sep_y, PAGE_W - MARGIN, sep_y)

    close_y = _rule_below(last_baseline, 9)
    pdf.set_stroke_color(*_DARK_TEXT)
    pdf.draw_line(MARGIN, close_y, PAGE_W - MARGIN, close_y)
    pdf.y = close_y + 16

    # -- Totals (atomic block: never split across a page break) ----------------------
    label_x = MARGIN + 290
    value_right = PAGE_W - MARGIN

    def _totals_row(label: str, value: str, bold: bool = False, size: float = 9) -> None:
        pdf.fixed(label_x, pdf.y, label, size, bold=bold)
        vx = _right_x(value, size, value_right)
        pdf.fixed_color(vx, pdf.y, value, size, bold=bold, color=_DARK_TEXT)
        pdf.y += size * 1.75

    tax_rows = tax_lines or ([(f"GST ({tax_percent:g}%)", tax_amount)] if tax_amount > 0 else [])
    balance = total - paid_amount
    totals_h = 6 + (1 + len(tax_rows)) * 9 * 1.75 + 11 * 1.75 + 9 * 1.75 + 34
    if pdf.y + totals_h > PAGE_H - MARGIN:
        pdf._new_page()

    pdf.y += 6
    _totals_row("Subtotal (INR)", format_inr(subtotal))
    for label, amount in tax_rows:
        _totals_row(label, format_inr(amount))

    total_baseline = pdf.y + 11
    rule_above_total = _rule_above(total_baseline, 11, pad=3.0)
    pdf.set_stroke_color(*_DARK_TEXT)
    pdf.draw_line(label_x, rule_above_total, value_right, rule_above_total)
    pdf.y = total_baseline
    _totals_row("Total", format_inr(total), bold=True, size=11)

    _totals_row("Paid", format_inr(paid_amount), size=9)

    # -- Balance Due (outlined emphasis box) ------------------------------------------
    balance_text = f"INR {format_inr(balance)}"
    box_w = value_right - label_x + 12
    box_y = pdf.y
    baseline = _box_baseline(box_y, 28, 10)
    pdf.set_stroke_color(*_DARK_TEXT)
    pdf.draw_rect(label_x - 8, box_y, box_w, 28, fill=False, stroke=True)
    pdf.fixed_color(label_x, baseline, "BALANCE DUE", 10, bold=True, color=_DARK_TEXT)
    bx = _right_x(balance_text, 10, value_right - 4)
    pdf.fixed_color(bx, baseline, balance_text, 10, bold=True, color=_DARK_TEXT)
    pdf.y += 34

    # -- Payment details (left) + Notes/Terms (right); atomic on one page -------------
    pay_lines: list[str] = []
    if payment_details:
        for key, label in (
            ("bank_name", "Bank"),
            ("account_name", "A/C name"),
            ("account_number", "A/C no"),
            ("ifsc_code", "IFSC"),
            ("upi_id", "UPI"),
        ):
            if payment_details.get(key):
                pay_lines.append(f"{label}: {payment_details[key]}")

    note_chunks = [c for c in ((notes or "").strip(), (terms or "").strip()) if c]
    note_wrapped = [_wrap(c, 245, 8.5) for c in note_chunks]

    left_h = (16 + len(pay_lines) * 11.5) if pay_lines else 0
    right_h = 16 + sum(len(lines) * 11.5 + 4 for lines in note_wrapped)
    block_h = max(left_h, right_h)
    if block_h > 0:
        # +12 keeps the section clear of the balance box above it
        if pdf.y + 12 + block_h + 10 > PAGE_H - MARGIN:
            pdf._new_page()
            pdf.y = MARGIN
        col_split = MARGIN + 278
        top = pdf.y + 12
        if pay_lines:
            pdf.fixed_color(MARGIN, top, "PAYMENT DETAILS", 8, bold=True, color=_MUTED_TEXT)
            ly = top + 16
            for pl in pay_lines:
                pdf.fixed_color(MARGIN, ly, pl, 8.5, color=_DARK_TEXT)
                ly += 11.5
        if note_wrapped:
            pdf.fixed_color(col_split, top, "NOTES / TERMS", 8, bold=True, color=_MUTED_TEXT)
            ry = top + 16
            for lines in note_wrapped:
                for nl in lines:
                    pdf.fixed_color(col_split, ry, nl, 8.5, color=_DARK_TEXT)
                    ry += 11.5
                ry += 4
        pdf.y = top + block_h

    # -- Footer on every page ---------------------------------------------------------
    _stamp_page_footers(pdf, studio_name, gstin)

    return pdf.render()


def site_visit_pdf(
    project_code: str,
    project_name: str,
    visit_date,
    purpose: str | None,
    location: str | None,
    notes: str | None,
    attendance_notes: str | None,
    photos: list[dict],
) -> bytes:
    pdf = PdfBuilder()
    pdf.fixed(MARGIN, MARGIN, STUDIO_NAME, 14, bold=True)
    pdf.fixed(PAGE_W - MARGIN - 120, MARGIN, "SITE VISIT REPORT", 14, bold=True)
    pdf.fixed(PAGE_W - MARGIN - 120, MARGIN + 20, f"Date: {visit_date.isoformat()}", 9)
    pdf.hline(MARGIN + 36)
    pdf.text(MARGIN, "PROJECT", 9, bold=True)
    pdf.text(MARGIN, f"{project_code}  |  {project_name}", 11, bold=True)
    pdf.y += 14
    pdf.text(MARGIN, "PURPOSE", 9, bold=True)
    pdf.text(MARGIN, purpose or "(not recorded)", 10, width=PAGE_W - 2 * MARGIN)
    if location:
        pdf.text(MARGIN, "LOCATION", 9, bold=True)
        pdf.text(MARGIN, location, 10, width=PAGE_W - 2 * MARGIN)
    if notes:
        pdf.text(MARGIN, "NOTES", 9, bold=True)
        pdf.text(MARGIN, notes, 10, width=PAGE_W - 2 * MARGIN)
    if attendance_notes:
        pdf.text(MARGIN, "ATTENDANCE", 9, bold=True)
        pdf.text(MARGIN, attendance_notes, 10, width=PAGE_W - 2 * MARGIN)
    if photos:
        pdf.y += 10
        pdf.text(MARGIN, f"PHOTOS ({len(photos)})", 9, bold=True)
        for photo in photos:
            caption = photo.get("caption") or "photo"
            pdf.text(
                MARGIN, f"- {caption} - {photo.get('file_path', '')}", 9, width=PAGE_W - 2 * MARGIN
            )
    pdf.y = PAGE_H - MARGIN - 16
    pdf.hline(pdf.y)
    pdf.fixed(MARGIN, pdf.y + 20, "Generated by StudioERP", 8)
    return pdf.render()


def payslip_pdf(
    employee_name: str,
    employee_id: str,
    designation: str,
    month_label: str,
    working_days: int,
    gross_salary: Decimal,
    deductions: Decimal,
    net_pay: Decimal,
) -> bytes:
    pdf = PdfBuilder()
    pdf.fixed(MARGIN, MARGIN, STUDIO_NAME, 14, bold=True)
    pdf.fixed(PAGE_W - MARGIN - 120, MARGIN, "PAYSLIP", 16, bold=True)
    pdf.fixed(PAGE_W - MARGIN - 120, MARGIN + 20, f"Period: {month_label}", 9)
    pdf.hline(MARGIN + 36)
    y = MARGIN + 56
    pdf.text(MARGIN, "EMPLOYEE", 9, bold=True)
    pdf.text(MARGIN, employee_name, 11, bold=True)
    pdf.text(MARGIN, f"{employee_id}  |  {designation or 'N/A'}", 9)
    y = pdf.y + 16
    pdf.fixed(MARGIN, y, "Working days", 10)
    pdf.fixed(PAGE_W - MARGIN - 140, y, str(working_days), 10, bold=True)
    y += 18
    pdf.fixed(MARGIN, y, "Gross salary", 10)
    pdf.fixed(PAGE_W - MARGIN - 140, y, f"{gross_salary:,.2f}", 10, bold=True)
    y += 18
    pdf.fixed(MARGIN, y, "Deductions", 10)
    pdf.fixed(PAGE_W - MARGIN - 140, y, f"-{deductions:,.2f}", 10)
    y += 18
    pdf.fixed(MARGIN, y, "Net pay", 12, bold=True)
    pdf.fixed(PAGE_W - MARGIN - 140, y, f"{net_pay:,.2f}", 12, bold=True)
    pdf.hline(y + 18)
    pdf.fixed(MARGIN, y + 28, "Generated by StudioERP", 8)
    return pdf.render()


def timesheet_pdf(
    employee_name: str,
    employee_code: str | None,
    week_label: str,
    status: str,
    submitted_label: str | None,
    reviewer_name: str | None,
    rows: list[dict],
    total_hours: str,
) -> bytes:
    """Simple weekly timesheet receipt (kept deliberately plain for later customisation).

    ``rows`` items: {date: str, project: str, description: str, hours: str}.
    """
    pdf = PdfBuilder()
    pdf.fixed(MARGIN, MARGIN, STUDIO_NAME, 14, bold=True)
    pdf.fixed(PAGE_W - MARGIN - 120, MARGIN, "TIMESHEET", 14, bold=True)
    pdf.fixed(PAGE_W - MARGIN - 120, MARGIN + 20, f"Week: {week_label}", 9)
    pdf.hline(MARGIN + 36)

    y = MARGIN + 56
    pdf.fixed(MARGIN, y, "EMPLOYEE", 8)
    pdf.fixed(MARGIN, y + 14, employee_name, 11, bold=True)
    sub = employee_code or "-"
    pdf.fixed(MARGIN, y + 30, f"ID {sub}", 9)

    meta_x = PAGE_W / 2
    pdf.fixed(meta_x, y, "STATUS", 8)
    pdf.fixed(meta_x, y + 14, status.title(), 10, bold=True)
    meta_lines = []
    if submitted_label:
        meta_lines.append(f"Submitted: {submitted_label}")
    if reviewer_name:
        meta_lines.append(f"Reviewed by: {reviewer_name}")
    for i, line in enumerate(meta_lines):
        pdf.fixed(meta_x, y + 32 + i * 13, line, 9)

    # ── Entries table ──
    table_top = max(y + 60, MARGIN + 120)
    col_date = MARGIN
    col_project = MARGIN + 72
    col_desc = MARGIN + 200
    right_edge = PAGE_W - MARGIN
    desc_width = right_edge - 64 - col_desc

    header_y = table_top
    pdf.set_fill_color(240, 238, 233)
    pdf.draw_rect(MARGIN, header_y - 4, right_edge - MARGIN, 20, fill=True)
    pdf.set_fill_color(0, 0, 0)
    pdf.fixed(col_date, header_y + 2, "DATE", 9, bold=True)
    pdf.fixed(col_project, header_y + 2, "PROJECT", 9, bold=True)
    pdf.fixed(col_desc, header_y + 2, "WHAT WAS DONE", 9, bold=True)
    pdf.fixed(right_edge - 52, header_y + 2, "HOURS", 9, bold=True)

    pdf.y = header_y + 28
    for row in rows:
        row_top = pdf.y
        date_label = row.get("date", "")
        if len(date_label) >= 10:
            parsed = date.fromisoformat(date_label)
            date_label = parsed.strftime("%a %d %b")
        pdf.text(col_date, date_label, 9)
        pdf.text(col_project, row.get("project", "-"), 9, width=col_desc - col_project - 10)
        pdf.text(col_desc, row.get("description", ""), 9, width=desc_width)
        pdf.y = max(pdf.y, row_top + 14)
        pdf.fixed(right_edge - 52, row_top + 2, row.get("hours", "0"), 9)
        pdf.y = max(pdf.y, row_top + 26)
        pdf.set_stroke_color(225, 222, 214)
        pdf.hline(pdf.y - 6, MARGIN, right_edge)

    if not rows:
        pdf.text(MARGIN, "No entries were logged for this week.", 9)

    pdf.y += 6
    pdf.hline(pdf.y)
    pdf.fixed(right_edge - 140, pdf.y + 8, "Total hours", 10, bold=True)
    pdf.fixed(right_edge - 52, pdf.y + 8, total_hours, 10, bold=True)

    sign_y = min(pdf.y + 60, PAGE_H - MARGIN - 40)
    pdf.hline(sign_y, MARGIN, MARGIN + 180)
    pdf.fixed(MARGIN, sign_y + 6, "Employee signature", 8)
    pdf.hline(sign_y, PAGE_W - MARGIN - 180, PAGE_W - MARGIN)
    pdf.fixed(PAGE_W - MARGIN - 180, sign_y + 6, "Approved by", 8)

    footer_y = PAGE_H - MARGIN - 12
    pdf.hline(footer_y)
    pdf.fixed(MARGIN, footer_y + 14, f"{STUDIO_NAME} · Generated by StudioERP", 8)
    return pdf.render()


def timesheet_month_pdf(
    title: str,
    groups: list[dict],
    grand_total: str,
) -> bytes:
    """Month export of timesheet entries, one section per employee.

    ``groups`` items: {heading: str, rows: [{date, project, description,
    hours}], total_hours: str}. Flows across pages as needed.
    """
    pdf = PdfBuilder()
    right_edge = PAGE_W - MARGIN

    pdf.fixed(MARGIN, MARGIN, STUDIO_NAME, 14, bold=True)
    pdf.fixed(PAGE_W - MARGIN - 160, MARGIN, title, 11, bold=True)
    pdf.hline(MARGIN + 36)

    col_date = MARGIN
    col_project = MARGIN + 72
    col_desc = MARGIN + 200
    desc_width = right_edge - 64 - col_desc
    header_y_offset = 2

    for group in groups:
        pdf._ensure_room(90)
        if pdf.y > MARGIN:
            pdf.y += 18
        pdf.y += 6
        pdf.fixed(MARGIN, pdf.y, group["heading"], 11, bold=True)

        header_y = pdf.y + 22
        pdf.set_fill_color(240, 238, 233)
        pdf.draw_rect(MARGIN, header_y - 4, right_edge - MARGIN, 20, fill=True)
        pdf.set_fill_color(0, 0, 0)
        pdf.fixed(col_date, header_y + header_y_offset, "DATE", 9, bold=True)
        pdf.fixed(col_project, header_y + header_y_offset, "PROJECT", 9, bold=True)
        pdf.fixed(col_desc, header_y + header_y_offset, "WHAT WAS DONE", 9, bold=True)
        pdf.fixed(right_edge - 52, header_y + header_y_offset, "HOURS", 9, bold=True)

        pdf.y = header_y + 28
        for row in group["rows"]:
            row_top = pdf.y
            date_label = row.get("date", "")
            if len(date_label) >= 10:
                parsed = date.fromisoformat(date_label)
                date_label = parsed.strftime("%a %d %b")
            pdf.text(col_date, date_label, 9)
            pdf.text(col_project, row.get("project", "-"), 9, width=col_desc - col_project - 10)
            pdf.text(
                col_desc,
                str(row.get("description", "")),
                9,
                width=desc_width,
            )
            pdf.y = max(pdf.y, row_top + 14)
            pdf.fixed(right_edge - 52, row_top + 2, row.get("hours", "0"), 9)
            pdf.y = max(pdf.y, row_top + 26)
            pdf.set_stroke_color(225, 222, 214)
            pdf.hline(pdf.y - 6, MARGIN, right_edge)

        if not group["rows"]:
            pdf.text(MARGIN, "No entries logged.", 9)

        pdf.y += 4
        pdf.hline(pdf.y)
        pdf.fixed(right_edge - 140, pdf.y + 8, "Employee total", 10, bold=True)
        pdf.fixed(right_edge - 52, pdf.y + 8, group["total_hours"], 10, bold=True)
        pdf.y += 24

    pdf._ensure_room(50)
    pdf.hline(pdf.y)
    pdf.fixed(right_edge - 140, pdf.y + 8, "Grand total", 11, bold=True)
    pdf.fixed(right_edge - 52, pdf.y + 8, grand_total, 11, bold=True)

    footer_y = PAGE_H - MARGIN - 12
    pdf.hline(footer_y)
    pdf.fixed(MARGIN, footer_y + 14, f"{STUDIO_NAME} · Generated by StudioERP", 8)
    return pdf.render()


def timesheet_report_pdf(
    title: str,
    filters_line: str,
    employees: list[dict],
) -> bytes:
    """Per-employee timesheet report.

    ``employees`` items: {user_id, employee_name, employee_id,
    department, total_hours: str, groups: [{label, hours: str, rows:
    [{date, project, description, hours}]}]}.

    Layout contract (the "many pages" case): every employee STARTS on a
    fresh page; if one employee's section outgrows the page it flows
    onto continuation pages — each new page re-stamps a small
    "<name> - continued" banner — before the next employee starts.
    Single-employee reports look identical to multi-employee ones,
    just with one section.
    """
    pdf = PdfBuilder()
    right_edge = PAGE_W - MARGIN

    def stamp_employee_header(name: str, subline: str) -> None:
        pdf.fixed(MARGIN, MARGIN, STUDIO_NAME, 14, bold=True)
        pdf.fixed(PAGE_W - MARGIN - 160, MARGIN, title, 11, bold=True)
        pdf.hline(MARGIN + 36)
        y = MARGIN + 46
        pdf.fixed(MARGIN, y, name, 13, bold=True)
        pdf.fixed(MARGIN, y + 18, subline, 9)
        pdf.y = y + 30

    # Report header on page one.
    pdf.fixed(MARGIN, MARGIN, STUDIO_NAME, 14, bold=True)
    pdf.fixed(PAGE_W - MARGIN - 160, MARGIN, title, 11, bold=True)
    pdf.hline(MARGIN + 36)
    pdf.y = MARGIN + 48
    pdf.text(MARGIN, filters_line, 9)

    col_project = MARGIN
    col_desc = MARGIN + 190
    desc_width = right_edge - 64 - col_desc

    for emp_index, emp in enumerate(employees):
        if emp_index > 0:
            pdf._new_page()

        meta_bits = [emp.get("employee_id") or f"User #{emp.get('user_id', '?')}"]
        if emp.get("department"):
            meta_bits.append(str(emp["department"]))
        meta_bits.append(f"Total {emp['total_hours']}h")
        heading = str(emp["employee_name"])
        subline = " · ".join(meta_bits)
        stamp_employee_header(heading, subline)
        first_content_on_page = True

        def ensure_room_with_banner(needed: float, name: str = heading) -> None:
            nonlocal first_content_on_page
            pages_before = len(pdf.pages)
            pdf._ensure_room(needed)
            if len(pdf.pages) > pages_before and not first_content_on_page:
                # Fresh page mid-section: stamp a continuation banner.
                pdf.set_fill_color(240, 238, 233)
                pdf.draw_rect(MARGIN, MARGIN, right_edge - MARGIN, 22, fill=True)
                pdf.set_fill_color(0, 0, 0)
                pdf.fixed(MARGIN + 6, MARGIN + 6, f"{name} - continued", 9, bold=True)
                pdf.y = MARGIN + 32

        for group in emp["groups"]:
            estimate = 34 + 16 * min(len(group["rows"]) or 1, 8)
            ensure_room_with_banner(estimate)

            pdf.y += 10
            label_y = pdf.y
            pdf.fixed(MARGIN, label_y, group["label"], 10.5, bold=True)
            pdf.fixed(right_edge - 90, label_y, f"{group['hours']} h", 10.5, bold=True)
            pdf.hline(label_y + 15)
            pdf.y = label_y + 22

            for row in group["rows"]:
                ensure_room_with_banner(20)
                row_top = pdf.y
                date_label = row.get("date") or ""
                if len(date_label) >= 10:
                    parsed = date.fromisoformat(date_label)
                    date_label = parsed.strftime("%a %d %b")
                x_proj = col_project + (58 if date_label else 0)
                if date_label:
                    pdf.text(col_project, date_label, 9)
                pdf.text(x_proj, row["project"], 9, width=col_desc - x_proj - 10)
                pdf.text(
                    col_desc,
                    str(row.get("description") or ""),
                    9,
                    width=desc_width,
                )
                pdf.y = max(pdf.y, row_top + 14)
                pdf.fixed(right_edge - 52, row_top + 2, str(row["hours"]), 9)
                pdf.y = max(pdf.y, row_top + 20)
                pdf.set_stroke_color(225, 222, 214)
                pdf.hline(pdf.y - 5, MARGIN, right_edge)

            if not group["rows"]:
                pdf.text(col_project, "No entries logged.", 9)
            first_content_on_page = False

        pdf._ensure_room(40)
        pdf.y += 4
        pdf.hline(pdf.y)
        pdf.fixed(right_edge - 140, pdf.y + 8, "Employee total", 10.5, bold=True)
        pdf.fixed(right_edge - 52, pdf.y + 8, str(emp["total_hours"]), 10.5, bold=True)
        pdf.y += 26

    footer_y = PAGE_H - MARGIN - 12
    pdf.hline(footer_y)
    pdf.fixed(MARGIN, footer_y + 14, f"{STUDIO_NAME} · Generated by StudioERP", 8)
    return pdf.render()
