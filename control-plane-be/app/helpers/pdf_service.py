"""
Convert xlsx bytes → PDF bytes using LibreOffice headless.

LibreOffice is the only tool that reproduces an Excel file 1-to-1:
page layout, print areas, column/row sizes, images, shapes, and fonts
are all preserved exactly as Excel would render them to paper.

Concurrent safety:
  Each conversion gets its own temporary HOME directory so that
  multiple requests don't fight over LibreOffice's user-profile lock.
"""

import io
import logging
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger("app")

# Prefer `libreoffice`, fall back to `soffice` (alias used on some distros)
_SOFFICE = shutil.which("libreoffice") or shutil.which("soffice") or "libreoffice"


def _patch_sheet_fit_to_width(sheet_xml: bytes) -> bytes:
    """
    Patch a worksheet XML so LibreOffice scales all columns onto one page width.

    Two settings are needed:
      1. <sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>
         — tells Calc this sheet uses "fit-to-page" scaling mode.
      2. <pageSetup fitToWidth="1" fitToHeight="0" .../>
         — 1 page wide, unlimited pages tall, no explicit scale %.

    Works via simple regex replacement so all existing namespace
    declarations and other attributes are preserved intact.
    """
    text = sheet_xml.decode("utf-8")

    # ── 1. pageSetup ─────────────────────────────────────────────────────────
    ps = re.search(r'<((?:[\w]+:)?pageSetup)\b([^/]*?)(/?>)', text, re.DOTALL)
    if ps:
        attrs = ps.group(2)
        # Remove scale (overrides fitToWidth when present)
        attrs = re.sub(r'\s*\bscale="[^"]*"', '', attrs)
        # Set fitToWidth / fitToHeight
        if re.search(r'\bfitToWidth="', attrs):
            attrs = re.sub(r'\bfitToWidth="[^"]*"', 'fitToWidth="1"', attrs)
        else:
            attrs += ' fitToWidth="1"'
        if re.search(r'\bfitToHeight="', attrs):
            attrs = re.sub(r'\bfitToHeight="[^"]*"', 'fitToHeight="0"', attrs)
        else:
            attrs += ' fitToHeight="0"'
        new_tag = f'<{ps.group(1)}{attrs}{ps.group(3)}'
        text = text[:ps.start()] + new_tag + text[ps.end():]
    else:
        # Insert before <pageMargins> or before </worksheet>
        ins = re.search(r'<(?:[\w]+:)?pageMargins\b|</(?:[\w]+:)?worksheet>', text)
        if ins:
            new_ps = '<pageSetup fitToWidth="1" fitToHeight="0"/>'
            text = text[:ins.start()] + new_ps + text[ins.start():]

    # ── 2. sheetPr / pageSetUpPr ─────────────────────────────────────────────
    psp = re.search(r'<((?:[\w]+:)?pageSetUpPr)\b([^/]*?)/>', text)
    if psp:
        # Ensure fitToPage="1" is set
        attrs = psp.group(2)
        if re.search(r'\bfitToPage="', attrs):
            attrs = re.sub(r'\bfitToPage="[^"]*"', 'fitToPage="1"', attrs)
        else:
            attrs += ' fitToPage="1"'
        text = text[:psp.start()] + f'<{psp.group(1)}{attrs}/>' + text[psp.end():]
    else:
        spr = re.search(r'<((?:[\w]+:)?sheetPr)\b([^>]*)>', text)
        if spr:
            # Inject inside existing <sheetPr>
            text = text[:spr.end()] + '<pageSetUpPr fitToPage="1"/>' + text[spr.end():]
        else:
            # No <sheetPr> at all — insert one right after the opening <worksheet ...> tag
            ws = re.search(r'<(?:[\w]+:)?worksheet\b[^>]*>', text)
            if ws:
                text = text[:ws.end()] + '<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>' + text[ws.end():]

    return text.encode("utf-8")


