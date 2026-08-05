"""
excel_diff.py — Git-like diff tool for Excel (.xlsx) files.
Compares cell content AND diagram/shape text, ignoring positional attributes.

PARSER FALLBACK CHAINS
  Cells:   openpyxl → pandas → raw XML (namespace-aware) → raw XML (wildcard scan)
  Shapes:  auto-detect XDR/DML namespace → wildcard namespace scan → vml fallback

SEMANTIC ROW DIFFING (Control-Plan aware)
  Triggered automatically per-sheet when the cell count differs between versions.
  Rows are grouped by their "Part/Process No." anchor (col A).
  Within each group, sub-operations are keyed by col G ("Process Name/Operation
  Description"). Continuation rows (A="/" or None, G="/" or None) are matched
  positionally within their parent sub-operation so that:
    • A new continuation row inserted anywhere is reported as [NEW ROW ADDED]
    • A deleted continuation row is reported as [ROW DELETED]
    • Re-ordered continuation rows inside the same sub-op are still compared correctly

  "New sub-operation added" (a row where G has a real value that doesn't exist in
  the other version) is also detected and reported cleanly.

SHEET MATCHING STRATEGY
  1. Match by sheet name (exact).
  2. If names differ but unmatched counts are equal on both sides, match by position
     (sheet 0 ↔ sheet 0, sheet 1 ↔ sheet 1, …).
  3. Sheets that cannot be paired are reported as fully added/deleted.

Usage:
    python excel_diff.py old.xlsx new.xlsx
    python excel_diff.py old.xlsx new.xlsx --format json
    python excel_diff.py old.xlsx new.xlsx --sheet "Sheet1"
    python excel_diff.py old.xlsx new.xlsx --debug
"""

import argparse
import json
import sys
import warnings
import zipfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Known namespace variants (standard + all known alternates)
# ---------------------------------------------------------------------------
SP_VARIANTS = [
    "http://schemas.openxmlformats.org/spreadsheetml/2006/main",   # Excel / modern
    "http://purl.oclc.org/ooxml/spreadsheetml/main",               # WPS / old LibreOffice
]
REL_VARIANTS = [
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "http://purl.oclc.org/ooxml/officeDocument/relationships",
]
XDR_VARIANTS = [
    "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "http://purl.oclc.org/ooxml/drawingml/spreadsheetDrawing",
]
DML_VARIANTS = [
    "http://schemas.openxmlformats.org/drawingml/2006/main",
    "http://purl.oclc.org/ooxml/drawingml/main",
]


# ---------------------------------------------------------------------------
# Namespace detection helpers
# ---------------------------------------------------------------------------

def _root_ns(tag: str) -> str:
    """Extract namespace URI from a Clark-notation tag like {uri}localname."""
    if tag.startswith('{'):
        return tag[1:].split('}')[0]
    return ""


def _detect_sp_ns(xlsx_path: str) -> str:
    """Detect spreadsheet namespace by inspecting sharedStrings or workbook."""
    with zipfile.ZipFile(xlsx_path) as zf:
        names = set(zf.namelist())
        for candidate in ["xl/sharedStrings.xml", "xl/workbook.xml"]:
            if candidate in names:
                try:
                    with zf.open(candidate) as f:
                        root = ET.parse(f).getroot()
                    ns = _root_ns(root.tag)
                    if ns:
                        return ns
                except Exception:
                    continue
    return SP_VARIANTS[0]


def _detect_rel_ns(xlsx_path: str) -> str:
    """Detect relationship namespace by inspecting workbook rels."""
    with zipfile.ZipFile(xlsx_path) as zf:
        names = set(zf.namelist())
        if "xl/_rels/workbook.xml.rels" in names:
            try:
                with zf.open("xl/_rels/workbook.xml.rels") as f:
                    root = ET.parse(f).getroot()
                for rel in root:
                    t = rel.get("Type", "")
                    for v in REL_VARIANTS:
                        if v.split("//")[1].split("/")[0] in t:
                            return v
            except Exception:
                pass
    return REL_VARIANTS[0]


def _detect_drawing_ns(drawing_path: str, zf: zipfile.ZipFile) -> tuple:
    """
    Detect XDR (spreadsheet drawing) and DML (drawing main) namespaces
    from the drawing XML root element and its descendants.
    Falls back to wildcard scan if known variants aren't found.
    """
    try:
        with zf.open(drawing_path) as f:
            root = ET.parse(f).getroot()
    except Exception:
        return XDR_VARIANTS[0], DML_VARIANTS[0]

    xdr_ns = _root_ns(root.tag) or XDR_VARIANTS[0]

    dml_ns = None
    for el in root.iter():
        ns = _root_ns(el.tag)
        if ns and ns != xdr_ns and ("drawingml" in ns or "ooxml/drawingml" in ns):
            if "spreadsheet" not in ns:
                dml_ns = ns
                break

    if not dml_ns:
        for v in DML_VARIANTS:
            if any(_root_ns(el.tag) == v for el in root.iter()):
                dml_ns = v
                break

    return xdr_ns, (dml_ns or DML_VARIANTS[0])


def _wildcard_ns_scan(root: ET.Element, local_name: str) -> list:
    """
    Find all elements matching a local tag name regardless of namespace.
    Last-resort fallback when namespace detection fails entirely.
    """
    return [el for el in root.iter() if el.tag.split('}')[-1] == local_name]


