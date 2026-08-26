"""Dependency-free .xlsx writer (zip of SpreadsheetML parts).

Produces professional, styled Excel workbooks with colours, borders,
number formats, column widths, freeze panes, and merged title rows.

Style IDs used across the workbook:

  0  – Normal text
  1  – Table header (dark blue bg, white bold text, thin border)
  2  – Title row (16 pt bold, dark blue text)
  3  – Subtitle (11 pt, grey text)
  4  – Section header (12 pt bold)
  5  – Currency text (#,##0.00)
  6  – Percentage (0.0%)
  7  – Integer with commas (#,##0)
  8  – Summary metric label (bold, light-blue bg, thin border)
  9  – Summary metric value (bold, light-blue bg, currency)
 10  – Alternating row (light grey bg)
 11  – Alternating currency row
 12  – Alternating percentage row
 13  – Date (yyyy-mm-dd)
 14  – Date alternating
 15  – KPI card value (14 pt bold, green bg)
 16  – KPI card value (14 pt bold, orange bg)
 17  – KPI card value (14 pt bold, red bg)
 18  – Subtotal row (bold, medium blue bg)
 19  – Subtotal currency
 20  – One-decimal number (#,##0.0)
 21  – One-decimal alternating
"""

import io
import zipfile
from decimal import Decimal
from xml.sax.saxutils import escape

_XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
_WORKBOOK_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
_STYLES_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles"

# ── Number format IDs (built-in + custom) ───────────────────────
_FMT_CURRENCY = '₹#,##0.00'
_FMT_INTEGER = '#,##0'
_FMT_PERCENT = '0.0%'
_FMT_DATE = 'yyyy-mm-dd'
_FMT_DECIMAL1 = '#,##0.0'


def _col_letter(index: int) -> str:
    letters = ""
    index += 1
    while index > 0:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _cell_ref(row: int, col: int) -> str:
    return f"{_col_letter(col)}{row + 1}"


# ── XML builders ────────────────────────────────────────────────


def _fonts_xml() -> bytes:
    """All font definitions used by cellXfs styles."""
    parts = [
        '<fonts count="8">',
        # 0: Normal 11pt Calibri
        '<font><sz val="11"/><name val="Calibri"/></font>',
        # 1: Bold 11pt
        '<font><b/><sz val="11"/><name val="Calibri"/></font>',
        # 2: Title 16pt bold dark blue
        '<font><b/><sz val="16"/><name val="Calibri"/><color rgb="FF1F4E79"/></font>',
        # 3: Subtitle 11pt grey
        '<font><sz val="11"/><name val="Calibri"/><color rgb="FF808080"/></font>',
        # 4: Section header 12pt bold
        '<font><b/><sz val="12"/><name val="Calibri"/></font>',
        # 5: Header white bold 11pt
        '<font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font>',
        # 6: KPI 14pt bold
        '<font><b/><sz val="14"/><name val="Calibri"/></font>',
        # 7: Subtotal 11pt bold
        '<font><b/><sz val="11"/><name val="Calibri"/></font>',
        '</fonts>',
    ]
    return "".join(parts).encode("utf-8")


def _fills_xml() -> bytes:
    """Fill patterns used by cellXfs styles."""
    parts = [
        '<fills count="11">',
        '<fill><patternFill patternType="none"/></fill>',           # 0
        '<fill><patternFill patternType="gray125"/></fill>',        # 1
        '<fill><patternFill patternType="solid"><fgColor rgb="FF1F4E79"/></patternFill></fill>',  # 2 dark blue
        '<fill><patternFill patternType="solid"><fgColor rgb="FFD6E4F0"/></patternFill></fill>',  # 3 light blue
        '<fill><patternFill patternType="solid"><fgColor rgb="FFF2F2F2"/></patternFill></fill>',  # 4 light grey
        '<fill><patternFill patternType="solid"><fgColor rgb="FFC6EFCE"/></patternFill></fill>',  # 5 green
        '<fill><patternFill patternType="solid"><fgColor rgb="FFFCE4D6"/></patternFill></fill>',  # 6 orange
        '<fill><patternFill patternType="solid"><fgColor rgb="FFFFC7CE"/></patternFill></fill>',  # 7 red
        '<fill><patternFill patternType="solid"><fgColor rgb="FF4472C4"/></patternFill></fill>',  # 8 medium blue
        '<fill><patternFill patternType="solid"><fgColor rgb="FF006100"/></patternFill></fill>',  # 9 dark green
        '<fill><patternFill patternType="solid"><fgColor rgb="FFFFFFFF"/></patternFill></fill>',  # 10 white
        '</fills>',
    ]
    return "".join(parts).encode("utf-8")


