"""Dependency-free .xlsx writer (zip of SpreadsheetML parts)."""

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


def _col_letter(index: int) -> str:
    letters = ""
    index += 1
    while index > 0:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _cell_ref(row: int, col: int) -> str:
    return f"{_col_letter(col)}{row + 1}"


def _cell_xml(row: int, col: int, value) -> str:
    ref = _cell_ref(row, col)
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"><v>{"1" if value else "0"}</v></c>'
    if isinstance(value, (int, float, Decimal)):
        return f'<c r="{ref}"><v>{value}</v></c>'
    text = "" if value is None else escape(str(value))
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def _sheet_xml(columns: list[str], rows: list[list]) -> bytes:
    lines = [_XML_DECL]
    lines.append(f'<worksheet xmlns="{_MAIN_NS}"><sheetData>')
    lines.append('<row r="1">')
    for col, header in enumerate(columns):
        ref = _cell_ref(0, col)
        text = escape(str(header))
        lines.append(
            f'<c r="{ref}" t="inlineStr" s="1"><is><t xml:space="preserve">{text}</t></is></c>'
        )
    lines.append("</row>")
    for row_index, row in enumerate(rows, start=1):
        lines.append(f'<row r="{row_index + 1}">')
        for col, value in enumerate(row):
            lines.append(_cell_xml(row_index, col, value))
        lines.append("</row>")
    lines.append("</sheetData></worksheet>")
    return "".join(lines).encode("utf-8")


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


def _styles_xml() -> bytes:
    return (
        _XML_DECL
        + f'<styleSheet xmlns="{_MAIN_NS}">'
        + '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
        + '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
        + '<fills count="2"><fill><patternFill patternType="none"/></fill>'
        + '<fill><patternFill patternType="gray125"/></fill></fills>'
        + '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        + '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        + '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        + '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
        + "</styleSheet>"
    ).encode("utf-8")


def write_xlsx(sheets: list[dict]) -> bytes:
    """sheets: [{"name": str, "columns": [str], "rows": [[...]]}]"""
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
                _sheet_xml(sheet["columns"], sheet["rows"]),
            )
    return buffer.getvalue()
