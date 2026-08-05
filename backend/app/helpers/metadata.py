"""
Robust metadata extractor for control-plan Excel files whose merged-cell
layout varies between versions.

Instead of hard-coding cell addresses (H6, H9, BR5 …) the extractor:

1. Reads every cell in the first sheet via direct ZIP+XML parsing
   (works even when openpyxl chokes on a file).
2. Builds a row→{col→value} map once, then uses *anchor-based lookup*:
   - For each target field, a set of keyword patterns is checked against
     column A of every row.
   - When a matching anchor row is found, the *first non-empty cell to the
     right of column A* in that row is taken as the field value.
3. Falls back through progressively looser strategies before giving up:
     STRATEGY 1 – exact anchor in col A of the same row
     STRATEGY 2 – anchor found in a *nearby* row (±3 rows)
     STRATEGY 3 – raw positional fallback (original hard-coded addresses)
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO
from typing import Optional

try:
    from PIL import Image, ImageEnhance, ImageOps
    import pytesseract
    _TESSERACT_AVAILABLE = True
except Exception:
    _TESSERACT_AVAILABLE = False


# ── Low-level XML helpers ─────────────────────────────────────────────────────

def _parse_shared_strings(data: bytes) -> list[str]:
    root = ET.fromstring(data)
    ns_uri = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""
    ns = {"ns": ns_uri} if ns_uri else {}
    pfx = "ns:" if ns_uri else ""
    strings: list[str] = []
    for si in root.findall(f".//{pfx}si", ns):
        parts: list[str] = []
        for t in si.findall(f".//{pfx}t", ns):
            if t.text:
                parts.append(t.text)
        strings.append("".join(parts))
    return strings


def _col_letter_to_index(col: str) -> int:
    """'A'→1, 'B'→2, 'Z'→26, 'AA'→27, …"""
    n = 0
    for ch in col.upper():
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def _parse_sheet_cells(sheet_xml: bytes, shared_strings: list[str]) -> dict[tuple[int, int], str]:
    """Return {(row, col_index): value} for every non-empty cell."""
    root = ET.fromstring(sheet_xml)
    ns_uri = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""
    ns = {"ns": ns_uri} if ns_uri else {}
    pfx = "ns:" if ns_uri else ""

    cells: dict[tuple[int, int], str] = {}
    cell_ref_re = re.compile(r"^([A-Z]+)(\d+)$")

    for row_el in root.findall(f".//{pfx}row", ns):
        for c in row_el.findall(f"{pfx}c", ns):
            ref = c.get("r", "")
            m = cell_ref_re.match(ref)
            if not m:
                continue
            col_idx = _col_letter_to_index(m.group(1))
            row_idx = int(m.group(2))
            t = c.get("t", "")
            v = c.find(f"{pfx}v", ns)
            if v is None or not v.text:
                continue
            if t == "s":
                try:
                    val: str = shared_strings[int(v.text)]
                except (IndexError, ValueError):
                    val = v.text
            else:
                val = v.text
            if val and val.strip():
                cells[(row_idx, col_idx)] = val
    return cells


# ── Anchor keyword sets ───────────────────────────────────────────────────────

_CONTROL_PLAN_NO_KEYWORDS = [
    "控制计划编号",       # Control Plan No.
    "工艺文件名称",       # Process Document Name (new cover-sheet layout)
    "Process Document Name",
]

_PART_NAME_KEYWORDS = [
    "零件名称",           # Part Name / Description
    "文件编号",           # Document Number (new cover-sheet layout — unique ID)
    "Document Number",
]

_STAGE_ROW_KEYWORDS = [
    "阶段",           # Stage
]

_DATE_COMPILE_KEYWORDS = [
    "日期（编制）",   # Date (Compile)
]


# ── Anchor-based cell finders ─────────────────────────────────────────────────

def _text_contains_any(text: str, keywords: list[str]) -> bool:
    tl = text.lower()
    return any(kw.lower() in tl for kw in keywords)


def _first_data_cell_in_row(
    cells: dict[tuple[int, int], str],
    row: int,
    min_col: int = 2,
    max_col: int = 200,
) -> Optional[str]:
    for col in range(min_col, max_col + 1):
        val = cells.get((row, col))
        if val and val.strip():
            return val.strip()
    return None


def _find_anchor_row(
    cells: dict[tuple[int, int], str],
    keywords: list[str],
    col_a_index: int = 1,
    search_rows: range | None = None,
) -> Optional[int]:
    if search_rows is None:
        search_rows = range(1, 51)
    for row in search_rows:
        cell_text = cells.get((row, col_a_index), "")
        if _text_contains_any(cell_text, keywords):
            return row
    return None


def _find_value_any_column(
    cells: dict[tuple[int, int], str],
    keywords: list[str],
    max_row: int = 30,
    max_col: int = 30,
) -> Optional[str]:
    """Scan every cell (not just col A) for a keyword label.
    When found at (row, col), return the first non-empty cell to its right.
    Handles layouts where labels are not in column A (e.g. col G).
    """
    for row in range(1, max_row + 1):
        for col in range(1, max_col + 1):
            cell_text = cells.get((row, col), "")
            if cell_text and _text_contains_any(cell_text, keywords):
                val = _first_data_cell_in_row(cells, row, min_col=col + 1)
                if val:
                    return val
    return None


def _find_date_in_stage_row(
    cells: dict[tuple[int, int], str],
    stage_row: int,
) -> Optional[str]:
    date_compile_col: Optional[int] = None
    for col in range(2, 200):
        val = cells.get((stage_row, col), "")
        if _text_contains_any(val, _DATE_COMPILE_KEYWORDS):
            date_compile_col = col
            break

    if date_compile_col is None:
        return None

    for col in range(date_compile_col + 1, date_compile_col + 10):
        val = cells.get((stage_row, col))
        if val and val.strip():
            return val.strip()
    return None


# ── Post-processing helpers ───────────────────────────────────────────────────

def normalize_process_code(raw: str) -> str:
    """Strip all whitespace; preserve CJK characters."""
    return re.sub(r"\s+", "", raw)


def h9_to_process_name(raw: str) -> str:
    """Return only the Latin/ASCII portion of the part-name field."""
    latin_only = re.sub(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+", "", raw)
    return latin_only.strip()


def _clean(v: Optional[str]) -> str:
    if not v:
        return ""
    s = v.strip()
    if s.lower() in ("none", "unknown") or s.startswith("="):
        return ""
    return s


# ── Full-text extraction ──────────────────────────────────────────────────────

def _text_nodes_from_xml(xml_bytes: bytes) -> list[str]:
    """Return every <*:t> text node from an arbitrary XML part."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    # Match any element whose local name is "t", regardless of namespace
    return [
        el.text.strip()
        for el in root.iter()
        if el.tag.split("}")[-1] == "t" and el.text and el.text.strip()
    ]