def _borders_xml() -> bytes:
    thin = (
        '<border><left style="thin"><color auto="1"/></left>'
        '<right style="thin"><color auto="1"/></right>'
        '<top style="thin"><color auto="1"/></top>'
        '<bottom style="thin"><color auto="1"/></bottom>'
        '<diagonal/></border>'
    )
    bottom_medium = (
        '<border><left/><right/><top/>'
        '<bottom style="medium"><color auto="1"/></bottom>'
        '<diagonal/></border>'
    )
    return (
        '<borders count="3">'
        '<border><left/><right/><top/><bottom/><diagonal/></border>'
        f'{thin}'
        f'{bottom_medium}'
        '</borders>'
    ).encode("utf-8")


def _cell_style_xfs_xml() -> bytes:
    return (
        '<cellStyleXfs count="1">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
        '</cellStyleXfs>'
    ).encode("utf-8")


def _fmt_id(fmt: str | None) -> int:
    """Map a number format string to the numFmt index used in cellXfs."""
    if fmt is None:
        return 0
    mapping = {
        _FMT_CURRENCY: 164,
        _FMT_INTEGER: 165,
        _FMT_PERCENT: 166,
        _FMT_DATE: 167,
        _FMT_DECIMAL1: 168,
    }
    return mapping.get(fmt, 0)


def _cell_xfs_xml() -> bytes:
    """All cell format definitions."""
    # (numFmt, font, fill, border, apply_numFmt, apply_font, apply_fill, apply_border)
    styles = [
        # 0: Normal
        (None, 0, 0, 0, False, False, False, False),
        # 1: Table header (dark blue bg, white bold, thin border)
        (None, 5, 2, 1, False, True, True, True),
        # 2: Title (16pt bold, dark blue)
        (None, 2, 0, 0, False, True, False, False),
        # 3: Subtitle (grey)
        (None, 3, 0, 0, False, True, False, False),
        # 4: Section header (12pt bold)
        (None, 4, 0, 0, False, True, False, False),
        # 5: Currency
        (_FMT_CURRENCY, 0, 0, 1, True, False, False, True),
        # 6: Percentage
        (_FMT_PERCENT, 0, 0, 1, True, False, False, True),
        # 7: Integer with commas
        (_FMT_INTEGER, 0, 0, 1, True, False, False, True),
        # 8: Summary metric label (bold, light-blue, border)
        (None, 1, 3, 1, False, True, True, True),
        # 9: Summary metric value (bold, light-blue, currency, border)
        (_FMT_CURRENCY, 1, 3, 1, True, True, True, True),
        # 10: Alternating row (grey bg)
        (None, 0, 4, 1, False, False, True, True),
        # 11: Alternating currency
        (_FMT_CURRENCY, 0, 4, 1, True, False, True, True),
        # 12: Alternating percentage
        (_FMT_PERCENT, 0, 4, 1, True, False, True, True),
        # 13: Date
        (_FMT_DATE, 0, 0, 1, True, False, False, True),
        # 14: Date alternating
        (_FMT_DATE, 0, 4, 1, True, False, True, True),
        # 15: KPI green
        (_FMT_CURRENCY, 6, 5, 1, True, True, True, True),
        # 16: KPI orange
        (_FMT_CURRENCY, 6, 6, 1, True, True, True, True),
        # 17: KPI red
        (_FMT_CURRENCY, 6, 7, 1, True, True, True, True),
        # 18: Subtotal (bold, medium blue bg)
        (None, 7, 8, 2, False, True, True, True),
        # 19: Subtotal currency
        (_FMT_CURRENCY, 7, 8, 2, True, True, True, True),
        # 20: One-decimal
        (_FMT_DECIMAL1, 0, 0, 1, True, False, False, True),
        # 21: One-decimal alternating
        (_FMT_DECIMAL1, 0, 4, 1, True, False, True, True),
        # 22: Normal + thin border (for text columns in data rows)
        (None, 0, 0, 1, False, False, False, True),
        # 23: Alternating + thin border
        (None, 0, 4, 1, False, False, True, True),
        # 24: Summary integer (bold, light-blue)
        (_FMT_INTEGER, 1, 3, 1, True, True, True, True),
        # 25: Summary percentage
        (_FMT_PERCENT, 1, 3, 1, True, True, True, True),
        # 26: Integer alternating
        (_FMT_INTEGER, 0, 4, 1, True, False, True, True),
        # 27: Bold + border
        (None, 1, 0, 1, False, True, False, True),
        # 28: Currency + border
        (_FMT_CURRENCY, 0, 0, 1, True, False, False, True),
        # 29: Integer + border
        (_FMT_INTEGER, 0, 0, 1, True, False, False, True),
        # 30: Percentage + border
        (_FMT_PERCENT, 0, 0, 1, True, False, False, True),
        # 31: Date + border
        (_FMT_DATE, 0, 0, 1, True, False, False, True),
        # 32: One-decimal + border
        (_FMT_DECIMAL1, 0, 0, 1, True, False, False, True),
    ]

    parts = [f'<cellXfs count="{len(styles)}">']
    for numFmt, font, fill, border, a_nf, a_font, a_fill, a_border in styles:
        fmt_id_val = _fmt_id(numFmt)
        attrs = f'numFmtId="{fmt_id_val}" fontId="{font}" fillId="{fill}" borderId="{border}" xfId="0"'
        apply = []
        if a_nf:
            apply.append('applyNumberFormat="1"')
        if a_font:
            apply.append('applyFont="1"')
        if a_fill:
            apply.append('applyFill="1"')
        if a_border:
            apply.append('applyBorder="1"')
        if apply:
            attrs += " " + " ".join(apply)
        parts.append(f'<xf {attrs}/>')
    parts.append('</cellXfs>')
    return "".join(parts).encode("utf-8")