def _attr_any(el: ET.Element, local_name: str) -> Optional[str]:
    """Get an attribute value by local name, ignoring its namespace prefix."""
    for k, v in el.attrib.items():
        if k.split('}')[-1] == local_name:
            return v
    return None


# ---------------------------------------------------------------------------
# CELL READER — 4-level fallback chain
# ---------------------------------------------------------------------------

def _cells_via_openpyxl(xlsx_path: str) -> dict:
    """Level 1: openpyxl (fastest, handles most modern Excel files)."""
    import openpyxl
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    result = {}
    for sheet_name in wb.sheetnames:
        cells = {}
        for row in wb[sheet_name].iter_rows():
            for cell in row:
                if cell.value is not None:
                    val = str(cell.value).strip()
                    if val:
                        cells[cell.coordinate] = val
        result[sheet_name] = cells
    return result


def _cells_via_pandas(xlsx_path: str) -> dict:
    """Level 2: pandas (handles more edge cases, uses xlrd/openpyxl under the hood)."""
    import pandas as pd
    result = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        all_sheets = pd.read_excel(xlsx_path, sheet_name=None, header=None, dtype=str)
    for sheet_name, df in all_sheets.items():
        cells = {}
        for row_idx, row in df.iterrows():
            for col_idx, val in row.items():
                if val is not None and str(val).strip() not in ("", "nan", "None"):
                    col_letter = _col_letter(col_idx)
                    coord = f"{col_letter}{row_idx + 1}"
                    cells[coord] = str(val).strip()
        result[sheet_name] = cells
    return result


def _col_letter(n: int) -> str:
    """Convert 0-based column index to Excel column letter (0→A, 25→Z, 26→AA)."""
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _cells_via_raw_xml(xlsx_path: str) -> dict:
    """Level 3: Direct XML parsing with auto-detected namespace."""
    SP  = _detect_sp_ns(xlsx_path)
    rel_ns = _detect_rel_ns(xlsx_path)

    result = {}
    with zipfile.ZipFile(xlsx_path) as zf:
        names = set(zf.namelist())

        shared_strings = []
        if "xl/sharedStrings.xml" in names:
            with zf.open("xl/sharedStrings.xml") as f:
                ss_root = ET.parse(f).getroot()
            for si in ss_root.iter(f"{{{SP}}}si"):
                parts = [t.text or "" for t in si.iter(f"{{{SP}}}t")]
                shared_strings.append("".join(parts))

        sheet_name_map: dict = {}
        if "xl/workbook.xml" in names and "xl/_rels/workbook.xml.rels" in names:
            with zf.open("xl/workbook.xml") as f:
                wb_root = ET.parse(f).getroot()
            with zf.open("xl/_rels/workbook.xml.rels") as f:
                rels_root = ET.parse(f).getroot()
            rel_map = {r.get("Id"): r.get("Target", "") for r in rels_root}
            for sheet_el in wb_root.iter(f"{{{SP}}}sheet"):
                r_id = sheet_el.get(f"{{{rel_ns}}}id")
                sname = sheet_el.get("name", "")
                target = rel_map.get(r_id, "")
                if target:
                    sheet_name_map["xl/" + target.lstrip("../")] = sname

        for sheet_path, sheet_name in sheet_name_map.items():
            if sheet_path not in names:
                continue
            with zf.open(sheet_path) as f:
                ws_root = ET.parse(f).getroot()
            cells = {}
            for c in ws_root.iter(f"{{{SP}}}c"):
                coord = c.get("r", "")
                c_type = c.get("t", "")
                v_el = c.find(f"{{{SP}}}v")
                is_el = c.find(f"{{{SP}}}is")
                value = _parse_cell_value(c_type, v_el, is_el, shared_strings, SP)
                if value:
                    cells[coord] = value
            result[sheet_name] = cells

    return result


def _cells_via_wildcard_xml(xlsx_path: str) -> dict:
    """
    Level 4: Wildcard XML scan — ignores all namespaces entirely.
    Last resort for completely non-standard files.
    """
    result = {}
    with zipfile.ZipFile(xlsx_path) as zf:
        names = set(zf.namelist())

        shared_strings = []
        if "xl/sharedStrings.xml" in names:
            with zf.open("xl/sharedStrings.xml") as f:
                ss_root = ET.parse(f).getroot()
            for si in _wildcard_ns_scan(ss_root, "si"):
                parts = [t.text or "" for t in _wildcard_ns_scan(si, "t")]
                shared_strings.append("".join(parts))

        sheet_files = []
        if "xl/workbook.xml" in names and "xl/_rels/workbook.xml.rels" in names:
            with zf.open("xl/workbook.xml") as f:
                wb_root = ET.parse(f).getroot()
            with zf.open("xl/_rels/workbook.xml.rels") as f:
                rels_root = ET.parse(f).getroot()
            rel_map = {_attr_any(r, "Id"): _attr_any(r, "Target") for r in rels_root}
            for sheet_el in _wildcard_ns_scan(wb_root, "sheet"):
                r_id = _attr_any(sheet_el, "id")
                sname = _attr_any(sheet_el, "name") or "Sheet"
                target = rel_map.get(r_id, "")
                if target:
                    path = "xl/" + target.lstrip("../")
                    sheet_files.append((path, sname))
        if not sheet_files:
            for name in sorted(names):
                if name.startswith("xl/worksheets/sheet") and "_rels" not in name:
                    sheet_files.append((name, Path(name).stem))

        for sheet_path, sheet_name in sheet_files:
            if sheet_path not in names:
                continue
            with zf.open(sheet_path) as f:
                ws_root = ET.parse(f).getroot()
            cells = {}
            for c in _wildcard_ns_scan(ws_root, "c"):
                coord = _attr_any(c, "r") or ""
                c_type = _attr_any(c, "t") or ""
                v_el_list = _wildcard_ns_scan(c, "v")
                is_el_list = _wildcard_ns_scan(c, "is")
                v_el = v_el_list[0] if v_el_list else None
                is_el = is_el_list[0] if is_el_list else None
                value = _parse_cell_value(c_type, v_el, is_el, shared_strings, None)
                if value and coord:
                    cells[coord] = value
            result[sheet_name] = cells

    return result


