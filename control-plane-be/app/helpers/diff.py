"""Parse CSV/XLSX control plan files and compute row-level diffs."""
import logging
import os
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO
from typing import Any

import pandas as pd

logger = logging.getLogger("app")


# ── XML / ZIP helpers (handles broken openpyxl workbook relationship specs) ───

def _detect_ns(root) -> str:
    """Extract spreadsheetML namespace from root element tag."""
    tag = root.tag
    if tag.startswith("{"):
        return tag[1:tag.index("}")]
    return "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _col_letter_to_index(col: str) -> int:
    """Convert Excel column letter(s) to 1-based index. A=1, Z=26, AA=27."""
    result = 0
    for ch in col.upper():
        result = result * 26 + (ord(ch) - ord("A") + 1)
    return result


def _cell_addr_to_row_col(addr: str):
    """Split 'H6' → ('H', 6), 'BR5' → ('BR', 5). Returns (None, None) on failure."""
    m = re.match(r"([A-Za-z]+)(\d+)", addr)
    if not m:
        return None, None
    return m.group(1).upper(), int(m.group(2))


def _parse_shared_strings(ss_xml: bytes) -> list[str]:
    """Parse xl/sharedStrings.xml → list of string values."""
    try:
        root = ET.fromstring(ss_xml)
        NS = _detect_ns(root)
        return [
            "".join((t.text or "") for t in si.iter(f"{{{NS}}}t"))
            for si in root.iter(f"{{{NS}}}si")
        ]
    except Exception:
        return []


def _sheet_xml_to_dataframe(sheet_xml: bytes, shared_strings: list[str]) -> pd.DataFrame:
    """Parse a single worksheet XML into a DataFrame (first row = header)."""
    try:
        root = ET.fromstring(sheet_xml)
    except Exception:
        return pd.DataFrame()

    NS = _detect_ns(root)
    rows_data: dict[int, dict[int, str]] = {}
    max_col = 0

    for row_el in root.iter(f"{{{NS}}}row"):
        row_num = int(row_el.get("r", 0))
        rows_data[row_num] = {}
        for c_el in row_el.iter(f"{{{NS}}}c"):
            ref = c_el.get("r", "")
            col_str, _ = _cell_addr_to_row_col(ref)
            if col_str is None:
                continue
            col_idx = _col_letter_to_index(col_str)
            max_col = max(max_col, col_idx)

            t_type = c_el.get("t", "")
            value = ""
            if t_type == "s":
                v_el = c_el.find(f"{{{NS}}}v")
                if v_el is not None and v_el.text is not None:
                    idx = int(v_el.text)
                    value = shared_strings[idx] if 0 <= idx < len(shared_strings) else ""
            elif t_type == "inlineStr":
                is_el = c_el.find(f"{{{NS}}}is")
                if is_el is not None:
                    t_el = is_el.find(f"{{{NS}}}t")
                    if t_el is not None:
                        value = t_el.text or ""
            else:
                v_el = c_el.find(f"{{{NS}}}v")
                if v_el is not None and v_el.text is not None:
                    value = v_el.text

            rows_data[row_num][col_idx] = value

    if not rows_data or max_col == 0:
        return pd.DataFrame()

    max_row = max(rows_data.keys())
    matrix = [
        [rows_data.get(r, {}).get(c, "") for c in range(1, max_col + 1)]
        for r in range(1, max_row + 1)
    ]

    if not matrix:
        return pd.DataFrame()

    # First row as header; deduplicate empty/duplicate column names
    raw_headers = matrix[0]
    seen: dict[str, int] = {}
    headers: list[str] = []
    for h in raw_headers:
        h = str(h).strip() if h else ""
        if not h:
            h = f"col_{len(headers)}"
        if h in seen:
            seen[h] += 1
            h = f"{h}_{seen[h]}"
        else:
            seen[h] = 0
        headers.append(h)

    return pd.DataFrame(matrix[1:], columns=headers).fillna("")