def _styles_xml() -> bytes:
    num_fmts = (
        '<numFmts count="5">'
        f'<numFmt numFmtId="164" formatCode="{_FMT_CURRENCY}"/>'
        f'<numFmt numFmtId="165" formatCode="{_FMT_INTEGER}"/>'
        f'<numFmt numFmtId="166" formatCode="{_FMT_PERCENT}"/>'
        f'<numFmt numFmtId="167" formatCode="{_FMT_DATE}"/>'
        f'<numFmt numFmtId="168" formatCode="{_FMT_DECIMAL1}"/>'
        '</numFmts>'
    )
    parts = [
        _XML_DECL,
        f'<styleSheet xmlns="{_MAIN_NS}">',
        num_fmts,
        _fonts_xml().decode(),
        _fills_xml().decode(),
        _borders_xml().decode(),
        _cell_style_xfs_xml().decode(),
        _cell_xfs_xml().decode(),
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>',
        '</styleSheet>',
    ]
    return "".join(parts).encode("utf-8")


# ── Cell / row / sheet XML ──────────────────────────────────────

_STYLE_MAP = {
    "title": 2,
    "subtitle": 3,
    "section": 4,
    "header": 1,
    "text": 22,
    "text_alt": 23,
    "currency": 5,
    "currency_alt": 11,
    "percent": 6,
    "percent_alt": 12,
    "integer": 7,
    "integer_alt": 26,
    "date": 13,
    "date_alt": 14,
    "decimal1": 20,
    "decimal1_alt": 21,
    "summary_label": 8,
    "summary_value": 9,
    "summary_integer": 24,
    "summary_percent": 25,
    "kpi_green": 15,
    "kpi_orange": 16,
    "kpi_red": 17,
    "subtotal": 18,
    "subtotal_currency": 19,
    "normal": 0,
    "text_border": 22,
    "currency_border": 28,
    "integer_border": 29,
    "percent_border": 30,
    "date_border": 31,
    "decimal1_border": 32,
}