def _parse_cell_value(c_type, v_el, is_el, shared_strings, SP) -> Optional[str]:
    """Parse a cell's value element given its type, shared strings table, and namespace."""
    value = None
    if c_type == "s" and v_el is not None:
        try:
            idx = int(v_el.text)
            value = shared_strings[idx] if idx < len(shared_strings) else ""
        except (ValueError, TypeError, IndexError):
            pass
    elif c_type == "inlineStr" and is_el is not None:
        if SP:
            parts = [t.text or "" for t in is_el.iter(f"{{{SP}}}t")]
        else:
            parts = [t.text or "" for t in _wildcard_ns_scan(is_el, "t")]
        value = "".join(parts)
    elif v_el is not None and v_el.text:
        value = v_el.text

    if value is not None:
        val = str(value).strip()
        return val if val else None
    return None


def _is_empty(data: dict) -> bool:
    return not data or all(len(c) == 0 for c in data.values())


def read_cells(xlsx_path: str, debug: bool = False) -> dict:
    """
    Try each cell reader in order, returning the first non-empty result.

    Chain:
      1. openpyxl          — fast, handles standard Excel files
      2. pandas            — broader compatibility, different internals
      3. raw XML           — namespace-aware direct parse (handles WPS/LibreOffice)
      4. wildcard XML      — ignores all namespaces, last resort
    """
    chain = [
        ("openpyxl",      _cells_via_openpyxl),
        ("pandas",        _cells_via_pandas),
        ("raw XML",       _cells_via_raw_xml),
        ("wildcard XML",  _cells_via_wildcard_xml),
    ]
    for name, fn in chain:
        try:
            result = fn(xlsx_path)
            if not _is_empty(result):
                if debug:
                    total = sum(len(c) for c in result.values())
                    print(f"  [cell parser] {name} → {total} cells", file=sys.stderr)
                return result
        except Exception as e:
            if debug:
                print(f"  [cell parser] {name} failed: {e}", file=sys.stderr)
            continue

    if debug:
        print("  [cell parser] all parsers failed, returning empty", file=sys.stderr)
    return {}


# ---------------------------------------------------------------------------
# SHAPE READER — 3-level fallback chain
# ---------------------------------------------------------------------------

def _shapes_via_drawing_xml(xlsx_path: str, debug: bool = False) -> dict:
    """
    Level 1 & 2 combined: auto-detect XDR/DML namespaces, then fall back
    to wildcard scan within the same drawing XML pass.
    Returns { sheet_name: { shape_name: text } }
    """
    SP     = _detect_sp_ns(xlsx_path)
    rel_ns = _detect_rel_ns(xlsx_path)
    result: dict = {}

    with zipfile.ZipFile(xlsx_path) as zf:
        names = set(zf.namelist())

        drawing_map: dict = {}
        for name in names:
            if name.startswith("xl/worksheets/_rels/") and name.endswith(".xml.rels"):
                try:
                    with zf.open(name) as f:
                        tree = ET.parse(f)
                    for rel in tree.getroot():
                        rtype = rel.get("Type", "").lower()
                        if "drawing" in rtype:
                            sheet_xml = name.replace("_rels/", "").replace(".rels", "")
                            target = rel.get("Target", "")
                            drawing_map[sheet_xml] = "xl/" + target.lstrip("../")
                except Exception:
                    continue

        sheet_name_map: dict = {}
        if "xl/workbook.xml" in names and "xl/_rels/workbook.xml.rels" in names:
            try:
                with zf.open("xl/workbook.xml") as f:
                    wb_root = ET.parse(f).getroot()
                with zf.open("xl/_rels/workbook.xml.rels") as f:
                    rels_root = ET.parse(f).getroot()
                rel_map = {r.get("Id"): r.get("Target", "") for r in rels_root}
                for sheet_el in wb_root.iter(f"{{{SP}}}sheet"):
                    r_id = sheet_el.get(f"{{{rel_ns}}}id")
                    sname = sheet_el.get("name", "")
                    target = rel_map.get(r_id, "")
                    if target:
                        sheet_name_map["xl/" + target.lstrip("../")] = sname
            except Exception:
                pass

        for sheet_xml_path, drawing_path in drawing_map.items():
            sheet_name = sheet_name_map.get(sheet_xml_path, sheet_xml_path)
            if drawing_path not in names:
                continue

            try:
                XDR, DML = _detect_drawing_ns(drawing_path, zf)
                with zf.open(drawing_path) as f:
                    drawing_root = ET.parse(f).getroot()
            except Exception:
                continue

            shapes: dict = {}

            for anchor in drawing_root:
                for sp in anchor.iter(f"{{{XDR}}}sp"):
                    sp_name = _get_shape_name_ns(sp, XDR)
                    texts = [t.text for t in sp.iter(f"{{{DML}}}t") if t.text]
                    shapes[sp_name] = "".join(texts).strip()

            if not shapes:
                if debug:
                    print(f"  [shape parser] ns scan found nothing in {drawing_path}, trying wildcard", file=sys.stderr)
                for sp in _wildcard_ns_scan(drawing_root, "sp"):
                    sp_name = _get_shape_name_wildcard(sp)
                    texts = [t.text for t in _wildcard_ns_scan(sp, "t") if t.text]
                    shapes[sp_name] = "".join(texts).strip()

            if shapes:
                result[sheet_name] = shapes

    return result


