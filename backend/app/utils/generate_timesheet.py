"""Timesheet PDF generation pipeline: Jinja2 templating + Playwright Chromium.

Provides:
- ``group_entries_by_date()`` — pre-processes raw entries into date-grouped
  structure for the template.
- ``render_timesheet_html()`` — renders the Jinja2 HTML template.
- ``generate_timesheet_pdf()`` — launches Chromium via Playwright and
  produces a paginated A4 PDF with headers, footers, and page counts.

The Chromium browser is lazily launched once and reused across requests
(singleton pattern) to avoid per-request process spawn overhead.
"""

import base64
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "timesheet"

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)

# ── Playwright browser singleton ────────────────────────────────────
_browser = None
_playwright = None


async def _get_browser():
    """Return the shared Chromium browser, launching on first call.

    If the previous browser was closed (e.g. event-loop restart during
    testing), both the Playwright instance and browser are recreated.
    """
    global _browser, _playwright
    if _browser is not None:
        try:
            if not _browser.is_connected():
                _browser = None
                _playwright = None
        except Exception:
            _browser = None
            _playwright = None
    if _browser is None:
        from playwright.async_api import async_playwright

        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch()
    return _browser


async def close_browser() -> None:
    """Shut down the shared browser (call on app shutdown)."""
    global _browser, _playwright
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright is not None:
        await _playwright.stop()
        _playwright = None


# ── Data URI helper ─────────────────────────────────────────────────


def logo_to_data_uri(logo_path: str | Path | None) -> str | None:
    """Convert an image file to a base64 data URI for inline HTML use.

    Returns ``None`` if *logo_path* is ``None`` or the file cannot be read.
    """
    if logo_path is None:
        return None
    try:
        raw = Path(logo_path).read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        suffix = Path(logo_path).suffix.lower()
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".webp": "image/webp",
        }.get(suffix, "image/png")
        return f"data:{mime};base64,{b64}"
    except Exception:
        logger.warning("Could not read logo file: %s", logo_path)
        return None


# ── Entry grouping ──────────────────────────────────────────────────


def group_entries_by_date(entries: list[dict]) -> list[dict]:
    """Group raw entry dicts by date for the HTML template.

    Each entry must have at least: ``date`` (str, "DD MMM" or ISO),
    ``hours``, ``project``, ``description``.  ``location`` is optional.

    Returns a list of groups::

        [{"date": "01 Aug", "color": "gray", "entries": [{...}, ...]}, ...]

    Consecutive date groups alternate between ``"gray"`` and ``"white"``
    so each day is visually distinct.
    """
    groups: list[dict] = []
    current_date = None
    current_group: dict | None = None
    color_cycle = ["gray", "white"]
    color_idx = 0

    for entry in entries:
        entry_date = entry["date"]
        if entry_date != current_date:
            if current_group is not None:
                color_idx += 1
            current_date = entry_date
            current_group = {
                "date": entry_date,
                "color": color_cycle[color_idx % 2],
                "entries": [],
            }
            groups.append(current_group)
        current_group["entries"].append(
            {
                "hours": entry.get("hours", ""),
                "project": entry.get("project", ""),
                "location": entry.get("location", ""),
                "description": entry.get("description", ""),
            }
        )

    return groups


# ── HTML rendering ──────────────────────────────────────────────────


def render_timesheet_html(context: dict) -> str:
    """Render the timesheet HTML template with the given context.

    Required keys: ``company_name``, ``company_tagline``, ``employee_name``,
    ``period_from``, ``period_to``, ``total_hours``, ``date_groups``.
    Optional: ``logo_path``, ``designation``, ``approved_by``.
    """
    template = _jinja_env.get_template("timesheet_template.html")
    return template.render(**context)


# ── PDF generation ──────────────────────────────────────────────────

_FOOTER_TEMPLATE = """\
<div style="font-size:8px; color:#888; width:100%%; display:flex; padding:0 16mm;">
  <span style="flex:1; text-align:left;">Generated on %(date)s</span>
  <span style="flex:1; text-align:center;">Confidential &ndash; Internal Use Only</span>
  <span style="flex:1; text-align:right;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>
"""


async def generate_timesheet_pdf(html_content: str) -> bytes:
    """Render HTML to a paginated A4 PDF via Playwright Chromium.

    Returns raw PDF bytes ready for an HTTP response.
    """
    from datetime import date as _date

    browser = await _get_browser()
    page = await browser.new_page()
    try:
        await page.set_content(html_content, wait_until="networkidle")
        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template='<div style="font-size:0;line-height:0;padding:0;margin:0;border:0;"></div>',
            footer_template=_FOOTER_TEMPLATE % {"date": _date.today().strftime("%d %b %Y")},
            margin={
                "top": "20mm",
                "bottom": "22mm",
                "left": "16mm",
                "right": "16mm",
            },
        )
        return pdf_bytes
    finally:
        await page.close()