def _cell_xml(row: int, col: int, value, style: str | None = None) -> str:
    ref = _cell_ref(row, col)
    s_attr = f' s="{_STYLE_MAP.get(style, 0)}"' if style else ""
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"{s_attr}><v>{"1" if value else "0"}</v></c>'
    if isinstance(value, (int, float, Decimal)):
        return f'<c r="{ref}"{s_attr}><v>{value}</v></c>'
    text = "" if value is None else escape(str(value))
    return f'<c r="{ref}" t="inlineStr"{s_attr}><is><t xml:space="preserve">{text}</t></is></c>'


def _compute_col_widths(
    columns: list[str], rows: list[list], col_formats: list[str] | None = None
) -> list[float]:
    """Estimate reasonable column widths based on content."""
    widths: list[float] = []
    for ci, header in enumerate(columns):
        max_len = len(str(header))
        for row in rows[:50]:  # sample first 50 rows
            if ci < len(row):
                val = row[ci]
                if val is None:
                    continue
                if isinstance(val, (int, float, Decimal)):
                    s = f"{val:,.2f}" if col_formats and ci < len(col_formats) and col_formats[ci] == "currency" else str(val)
                    max_len = max(max_len, len(s))
                else:
                    max_len = max(max_len, len(str(val)))
        # Clamp: min 12, max 50, add padding
        widths.append(min(50, max(12, max_len + 4)))
    return widths


def _sheet_xml(
    columns: list[str],
    rows: list[list],
    col_styles: list[str | None] | None = None,
    alt_col_styles: list[str | None] | None = None,
    col_formats: list[str] | None = None,
    freeze_row: int = 0,
    merge_cells: list[tuple[int, int, int, int]] | None = None,
    extra_rows_before: list[list[tuple[str, str | None]]] | None = None,
    extra_rows_after: list[list[tuple[str, str | None]]] | None = None,
) -> bytes:
    lines = [_XML_DECL]
    lines.append(f'<worksheet xmlns="{_MAIN_NS}">')

    # Sheet view with freeze panes
    if freeze_row > 0:
        lines.append(
            '<sheetViews><sheetView tabSelected="1" workbookViewId="0">'
            f'<pane ySplit="{freeze_row}" topLeftCell="A{freeze_row + 1}" '
            'activePane="bottomLeft" state="frozen"/>'
            '</sheetView></sheetViews>'
        )

    # Column widths
    widths = _compute_col_widths(columns, rows, col_formats)
    lines.append('<cols>')
    for ci, w in enumerate(widths, start=1):
        lines.append(f'<col min="{ci}" max="{ci}" width="{w}" customWidth="1"/>')
    lines.append('</cols>')

    lines.append('<sheetData>')

    current_row = 0

    # Extra rows before the header (titles, subtitles, etc.)
    if extra_rows_before:
        for row_data in extra_rows_before:
            lines.append(f'<row r="{current_row + 1}">')
            for ci, cell in enumerate(row_data):
                if isinstance(cell, tuple) and len(cell) == 2:
                    value, style = cell
                else:
                    value, style = str(cell), None
                lines.append(_cell_xml(current_row, ci, value, style))
            lines.append('</row>')
            current_row += 1

    # Header row
    lines.append(f'<row r="{current_row + 1}">')
    for ci, header in enumerate(columns):
        lines.append(_cell_xml(current_row, ci, header, "header"))
    lines.append('</row>')
    current_row += 1

    # Data rows
    for ri, row in enumerate(rows):
        lines.append(f'<row r="{current_row + 1}">')
        is_alt = ri % 2 == 1
        for ci, value in enumerate(row):
            style = None
            if col_styles and ci < len(col_styles):
                style = col_styles[ci]
                if is_alt and alt_col_styles and ci < len(alt_col_styles):
                    style = alt_col_styles[ci]
            elif is_alt:
                style = "text_alt"
            lines.append(_cell_xml(current_row, ci, value, style))
        lines.append('</row>')
        current_row += 1

    # Extra rows after data (subtotals, footers, etc.)
    if extra_rows_after:
        for row_data in extra_rows_after:
            lines.append(f'<row r="{current_row + 1}">')
            for ci, cell in enumerate(row_data):
                if isinstance(cell, tuple) and len(cell) == 2:
                    value, style = cell
                else:
                    value, style = str(cell), None
                lines.append(_cell_xml(current_row, ci, value, style))
            lines.append('</row>')
            current_row += 1

    lines.append('</sheetData>')

    # Merged cells
    if merge_cells:
        lines.append(f'<mergeCells count="{len(merge_cells)}">')
        for start_row, start_col, end_row, end_col in merge_cells:
            start_ref = _cell_ref(start_row, start_col)
            end_ref = _cell_ref(end_row, end_col)
            lines.append(f'<mergeCell ref="{start_ref}:{end_ref}"/>')
        lines.append('</mergeCells>')

    lines.append('</worksheet>')
    return "".join(lines).encode("utf-8")