def _preprocess_variants(img: "Image.Image") -> list:
    base_width = 1600
    if img.width < base_width:
        wpercent = base_width / float(img.width)
        hsize = int(float(img.height) * wpercent)
        img = img.resize((base_width, hsize), Image.LANCZOS)
    gray = ImageOps.grayscale(img)
    sharp = ImageEnhance.Sharpness(gray).enhance(3.0)
    contrast = ImageEnhance.Contrast(sharp).enhance(3.0)
    bin1 = contrast.point(lambda x: 0 if x < 180 else 255, '1').convert('L')
    bin2 = contrast.point(lambda x: 0 if x < 128 else 255, '1').convert('L')
    return [bin1, ImageOps.invert(bin1), bin2, gray]


def _ocr_text_from_images(zf: zipfile.ZipFile, names_in_zip: list[str]) -> list[str]:
    """Extract OCR text from images embedded in the Excel ZIP using Tesseract."""
    if not _TESSERACT_AVAILABLE:
        return []

    tokens: list[str] = []
    image_names = sorted(
        n for n in names_in_zip
        if n.startswith("xl/media/") and not n.endswith("/")
    )

    for name in image_names:
        try:
            img_bytes = zf.read(name)
            texts: list[str] = []
            with Image.open(BytesIO(img_bytes)) as img:
                for variant in _preprocess_variants(img):
                    text = pytesseract.image_to_string(variant, config='--psm 6').strip()
                    if text:
                        texts.append(text)
            combined = " ".join(sorted(set(texts), key=lambda x: -len(x)))
            if combined:
                tokens.append(combined)
        except Exception:
            continue

    return tokens