def _apply_fit_to_width(xlsx_bytes: bytes) -> bytes:
    """
    Repack the xlsx, patching every worksheet XML with fit-to-width print settings.
    All other files (styles, drawings, media, rels, …) are copied unchanged.
    """
    in_buf  = io.BytesIO(xlsx_bytes)
    out_buf = io.BytesIO()

    with zipfile.ZipFile(in_buf, "r") as zf_in, \
         zipfile.ZipFile(out_buf, "w", zipfile.ZIP_DEFLATED) as zf_out:

        names = set(zf_in.namelist())

        # Discover worksheet paths from workbook rels (most reliable)
        sheet_paths: set[str] = set()
        try:
            if "xl/_rels/workbook.xml.rels" in names:
                rels_root = ET.fromstring(zf_in.read("xl/_rels/workbook.xml.rels"))
                for rel in rels_root:
                    if "worksheet" in rel.get("Type", "").lower():
                        target = rel.get("Target", "").lstrip("../")
                        sheet_paths.add("xl/" + target if not target.startswith("xl/") else target)
        except Exception:
            pass

        # Fallback: any xl/worksheets/sheet*.xml
        if not sheet_paths:
            sheet_paths = {n for n in names if re.match(r'xl/worksheets/sheet\d+\.xml$', n)}

        for item in zf_in.infolist():
            data = zf_in.read(item.filename)
            if item.filename in sheet_paths:
                try:
                    data = _patch_sheet_fit_to_width(data)
                except Exception:
                    pass  # keep original if patching fails
            zf_out.writestr(item, data)

    out_buf.seek(0)
    return out_buf.getvalue()


def xlsx_to_pdf(xlsx_bytes: bytes, timeout: int = 60) -> bytes:
    """
    Convert raw xlsx bytes to PDF bytes using LibreOffice headless.

    Page-fit behaviour:
      Before conversion, every worksheet is patched to use "fit to 1 page wide"
      print scaling so that no content overflows to the right.

    Parameters
    ----------
    xlsx_bytes : raw bytes of the .xlsx file
    timeout    : seconds to wait before killing LibreOffice (default 60)

    Returns
    -------
    bytes — raw PDF content

    Raises
    ------
    RuntimeError if LibreOffice is not installed or conversion fails.
    """
    if not shutil.which(_SOFFICE) and _SOFFICE == "libreoffice":
        raise RuntimeError(
            "LibreOffice is not installed. "
            "Add 'libreoffice' to the Dockerfile and rebuild the image."
        )

    # Patch all worksheets to fit-to-width before handing to LibreOffice
    try:
        xlsx_bytes = _apply_fit_to_width(xlsx_bytes)
    except Exception as exc:
        logger.warning("fit-to-width patch failed, using original xlsx: %s", exc)

    # Use a fully isolated temp directory so concurrent conversions are safe.
    work_dir = tempfile.mkdtemp(prefix="lo_conv_")
    try:
        lo_home = os.path.join(work_dir, "home")
        out_dir = os.path.join(work_dir, "out")
        in_path = os.path.join(work_dir, "input.xlsx")
        os.makedirs(lo_home, exist_ok=True)
        os.makedirs(out_dir,  exist_ok=True)

        with open(in_path, "wb") as f:
            f.write(xlsx_bytes)

        cmd = [
            _SOFFICE,
            "--headless",
            "--norestore",
            "--nofirststartwizard",
            f"-env:UserInstallation=file://{lo_home}",
            "--convert-to", "pdf",
            "--outdir", out_dir,
            in_path,
        ]

        logger.debug("Running LibreOffice: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"LibreOffice conversion failed (rc={result.returncode}): {stderr}")

        pdf_path = Path(out_dir) / "input.pdf"
        if not pdf_path.exists():
            candidates = list(Path(out_dir).glob("*.pdf"))
            if not candidates:
                raise RuntimeError("LibreOffice ran but produced no PDF output.")
            pdf_path = candidates[0]

        return pdf_path.read_bytes()

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