def _shapes_via_vml(xlsx_path: str, debug: bool = False) -> dict:
    """
    Level 3: VML fallback — older Excel files store shapes in vmlDrawing*.vml
    instead of drawing*.xml. Parses <v:textbox> and <v:shape> elements.
    """
    result: dict = {}

    with zipfile.ZipFile(xlsx_path) as zf:
        names = set(zf.namelist())
        vml_files = [n for n in names if n.startswith("xl/drawings/vmlDrawing") and n.endswith(".vml")]

        for vml_path in vml_files:
            try:
                with zf.open(vml_path) as f:
                    content = f.read().decode("utf-8", errors="replace")
                try:
                    root = ET.fromstring(content)
                except ET.ParseError:
                    root = ET.fromstring(f"<root>{content}</root>")

                shapes: dict = {}
                for shape in _wildcard_ns_scan(root, "shape"):
                    sp_id = _attr_any(shape, "id") or _attr_any(shape, "spid") or "unknown"
                    text_parts = []
                    for tb in _wildcard_ns_scan(shape, "textbox"):
                        for t in tb.iter():
                            if t.text and t.text.strip():
                                text_parts.append(t.text.strip())
                    if text_parts:
                        shapes[sp_id] = " ".join(text_parts)

                sheet_name = Path(vml_path).stem
                if shapes:
                    result[sheet_name] = shapes
            except Exception as e:
                if debug:
                    print(f"  [shape parser] VML parse failed for {vml_path}: {e}", file=sys.stderr)
                continue

    return result


def _get_shape_name_ns(sp: ET.Element, XDR: str) -> str:
    """Extract shape name using known namespace."""
    nv_sp = sp.find(f".//{{{XDR}}}nvSpPr")
    if nv_sp is not None:
        c_nv = nv_sp.find(f"{{{XDR}}}cNvPr")
        if c_nv is not None:
            return c_nv.get("name") or c_nv.get("id") or "unknown"
    return "unknown"


def _get_shape_name_wildcard(sp: ET.Element) -> str:
    """Extract shape name using wildcard scan."""
    for nv in _wildcard_ns_scan(sp, "nvSpPr"):
        for cnv in _wildcard_ns_scan(nv, "cNvPr"):
            name = _attr_any(cnv, "name") or _attr_any(cnv, "id")
            if name:
                return name
    return _attr_any(sp, "id") or "unknown"


def read_shapes(xlsx_path: str, debug: bool = False) -> dict:
    """
    Try each shape reader in order, returning the first non-empty result.

    Chain:
      1. drawing XML with namespace detection + internal wildcard fallback
      2. VML drawing fallback (older xlsx / xls-converted files)
    """
    chain = [
        ("drawing XML",  lambda p: _shapes_via_drawing_xml(p, debug)),
        ("VML",          lambda p: _shapes_via_vml(p, debug)),
    ]
    for name, fn in chain:
        try:
            result = fn(xlsx_path)
            if not _is_empty(result):
                if debug:
                    total = sum(len(s) for s in result.values())
                    print(f"  [shape parser] {name} → {total} shapes", file=sys.stderr)
                return result
        except Exception as e:
            if debug:
                print(f"  [shape parser] {name} failed: {e}", file=sys.stderr)
            continue

    if debug:
        print("  [shape parser] all parsers failed, returning empty", file=sys.stderr)
    return {}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CellDiff:
    sheet: str
    cell: str               # old coordinate (or new coordinate if added)
    old_value: object
    new_value: object
    change_type: str        # "modified" | "added" | "deleted"
    new_coord: str = ""     # populated for "modified" when old/new row numbers differ


@dataclass
class ShapeDiff:
    sheet: str
    shape_name: str
    old_text: Optional[str]
    new_text: Optional[str]
    change_type: str        # "modified" | "added" | "deleted"


@dataclass
class RowDiff:
    sheet: str
    change_type: str        # "added" | "deleted"
    old_row: Optional[int]
    new_row: Optional[int]
    data: dict              # {col_int: value_str}


@dataclass
class DiffResult:
    cell_changes:  list = field(default_factory=list)
    row_changes:   list = field(default_factory=list)
    shape_changes: list = field(default_factory=list)

    @property
    def has_changes(self):
        return bool(self.cell_changes or self.row_changes or self.shape_changes)

    def summary(self):
        return {
            "cell_changes":  len(self.cell_changes),
            "row_changes":   len(self.row_changes),
            "shape_changes": len(self.shape_changes),
            "total": len(self.cell_changes) + len(self.row_changes) + len(self.shape_changes),
        }


# ---------------------------------------------------------------------------
# SHEET MATCHING — name-first, index-fallback
# ---------------------------------------------------------------------------