def extract_all_text(data: bytes) -> str:
    """Extract all text from an Excel file for PostgreSQL full-text search.

    Sources:
    - Cell values from all worksheets  (xl/worksheets/sheet*.xml)
    - Shape / text-box text            (xl/drawings/drawing*.xml  →  <a:t>)
    - Cell comments                    (xl/comments*.xml           →  <t>)

    Returns an empty string for non-Excel or unreadable files (CSV/XLS).
    """
    try:
        with zipfile.ZipFile(BytesIO(data), "r") as zf:
            names_in_zip = zf.namelist()

            # ── shared strings (needed for cell decoding) ──────────────────
            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in names_in_zip:
                shared_strings = _parse_shared_strings(zf.read("xl/sharedStrings.xml"))

            tokens: list[str] = []

            # ── 1. cell values ─────────────────────────────────────────────
            for name in sorted(n for n in names_in_zip
                               if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")):
                cells = _parse_sheet_cells(zf.read(name), shared_strings)
                tokens.extend(v.strip() for v in cells.values() if v and v.strip())

            # ── 2. drawing text boxes / shapes ─────────────────────────────
            for name in sorted(n for n in names_in_zip
                               if n.startswith("xl/drawings/drawing") and n.endswith(".xml")):
                tokens.extend(_text_nodes_from_xml(zf.read(name)))

            # ── 3. cell comments ───────────────────────────────────────────
            for name in sorted(n for n in names_in_zip
                               if n.startswith("xl/comments") and n.endswith(".xml")):
                tokens.extend(_text_nodes_from_xml(zf.read(name)))

            # ── 4. OCR on embedded images (optional) ───────────────────────
            tokens.extend(_ocr_text_from_images(zf, names_in_zip))

            return " ".join(tokens)
    except Exception:
        return ""


# ── Main extractor ────────────────────────────────────────────────────────────

def extract_excel_metadata(data: bytes) -> dict:
    """
    Extract process metadata from a control plan Excel file.

    Uses anchor-based lookup so it handles varying merged-cell layouts:
      • Finds "控制计划编号" in col A  → first non-empty cell to the right
        (replaces hard-coded H6)
      • Finds "零件名称／描述" in col A → first non-empty cell to the right
        (replaces hard-coded H9)
      • Finds "阶段" in col A          → scans that row for "日期（编制）"
        label, takes the value cell to its right  (replaces hard-coded BR5)

    Falls back through:
      1. Exact keyword match in col A of the same row
      2. Keyword match within ±3 rows (handles shifted layouts)
      3. Original hard-coded addresses (H6, H9, BR5) as last resort

    Returns:
        {
            "name":          str,  # control_plan_no + "_" + part_name
            "date":          str,  # compile date
            "extractedCode": str,  # part name with whitespace stripped
            "processName":   str,  # part name – CJK characters (Latin only)
        }
    All values are empty strings when not found.
    """

    def _get_cell_by_address(cells: dict[tuple[int, int], str], address: str) -> Optional[str]:
        m = re.match(r"^([A-Z]+)(\d+)$", address.upper())
        if not m:
            return None
        col = _col_letter_to_index(m.group(1))
        row = int(m.group(2))
        return cells.get((row, col))

    def _extract_field(
        cells: dict[tuple[int, int], str],
        keywords: list[str],
        fallback_address: str,
    ) -> str:
        # Strategy 0: scan all columns (handles layouts where label is not in col A)
        val = _find_value_any_column(cells, keywords)
        if val:
            return _clean(val)

        # Strategy 1: exact anchor row in col A
        row = _find_anchor_row(cells, keywords)
        if row is not None:
            val = _first_data_cell_in_row(cells, row)
            if val:
                return _clean(val)

        # Strategy 2: anchor within ±3 rows
        if row is None:
            for candidate_row in range(1, 51):
                cell_text = cells.get((candidate_row, 1), "")
                for kw in keywords:
                    if len(kw) >= 2 and kw[:2] in cell_text:
                        for delta in range(-3, 4):
                            val = _first_data_cell_in_row(cells, candidate_row + delta)
                            if val:
                                return _clean(val)

        # Strategy 3: positional fallback
        val = _get_cell_by_address(cells, fallback_address)
        return _clean(val)

    try:
        with zipfile.ZipFile(BytesIO(data), "r") as zf:
            names_in_zip = zf.namelist()
            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in names_in_zip:
                shared_strings = _parse_shared_strings(zf.read("xl/sharedStrings.xml"))

            sheet_files = sorted(
                n for n in names_in_zip
                if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
            )
            if not sheet_files:
                return {"name": "", "date": "", "extractedCode": "", "processName": ""}

            cells = _parse_sheet_cells(zf.read(sheet_files[0]), shared_strings)

        # Control Plan No. (was H6)
        control_plan_no = _extract_field(cells, _CONTROL_PLAN_NO_KEYWORDS, "H6")

        # Part Name (was H9)
        part_name = _extract_field(cells, _PART_NAME_KEYWORDS, "H9")

        # Date (was BR5)
        date_val = ""
        stage_row = _find_anchor_row(cells, _STAGE_ROW_KEYWORDS)
        if stage_row is not None:
            date_val = _clean(_find_date_in_stage_row(cells, stage_row))
        if not date_val:
            for candidate_row in range(1, 51):
                cell_text = cells.get((candidate_row, 1), "")
                if "阶段" in cell_text:
                    for delta in range(-3, 4):
                        d = _clean(_find_date_in_stage_row(cells, candidate_row + delta))
                        if d:
                            date_val = d
                            break
                    if date_val:
                        break
        if not date_val:
            for addr in ("BR5", "BV5", "CB5"):
                row_num = int(re.search(r"\d+", addr).group())
                col_num = _col_letter_to_index(re.search(r"[A-Z]+", addr).group())
                v = cells.get((row_num, col_num))
                if v and _clean(v):
                    date_val = _clean(v)
                    break

        name = "_".join(p for p in [control_plan_no, part_name] if p)
        extracted_code = normalize_process_code(part_name) if part_name else ""
        process_name = h9_to_process_name(part_name) if part_name else ""

        return {
            "name": name,
            "date": date_val,
            "extractedCode": extracted_code,
            "processName": process_name,
        }

    except Exception:
        import traceback
        traceback.print_exc()
        return {"name": "", "date": "", "extractedCode": "", "processName": ""}