def _read_excel_robust(data: bytes) -> pd.DataFrame:
    """
    Read Excel bytes into a DataFrame.

    First tries pandas/openpyxl normally. If openpyxl reports 0 worksheets
    (broken workbook relationship spec), falls back to direct ZIP+XML parsing.
    """
    buf = BytesIO(data)
    try:
        return pd.read_excel(buf, dtype=str).fillna("")
    except (ValueError, Exception):
        pass  # fall through to ZIP parsing

    buf.seek(0)
    try:
        with zipfile.ZipFile(buf, "r") as zf:
            names_in_zip = zf.namelist()

            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in names_in_zip:
                shared_strings = _parse_shared_strings(zf.read("xl/sharedStrings.xml"))

            # Find worksheet files ordered by name (sheet1, sheet2, …)
            sheet_files = sorted(
                n for n in names_in_zip
                if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
            )

            if not sheet_files:
                return pd.DataFrame()

            return _sheet_xml_to_dataframe(zf.read(sheet_files[0]), shared_strings)
    except Exception:
        return pd.DataFrame()


# ── Public API ────────────────────────────────────────────────────────────────

def _read_file(data: bytes, filename: str) -> pd.DataFrame:
    lower = filename.lower()
    buf = BytesIO(data)
    if lower.endswith(".csv"):
        return pd.read_csv(buf, dtype=str).fillna("")
    elif lower.endswith((".xlsx", ".xls")):
        return _read_excel_robust(data)
    raise ValueError(f"Unsupported file type: {filename}")


def compute_diff(
    old_data: bytes | None,
    old_name: str | None,
    new_data: bytes,
    new_name: str,
) -> tuple[list[dict[str, Any]], int]:
    """
    Returns (diff_rows, change_count).
    diff_rows: list of {row, field, oldValue, newValue}
    """
    new_df = _read_file(new_data, new_name)

    if old_data is None or old_name is None:
        # First version — every cell is "added"
        diff_rows: list[dict] = []
        for i, row in new_df.iterrows():
            for col in new_df.columns:
                diff_rows.append(
                    {"row": str(i), "field": col, "oldValue": "", "newValue": str(row[col])}
                )
        return diff_rows, len(new_df)

    old_df = _read_file(old_data, old_name)

    # Align on common columns
    all_cols = list(dict.fromkeys(list(old_df.columns) + list(new_df.columns)))
    old_df = old_df.reindex(columns=all_cols, fill_value="")
    new_df = new_df.reindex(columns=all_cols, fill_value="")

    max_rows = max(len(old_df), len(new_df))
    old_df = old_df.reindex(range(max_rows), fill_value="")
    new_df = new_df.reindex(range(max_rows), fill_value="")

    diff_rows = []
    for i in range(max_rows):
        for col in all_cols:
            old_val = str(old_df.at[i, col])
            new_val = str(new_df.at[i, col])
            if old_val != new_val:
                diff_rows.append(
                    {"row": str(i), "field": col, "oldValue": old_val, "newValue": new_val}
                )

    return diff_rows, len(diff_rows)