def match_sheets(old_sheet_names: list, new_sheet_names: list, debug: bool = False) -> list:
    """
    Produce a list of (old_name_or_None, new_name_or_None) sheet pairs.

    Strategy
    --------
    1. Exact name match: pair sheets that share the same name.
    2. If there are unmatched sheets left on both sides AND both sides have the
       same count of unmatched sheets, pair them by position (index fallback).
    3. Any remaining unmatched sheet is reported as purely added (old=None)
       or deleted (new=None).
    """
    pairs = []
    matched_old, matched_new = set(), set()

    for o in old_sheet_names:
        if o in new_sheet_names:
            pairs.append((o, o))
            matched_old.add(o)
            matched_new.add(o)

    unmatched_old = [s for s in old_sheet_names if s not in matched_old]
    unmatched_new = [s for s in new_sheet_names if s not in matched_new]

    if unmatched_old and unmatched_new and len(unmatched_old) == len(unmatched_new):
        if debug:
            print(f"  [sheet match] name mismatch, falling back to index pairing: "
                  f"{unmatched_old} ↔ {unmatched_new}", file=sys.stderr)
        for o, n in zip(unmatched_old, unmatched_new):
            pairs.append((o, n))
        unmatched_old, unmatched_new = [], []

    for o in unmatched_old:
        pairs.append((o, None))
    for n in unmatched_new:
        pairs.append((None, n))

    if debug:
        for o, n in pairs:
            print(f"  [sheet match] '{o}' ↔ '{n}'", file=sys.stderr)

    return pairs


# ---------------------------------------------------------------------------
# SEMANTIC ROW DIFFING — group-aware, sub-operation keyed
# ---------------------------------------------------------------------------

COL_GROUP_ID = 1   # A — Part/Process No.  (marks start of a logical group)
COL_SUBOP_ID = 7   # G — Process Name/Operation Description (sub-operation key)

_PLACEHOLDER_VALUES = {'/', ''}


def _is_placeholder(val) -> bool:
    if val is None:
        return True
    return str(val).strip() in _PLACEHOLDER_VALUES


def _row_key(val) -> Optional[str]:
    if _is_placeholder(val):
        return None
    return str(val).strip()


def _coord(col: int, row: int) -> str:
    """Convert 1-based (col, row) to Excel coordinate string like 'A1'."""
    return f"{_col_letter(col - 1)}{row}"


def extract_sheet_rows(ws) -> list:
    """Read every row of a worksheet into a list of {row, data} dicts."""
    rows = []
    for r in range(1, ws.max_row + 1):
        data = {}
        for cell in ws[r]:
            if cell.value is not None:
                v = str(cell.value).strip()
                if v:
                    data[cell.column] = v
        rows.append({'row': r, 'data': data})
    return rows


def _split_into_groups(sheet_rows: list) -> list:
    """
    Partition sheet rows into logical groups based on COL_GROUP_ID (col A).
    A group starts when col A has a real (non-placeholder) value.
    Rows before the first group are placed in a group with group_id=None.
    """
    groups = []
    current = {'group_id': None, 'start_row': 1, 'rows': []}
    groups.append(current)

    for item in sheet_rows:
        a_val = item['data'].get(COL_GROUP_ID)
        key = _row_key(a_val)
        if key is not None:
            current = {'group_id': key, 'start_row': item['row'], 'rows': [item]}
            groups.append(current)
        else:
            current['rows'].append(item)

    return groups


def _split_group_into_subops(group_rows: list) -> list:
    """
    Within a group's rows, split into sub-operations keyed by COL_SUBOP_ID (col G).
    Continuation rows (G = "/" or None) belong to the most recent sub-operation.
    """
    subops = []
    current = None

    for item in group_rows:
        g_val = item['data'].get(COL_SUBOP_ID)
        key = _row_key(g_val)
        if key is not None:
            current = {'subop_key': key, 'header_row': item, 'continuation': []}
            subops.append(current)
        else:
            if current is None:
                current = {'subop_key': None, 'header_row': None, 'continuation': [item]}
                subops.append(current)
            else:
                current['continuation'].append(item)

    return subops


def _diff_row_data(old_data: dict, new_data: dict,
                   old_row: int, new_row: int,
                   sheet: str, changes: list):
    """
    Compare two row data dicts cell by cell and append CellDiff entries.
    Skips COL_GROUP_ID and COL_SUBOP_ID (structural identity columns).
    """
    all_cols = set(old_data) | set(new_data)
    all_cols -= {COL_GROUP_ID, COL_SUBOP_ID}

    for col in sorted(all_cols):
        ov = old_data.get(col)
        nv = new_data.get(col)
        if ov == nv:
            continue
        old_c = _coord(col, old_row)
        new_c = _coord(col, new_row)
        if ov is None:
            changes.append(CellDiff(sheet, new_c, None, nv, "added"))
        elif nv is None:
            changes.append(CellDiff(sheet, old_c, ov, None, "deleted"))
        else:
            changes.append(CellDiff(sheet, old_c, ov, nv, "modified",
                                    new_coord=new_c))


def _diff_continuation_rows(old_cont: list, new_cont: list,
                             sheet: str, changes: list):
    """
    Compare continuation rows of a matched sub-operation pair using a greedy
    forward-scan with dynamic offset to detect insertions and deletions.
    """
    offset = 0

    for i, old_item in enumerate(old_cont):
        j = i + offset
        if j >= len(new_cont):
            changes.append(RowDiff(sheet, "deleted", old_item['row'], None, old_item['data']))
            continue

        new_item = new_cont[j]

        if old_item['data'] == new_item['data']:
            continue

        if j + 1 < len(new_cont) and new_cont[j + 1]['data'] == old_item['data']:
            changes.append(RowDiff(sheet, "added", None, new_cont[j]['row'], new_cont[j]['data']))
            offset += 1
        else:
            _diff_row_data(
                old_item['data'], new_item['data'],
                old_item['row'], new_item['row'],
                sheet, changes,
            )

    for extra in new_cont[len(old_cont) + offset:]:
        changes.append(RowDiff(sheet, "added", None, extra['row'], extra['data']))