# ── Package parts ───────────────────────────────────────────────


def _content_types(sheet_count: int) -> bytes:
    parts = [_XML_DECL, f'<Types xmlns="{_CONTENT_TYPES_NS}">']
    parts.append(
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    )
    parts.append('<Default Extension="xml" ContentType="application/xml"/>')
    parts.append(
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    )
    parts.append(
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    )
    for i in range(1, sheet_count + 1):
        parts.append(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    parts.append("</Types>")
    return "".join(parts).encode("utf-8")


def _root_rels() -> bytes:
    return (
        _XML_DECL
        + f'<Relationships xmlns="{_REL_NS}">'
        + '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        + "</Relationships>"
    ).encode("utf-8")


def _workbook_xml(names: list[str]) -> bytes:
    parts = [
        _XML_DECL,
        f'<workbook xmlns="{_MAIN_NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>',
    ]
    for index, name in enumerate(names, start=1):
        parts.append(f'<sheet name="{escape(name[:31])}" sheetId="{index}" r:id="rId{index}"/>')
    parts.append("</sheets></workbook>")
    return "".join(parts).encode("utf-8")


def _workbook_rels(sheet_count: int) -> bytes:
    parts = [_XML_DECL, f'<Relationships xmlns="{_REL_NS}">']
    for i in range(1, sheet_count + 1):
        parts.append(
            f'<Relationship Id="rId{i}" Type="{_WORKBOOK_REL_TYPE}" Target="worksheets/sheet{i}.xml"/>'
        )
    parts.append(
        f'<Relationship Id="rId{sheet_count + 1}" Type="{_STYLES_REL_TYPE}" Target="styles.xml"/>'
    )
    parts.append("</Relationships>")
    return "".join(parts).encode("utf-8")


# ── Public API ──────────────────────────────────────────────────


def write_xlsx(sheets: list[dict]) -> bytes:
    """Write a styled .xlsx workbook.

    Each sheet dict may contain:

        name          – Sheet tab name (required)
        columns       – Header labels (required)
        rows          – 2-D list of data (required)
        col_styles    – Per-column style name (e.g. ["text","currency","percent"])
        alt_col_styles– Per-column style for alternating rows
        col_formats   – Per-column format hint for width estimation
        freeze_row    – Number of header rows to freeze (default 0)
        merge_cells   – List of (sr, sc, er, ec) merge ranges
        extra_rows_before – Rows inserted above the header.
                            Each row is [(value, style), …]
        extra_rows_after  – Rows appended after the data.
                            Each row is [(value, style), …]

    The old simple format ``{"name": ..., "columns": [...], "rows": [[...]]}``
    still works identically.
    """
    if not sheets:
        raise ValueError("At least one sheet is required")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types(len(sheets)))
        archive.writestr("_rels/.rels", _root_rels())
        archive.writestr("xl/workbook.xml", _workbook_xml([s["name"] for s in sheets]))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(sheets)))
        archive.writestr("xl/styles.xml", _styles_xml())
        for index, sheet in enumerate(sheets, start=1):
            archive.writestr(
                f"xl/worksheets/sheet{index}.xml",
                _sheet_xml(
                    columns=sheet["columns"],
                    rows=sheet.get("rows", []),
                    col_styles=sheet.get("col_styles"),
                    alt_col_styles=sheet.get("alt_col_styles"),
                    col_formats=sheet.get("col_formats"),
                    freeze_row=sheet.get("freeze_row", 0),
                    merge_cells=sheet.get("merge_cells"),
                    extra_rows_before=sheet.get("extra_rows_before"),
                    extra_rows_after=sheet.get("extra_rows_after"),
                ),
            )
    return buffer.getvalue()