def _diff_result_to_dict(result, old_path: str, new_path: str) -> dict:
    """
    Convert a DiffResult (from excel_diff) into the standard app diff dict:
        {sheets, summary, sheet_names_a, sheet_names_b}
    """
    from collections import defaultdict
    from app.helpers.excel_diff import read_cells, _col_letter

    sheets_data: dict = defaultdict(lambda: {
        "cell_changes": {"modified": {}, "added": {}, "removed": {}},
        "shape_changes": {"added": [], "removed": []},
        "image_changes": {"new_images": [], "removed_images": [], "modified_images": []},
        "row_changes": [],
    })

    for cd in result.cell_changes:
        if cd.change_type == "modified":
            # Use V2 coordinate (new_coord) when the row shifted; fall back to cd.cell
            # when new_coord is absent (non-semantic diff path, same row in both files).
            coord = cd.new_coord if cd.new_coord else cd.cell
            sheets_data[cd.sheet]["cell_changes"]["modified"][coord] = {
                "previous": str(cd.old_value),
                "current": str(cd.new_value),
            }
        elif cd.change_type == "added":
            sheets_data[cd.sheet]["cell_changes"]["added"][cd.cell] = {
                "value": str(cd.new_value),
            }
        elif cd.change_type == "deleted":
            sheets_data[cd.sheet]["cell_changes"]["removed"][cd.cell] = {
                "value": str(cd.old_value),
            }

    # Convert RowDiff entries: register each cell for highlighting and record
    # the structured row event so callers can display [NEW ROW ADDED]/[ROW DELETED].
    for rd in getattr(result, "row_changes", []):
        row_num = rd.new_row if rd.change_type == "added" else rd.old_row
        cell_key = "added" if rd.change_type == "added" else "removed"
        for col_int, val in rd.data.items():
            coord = f"{_col_letter(col_int - 1)}{row_num}"
            sheets_data[rd.sheet]["cell_changes"][cell_key][coord] = {"value": str(val)}
        sheets_data[rd.sheet]["row_changes"].append({
            "change_type": rd.change_type,
            "row": row_num,
            "data": {
                f"{_col_letter(c - 1)}{row_num}": v
                for c, v in rd.data.items()
            },
        })

    for sd in result.shape_changes:
        if sd.change_type in ("added", "modified"):
            sheets_data[sd.sheet]["shape_changes"]["added"].append(
                f"{sd.shape_name}: {sd.new_text or ''}"
            )
        if sd.change_type in ("deleted", "modified"):
            sheets_data[sd.sheet]["shape_changes"]["removed"].append(
                f"{sd.shape_name}: {sd.old_text or ''}"
            )

    total_modified = total_added = total_removed = 0
    total_shape_added = total_shape_removed = 0
    sheets_list = []

    for sheet_name in sorted(sheets_data.keys()):
        sd = sheets_data[sheet_name]
        mod = sd["cell_changes"]["modified"]
        added = sd["cell_changes"]["added"]
        removed = sd["cell_changes"]["removed"]

        total_modified += len(mod)
        total_added += len(added)
        total_removed += len(removed)
        total_shape_added += len(sd["shape_changes"]["added"])
        total_shape_removed += len(sd["shape_changes"]["removed"])

        sheets_list.append({
            "sheet_name": sheet_name,
            "status": "matched",
            "cell_changes": sd["cell_changes"],
            "row_changes": sd["row_changes"],
            "summary": {
                "total_modified": len(mod),
                "total_added": len(added),
                "total_removed": len(removed),
            },
            "shape_changes": sd["shape_changes"],
            "image_changes": sd["image_changes"],
        })

    # Sheet name ordering from both files
    try:
        names_a = list(read_cells(old_path).keys())
        names_b = list(read_cells(new_path).keys())
    except Exception:
        names_a = names_b = [s["sheet_name"] for s in sheets_list]

    return {
        "sheets": sheets_list,
        "summary": {
            "total_modified": total_modified,
            "total_added": total_added,
            "total_removed": total_removed,
            "total_shape_added": total_shape_added,
            "total_shape_removed": total_shape_removed,
            "total_new_images": 0,
            "total_removed_images": 0,
            "total_sheets_compared": len(sheets_list),
            "new_sheets": 0,
            "removed_sheets": 0,
        },
        "sheet_names_a": names_a,
        "sheet_names_b": names_b,
    }


def compute_deep_diff(
    old_data: bytes | None,
    old_name: str | None,
    new_data: bytes,
    new_name: str,
) -> tuple[dict | list, int]:
    """
    For xlsx files with a previous version: returns a rich per-sheet diff dict
    using excel_diff (cell-level + shapes, with openpyxl→raw XML fallback and
    automatic namespace detection).

    Falls back to the simple row-level diff (list format) for CSV/.xls files
    or when the deep engine fails.

    Returns (diff_data, change_count).
    """
    new_ext = os.path.splitext(new_name)[1].lower()
    old_ext = os.path.splitext(old_name)[1].lower() if old_name else ""

    if (old_data is not None and old_name is not None
            and new_ext == ".xlsx" and old_ext == ".xlsx"):
        old_path = None
        new_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f_old:
                f_old.write(old_data)
                old_path = f_old.name
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f_new:
                f_new.write(new_data)
                new_path = f_new.name

            from app.helpers.excel_diff import diff as excel_diff
            result = excel_diff(old_path, new_path)
            diff_dict = _diff_result_to_dict(result, old_path, new_path)
            summary = diff_dict["summary"]
            change_count = (
                summary["total_modified"]
                + summary["total_added"]
                + summary["total_removed"]
            )
            return diff_dict, change_count
        except Exception as exc:
            logger.warning(f"Deep Excel diff failed ({exc}), falling back to simple diff.")
        finally:
            for p in (old_path, new_path):
                if p:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass

    # Fallback: simple pandas row-level diff
    diff_rows, change_count = compute_diff(old_data, old_name, new_data, new_name)
    return diff_rows, change_count