def _diff_plain_rows(old_rows: list, new_rows: list, sheet: str, changes: list):
    """
    Simple positional diff for rows with no group/sub-op structure (e.g. header rows).
    """
    offset = 0
    for i, old_item in enumerate(old_rows):
        j = i + offset
        if j >= len(new_rows):
            changes.append(RowDiff(sheet, "deleted", old_item['row'], None, old_item['data']))
            continue
        new_item = new_rows[j]
        if old_item['data'] == new_item['data']:
            continue
        if j + 1 < len(new_rows) and new_rows[j + 1]['data'] == old_item['data']:
            changes.append(RowDiff(sheet, "added", None, new_rows[j]['row'], new_rows[j]['data']))
            offset += 1
        else:
            _diff_row_data(old_item['data'], new_item['data'],
                           old_item['row'], new_item['row'], sheet, changes)

    for extra in new_rows[len(old_rows) + offset:]:
        changes.append(RowDiff(sheet, "added", None, extra['row'], extra['data']))


def _stable_union(a: list, b: list) -> list:
    """Union of two lists preserving order: items from a first, then new items from b."""
    seen = set(a)
    return list(a) + [x for x in b if x not in seen]


def semantic_diff_sheet(old_ws, new_ws, sheet: str) -> list:
    """
    Perform a full semantic diff of two worksheet objects.
    Returns a flat list of CellDiff / RowDiff objects.
    """
    changes = []

    old_rows = extract_sheet_rows(old_ws)
    new_rows = extract_sheet_rows(new_ws)

    old_groups = _split_into_groups(old_rows)
    new_groups = _split_into_groups(new_rows)

    old_group_map = {g['group_id']: g for g in old_groups if g['group_id'] is not None}
    new_group_map = {g['group_id']: g for g in new_groups if g['group_id'] is not None}

    old_header_group = next((g for g in old_groups if g['group_id'] is None), None)
    new_header_group = next((g for g in new_groups if g['group_id'] is None), None)

    if old_header_group and new_header_group:
        _diff_plain_rows(old_header_group['rows'], new_header_group['rows'], sheet, changes)

    all_group_ids = _stable_union(
        [g['group_id'] for g in old_groups if g['group_id']],
        [g['group_id'] for g in new_groups if g['group_id']],
    )

    for gid in all_group_ids:
        og = old_group_map.get(gid)
        ng = new_group_map.get(gid)

        if og is None:
            for item in ng['rows']:
                changes.append(RowDiff(sheet, "added", None, item['row'], item['data']))
            continue

        if ng is None:
            for item in og['rows']:
                changes.append(RowDiff(sheet, "deleted", item['row'], None, item['data']))
            continue

        old_subops = _split_group_into_subops(og['rows'])
        new_subops = _split_group_into_subops(ng['rows'])

        old_subop_map = {s['subop_key']: s for s in old_subops if s['subop_key'] is not None}
        new_subop_map = {s['subop_key']: s for s in new_subops if s['subop_key'] is not None}

        all_subop_keys = _stable_union(
            [s['subop_key'] for s in old_subops if s['subop_key']],
            [s['subop_key'] for s in new_subops if s['subop_key']],
        )

        for sk in all_subop_keys:
            osp = old_subop_map.get(sk)
            nsp = new_subop_map.get(sk)

            if osp is None:
                if nsp['header_row']:
                    changes.append(RowDiff(sheet, "added", None,
                                           nsp['header_row']['row'], nsp['header_row']['data']))
                for item in nsp['continuation']:
                    changes.append(RowDiff(sheet, "added", None, item['row'], item['data']))
                continue

            if nsp is None:
                if osp['header_row']:
                    changes.append(RowDiff(sheet, "deleted",
                                           osp['header_row']['row'], None, osp['header_row']['data']))
                for item in osp['continuation']:
                    changes.append(RowDiff(sheet, "deleted", item['row'], None, item['data']))
                continue

            if osp['header_row'] and nsp['header_row']:
                _diff_row_data(
                    osp['header_row']['data'], nsp['header_row']['data'],
                    osp['header_row']['row'], nsp['header_row']['row'],
                    sheet, changes,
                )

            _diff_continuation_rows(osp['continuation'], nsp['continuation'], sheet, changes)

    return changes


# ---------------------------------------------------------------------------
# Diff logic
# ---------------------------------------------------------------------------

def compare_cells(old_data: dict, new_data: dict, sheet_pairs: list) -> list:
    """
    Flat cell-level diff for a list of (old_name, new_name) sheet pairs.
    Handles fully-added (old=None) and fully-deleted (new=None) sheets.
    """
    diffs = []
    for old_name, new_name in sheet_pairs:
        if old_name is None or new_name is None:
            if old_name is None:
                for coord, val in sorted((new_data.get(new_name) or {}).items()):
                    diffs.append(CellDiff(new_name, coord, None, val, "added"))
            else:
                for coord, val in sorted((old_data.get(old_name) or {}).items()):
                    diffs.append(CellDiff(old_name, coord, val, None, "deleted"))
            continue

        old_cells = old_data.get(old_name, {})
        new_cells = new_data.get(new_name, {})
        label = new_name
        for coord in sorted(set(old_cells) | set(new_cells)):
            ov, nv = old_cells.get(coord), new_cells.get(coord)
            if ov == nv:
                continue
            if ov is None:
                diffs.append(CellDiff(label, coord, None, nv, "added"))
            elif nv is None:
                diffs.append(CellDiff(label, coord, ov, None, "deleted"))
            else:
                diffs.append(CellDiff(label, coord, ov, nv, "modified"))
    return diffs


def compare_shapes(old_shapes: dict, new_shapes: dict, sheet_pairs: list) -> list:
    """Shape-level diff for a list of (old_name, new_name) sheet pairs."""
    diffs = []
    for old_name, new_name in sheet_pairs:
        old_by_name = old_shapes.get(old_name or "", {})
        new_by_name = new_shapes.get(new_name or "", {})
        label = new_name or old_name
        for name in sorted(set(old_by_name) | set(new_by_name)):
            ot = old_by_name.get(name)
            nt = new_by_name.get(name)
            if ot == nt:
                continue
            if ot is None:
                diffs.append(ShapeDiff(label, name, None, nt, "added"))
            elif nt is None:
                diffs.append(ShapeDiff(label, name, ot, None, "deleted"))
            else:
                diffs.append(ShapeDiff(label, name, ot, nt, "modified"))
    return diffs


def diff(old_path: str, new_path: str, sheet_filter=None, debug: bool = False) -> DiffResult:
    """
    Main entry point. Compares two Excel files and returns a DiffResult.

    Per-sheet strategy
    ------------------
    1. Match sheets using match_sheets() (name-first, index-fallback).
    2. For each matched pair, compare the total cell count:
       - If counts DIFFER → run semantic diff (group/sub-op aware, detects
         inserted and deleted rows).
       - If counts MATCH  → run flat cell-level diff (faster, no row tracking
         needed since no rows were added or removed).
    3. Fully added/deleted sheets always use flat diff.
    """
    if debug:
        print(f"\n[debug] Reading cells from {old_path}", file=sys.stderr)
    old_cells = read_cells(old_path, debug)
    if debug:
        print(f"[debug] Reading cells from {new_path}", file=sys.stderr)
    new_cells = read_cells(new_path, debug)

    if debug:
        print(f"[debug] Reading shapes from {old_path}", file=sys.stderr)
    old_shapes = read_shapes(old_path, debug)
    if debug:
        print(f"[debug] Reading shapes from {new_path}", file=sys.stderr)
    new_shapes = read_shapes(new_path, debug)

    old_names = list(old_cells.keys())
    new_names = list(new_cells.keys())
    sheet_pairs = match_sheets(old_names, new_names, debug)

    if sheet_filter:
        sheet_pairs = [(o, n) for o, n in sheet_pairs
                       if sheet_filter in (o or "", n or "")]

    # Determine if any paired sheet needs semantic diff (cell count mismatch)
    needs_semantic = any(
        o is not None and n is not None
        and len(old_cells.get(o, {})) != len(new_cells.get(n, {}))
        for o, n in sheet_pairs
    )

    # Load openpyxl workbooks once if any sheet needs semantic diff
    if needs_semantic:
        import openpyxl
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wb_old = openpyxl.load_workbook(old_path, data_only=True)
            wb_new = openpyxl.load_workbook(new_path, data_only=True)
        old_ws_map = {ws.title: ws for ws in wb_old.worksheets}
        new_ws_map = {ws.title: ws for ws in wb_new.worksheets}
    else:
        old_ws_map = new_ws_map = {}

    all_cell_changes: list = []
    all_row_changes:  list = []

    for old_name, new_name in sheet_pairs:
        # Fully added or deleted sheet — always flat diff
        if old_name is None or new_name is None:
            all_cell_changes.extend(
                compare_cells(old_cells, new_cells, [(old_name, new_name)])
            )
            continue

        old_count = len(old_cells.get(old_name, {}))
        new_count = len(new_cells.get(new_name, {}))

        if old_count != new_count:
            # Cell count differs → semantic diff
            old_ws = old_ws_map.get(old_name)
            new_ws = new_ws_map.get(new_name)
            if old_ws is not None and new_ws is not None:
                if debug:
                    print(
                        f"  [semantic] '{old_name}': {old_count} → {new_count} cells, "
                        f"running semantic diff",
                        file=sys.stderr,
                    )
                for ch in semantic_diff_sheet(old_ws, new_ws, new_name):
                    if isinstance(ch, RowDiff):
                        all_row_changes.append(ch)
                    else:
                        all_cell_changes.append(ch)
                continue
            # Fallback if worksheet objects unavailable
            if debug:
                print(
                    f"  [semantic] '{old_name}': worksheet not found, falling back to flat diff",
                    file=sys.stderr,
                )

        # Cell counts match (or semantic fallback) → flat diff
        all_cell_changes.extend(
            compare_cells(old_cells, new_cells, [(old_name, new_name)])
        )

    shape_changes = compare_shapes(old_shapes, new_shapes, sheet_pairs)

    return DiffResult(
        cell_changes=all_cell_changes,
        row_changes=all_row_changes,
        shape_changes=shape_changes,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

C = {
    "reset": "\033[0m", "red": "\033[31m", "green": "\033[32m",
    "yellow": "\033[33m", "cyan": "\033[36m", "bold": "\033[1m",
}

def _c(col, text):
    return f"{C[col]}{text}{C['reset']}"


def print_pretty(result: DiffResult, old_path: str, new_path: str):
    print(f"\n{_c('bold', '═'*64)}")
    print(f"  {_c('bold','Excel Diff')}   {_c('cyan', old_path)}  →  {_c('cyan', new_path)}")
    print(f"{_c('bold', '═'*64)}\n")

    if not result.has_changes:
        print(_c("green", "  ✔  No content changes detected."))
        print(_c("bold", "\n" + "═"*64) + "\n")
        return

    if result.cell_changes:
        print(_c("bold", f"  CELL CHANGES  ({len(result.cell_changes)})"))
        print("  " + "─"*60)
        cur = None
        for d in result.cell_changes:
            if d.sheet != cur:
                print(f"\n  {_c('cyan', f'[{d.sheet}]')}")
                cur = d.sheet
            if d.change_type == "added":
                print(f"    {_c('green','+')} {d.cell:<8}  {_c('green', str(d.new_value))}")
            elif d.change_type == "deleted":
                print(f"    {_c('red','-')} {d.cell:<8}  {_c('red', str(d.old_value))}")
            else:
                loc = d.cell + (f" → {d.new_coord}" if d.new_coord and d.new_coord != d.cell else "")
                print(f"    {_c('yellow','~')} {loc:<16}  {_c('red', str(d.old_value))}  →  {_c('green', str(d.new_value))}")

    if result.row_changes:
        print(f"\n  {_c('bold', f'ROW CHANGES  ({len(result.row_changes)})')}")
        print("  " + "─"*60)
        cur = None
        for d in result.row_changes:
            if d.sheet != cur:
                print(f"\n  {_c('cyan', f'[{d.sheet}]')}")
                cur = d.sheet
            row_label = f"row {d.new_row}" if d.change_type == "added" else f"row {d.old_row}"
            symbol = _c('green', '+') if d.change_type == "added" else _c('red', '-')
            action = "NEW ROW ADDED" if d.change_type == "added" else "ROW DELETED"
            print(f"    {symbol} [{action}]  {_c('cyan', row_label)}")
            for col in sorted(d.data):
                coord = _coord(col, d.new_row or d.old_row)
                val = str(d.data[col])[:80]
                colour = 'green' if d.change_type == "added" else 'red'
                print(f"        {coord}: {_c(colour, val)}")

    if result.shape_changes:
        print(f"\n  {_c('bold', f'SHAPE / DIAGRAM CHANGES  ({len(result.shape_changes)})')}")
        print("  " + "─"*60)
        cur = None
        for d in result.shape_changes:
            if d.sheet != cur:
                print(f"\n  {_c('cyan', f'[{d.sheet}]')}")
                cur = d.sheet
            if d.change_type == "added":
                print(f"    {_c('green','+')} {d.shape_name}")
                print(f"        text: {_c('green', repr(d.new_text))}")
            elif d.change_type == "deleted":
                print(f"    {_c('red','-')} {d.shape_name}")
                print(f"        text: {_c('red', repr(d.old_text))}")
            else:
                print(f"    {_c('yellow','~')} {d.shape_name}")
                print(f"        old:  {_c('red',    repr(d.old_text))}")
                print(f"        new:  {_c('green',  repr(d.new_text))}")

    s = result.summary()
    print(f"\n{_c('bold','─'*64)}")
    print(f"  Summary: {s['cell_changes']} cell, {s['row_changes']} row, "
          f"{s['shape_changes']} shape  —  {s['total']} total change(s)")
    print(_c("bold", "═"*64) + "\n")


def print_json(result: DiffResult):
    def _ser(obj):
        if isinstance(obj, (CellDiff, ShapeDiff)):
            return asdict(obj)
        if isinstance(obj, RowDiff):
            row_num = obj.new_row or obj.old_row
            return {
                "sheet":       obj.sheet,
                "change_type": obj.change_type,
                "old_row":     obj.old_row,
                "new_row":     obj.new_row,
                "data":        {_col_letter(c - 1) + str(row_num): v
                                for c, v in obj.data.items()},
            }
        return str(obj)

    print(json.dumps({
        "summary":      result.summary(),
        "cell_changes": [_ser(d) for d in result.cell_changes],
        "row_changes":  [_ser(d) for d in result.row_changes],
        "shape_changes":[_ser(d) for d in result.shape_changes],
    }, indent=2, default=str))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Git-like diff for Excel (.xlsx) files — cells, rows, and diagram text."
    )
    parser.add_argument("old", help="Path to the OLD Excel file")
    parser.add_argument("new", help="Path to the NEW Excel file")
    parser.add_argument("--sheet", default=None, help="Compare only this sheet name")
    parser.add_argument("--format", choices=["pretty", "json"], default="pretty")
    parser.add_argument("--debug", action="store_true",
                        help="Show which parser was used and which sheets use semantic diff")
    args = parser.parse_args()

    for p in [args.old, args.new]:
        if not Path(p).exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            sys.exit(1)

    result = diff(args.old, args.new, sheet_filter=args.sheet, debug=args.debug)

    if args.format == "json":
        print_json(result)
    else:
        print_pretty(result, args.old, args.new)

    sys.exit(0 if not result.has_changes else 1)


if __name__ == "__main__":
    main()
