"""
highlighting_service.py — Apply diff-based green highlights to xlsx files.

Pure transformation functions with no database or storage dependencies.
Designed to be called from version_service after fetching the raw bytes and
diff data from storage / the database.

Highlight legend:
  Green (#92D050) — modified or added cells (including newly added rows)
                    and added/modified shapes.
  Removed items are not highlighted.

The ZIP+XML approach is used instead of openpyxl.save() so that complex
files with hidden sheets, VBA, custom properties, or non-standard structures
are preserved byte-for-byte, with only the targeted entries rewritten.
"""
import io
import re
import xml.etree.ElementTree as ET
import zipfile

HIGHLIGHT_COLOUR_ARGB = "FF92D050"
HIGHLIGHT_COLOUR_RGB  = "92D050"


def _collect_cell_styles(sheet_data: bytes, cell_addrs: set) -> dict:
    """Return {cell_addr: current_xf_index} for cells that need highlighting."""
    text = sheet_data.decode("utf-8")
    result = {}
    for m in re.finditer(r'<(?:[A-Za-z_][\w]*:)?c\b([^>]*)/?>', text):
        attrs = m.group(1)
        addr_m = re.search(r'\br="([^"]+)"', attrs)
        if not addr_m or addr_m.group(1) not in cell_addrs:
            continue
        s_m = re.search(r'\bs="(\d+)"', attrs)
        result[addr_m.group(1)] = int(s_m.group(1)) if s_m else 0
    # Cells in diff but absent from the XML default to style 0
    for addr in cell_addrs:
        if addr not in result:
            result[addr] = 0
    return result


def _patch_styles_bytes(
    styles_bytes: bytes,
    source_xf_indices: set,
    colour_argb: str = HIGHLIGHT_COLOUR_ARGB,
) -> tuple:
    """
    Inject a green fill into styles.xml, then clone each source xf with that
    fill applied — preserving font, border, alignment (wrapText), number format.
    Returns (patched_bytes, {original_xf_index: new_xf_index}).
    """
    text = styles_bytes.decode("utf-8")

    # ── inject fill ──────────────────────────────────────────────────────────
    m = re.search(r'(<fills[^>]*\bcount=")(\d+)(")', text)
    existing_fills = int(m.group(2)) if m else 2
    new_fill_idx = existing_fills
    new_fill = (
        f'<fill><patternFill patternType="solid">'
        f'<fgColor rgb="{colour_argb}"/>'
        f'<bgColor indexed="64"/>'
        f'</patternFill></fill>'
    )
    text = re.sub(r'(</fills>)', new_fill + r'\1', text, count=1)
    if m:
        text = re.sub(
            r'(<fills[^>]*\bcount=")(\d+)(")',
            lambda x: x.group(1) + str(existing_fills + 1) + x.group(3),
            text, count=1,
        )

    # ── find all existing xf entries in <cellXfs> ────────────────────────────
    cellxfs_m = re.search(r'(<cellXfs[^>]*>)(.*?)(</cellXfs>)', text, re.DOTALL)
    if not cellxfs_m:
        fallback_xf = (
            f'<xf numFmtId="0" fontId="0" fillId="{new_fill_idx}" '
            f'borderId="0" applyFill="1"/>'
        )
        text = re.sub(r'(</cellXfs>)', fallback_xf + r'\1', text, count=1)
        return text.encode("utf-8"), {idx: 0 for idx in source_xf_indices}

    xf_entries = list(re.finditer(r'<xf\b[^>]*?(?:/>|>.*?</xf>)', cellxfs_m.group(2), re.DOTALL))
    existing_xf_count = len(xf_entries)

    # ── clone each needed xf, swapping fillId ────────────────────────────────
    xf_map: dict = {}
    new_xfs: list = []
    next_idx = existing_xf_count

    for orig_idx in sorted(source_xf_indices):
        if orig_idx < len(xf_entries):
            xf_text = xf_entries[orig_idx].group(0)
            if re.search(r'\bfillId="', xf_text):
                xf_text = re.sub(r'\bfillId="\d+"', f'fillId="{new_fill_idx}"', xf_text)
            else:
                xf_text = re.sub(r'(<xf\b)', rf'\1 fillId="{new_fill_idx}"', xf_text)
            if re.search(r'\bapplyFill="', xf_text):
                xf_text = re.sub(r'\bapplyFill="[^"]*"', 'applyFill="1"', xf_text)
            else:
                xf_text = re.sub(r'(<xf\b[^>]*?)(/>|>)', rf'\1 applyFill="1"\2', xf_text, count=1)
        else:
            xf_text = (
                f'<xf numFmtId="0" fontId="0" fillId="{new_fill_idx}" '
                f'borderId="0" applyFill="1"/>'
            )

        new_xfs.append(xf_text)
        xf_map[orig_idx] = next_idx
        next_idx += 1

    if new_xfs:
        text = re.sub(r'(</cellXfs>)', ''.join(new_xfs) + r'\1', text, count=1)
        new_count = existing_xf_count + len(new_xfs)
        text = re.sub(
            r'(<cellXfs[^>]*\bcount=")(\d+)(")',
            lambda x: x.group(1) + str(new_count) + x.group(3),
            text, count=1,
        )

    return text.encode("utf-8"), xf_map


def _patch_sheet_xml(sheet_data: bytes, cell_to_xf: dict) -> bytes:
    """
    Apply style index to changed cells in a worksheet XML.
    Works by regex-patching <c r="ADDR"> tags — preserves all other content.
    """
    text = sheet_data.decode("utf-8")

    def _replace(m: re.Match) -> str:
        tag = m.group(0)
        addr_m = re.search(r'\br="([^"]+)"', tag)
        if not addr_m or addr_m.group(1) not in cell_to_xf:
            return tag
        xf = cell_to_xf[addr_m.group(1)]
        if re.search(r'\bs="\d+"', tag):
            return re.sub(r'\bs="\d+"', f's="{xf}"', tag)
        return re.sub(r'(\br="[^"]*")', rf'\1 s="{xf}"', tag, count=1)

    return re.sub(r'<(?:[A-Za-z_][\w]*:)?c\b[^>]*/?>',  _replace, text).encode("utf-8")


def _apply_fill_to_shapes(drawing_xml: bytes, shape_names: set, fill_color: str) -> bytes:
    """
    Inject solidFill into named shapes inside a drawing*.xml.
    Uses wildcard tag matching — works regardless of namespace prefix.
    """
    def _local(tag: str) -> str:
        return tag.split("}")[-1] if "}" in tag else tag

    def _ns(tag: str) -> str:
        return tag[1:tag.index("}")] if tag.startswith("{") else ""

    root = ET.fromstring(drawing_xml)

    xdr_ns = _ns(root.tag) or "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
    dml_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
    for el in root.iter():
        ns = _ns(el.tag)
        if ns and ns != xdr_ns and "drawingml" in ns and "spreadsheet" not in ns:
            dml_ns = ns
            break

    ET.register_namespace("xdr", xdr_ns)
    ET.register_namespace("a", dml_ns)
    ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")

    FILL_LOCALS = {"noFill", "solidFill", "gradFill", "pattFill", "blipFill", "grpFill"}

    for sp in [e for e in root.iter() if _local(e.tag) == "sp"]:
        shape_name = None
        for nv in [e for e in sp.iter() if _local(e.tag) == "nvSpPr"]:
            for cnv in [e for e in nv.iter() if _local(e.tag) == "cNvPr"]:
                shape_name = cnv.get("name") or cnv.get("id")
                break
            if shape_name:
                break

        if shape_name not in shape_names:
            continue

        sp_pr_list = [e for e in sp if _local(e.tag) == "spPr"]
        sp_pr = sp_pr_list[0] if sp_pr_list else ET.SubElement(sp, f"{{{xdr_ns}}}spPr")

        for child in list(sp_pr):
            if _local(child.tag) in FILL_LOCALS:
                sp_pr.remove(child)

        new_fill = ET.Element(f"{{{dml_ns}}}solidFill")
        ET.SubElement(new_fill, f"{{{dml_ns}}}srgbClr").set("val", fill_color)
        sp_pr.insert(0, new_fill)

    return ET.tostring(root, encoding="unicode").encode("utf-8")


def apply_highlights_to_xlsx(raw_bytes: bytes, diff_data: dict) -> bytes:
    """
    Apply green highlights to an xlsx file based on a diff_data dict.

    Highlights:
      - modified cells  (cell_changes.modified)
      - added cells     (cell_changes.added)
      - added rows      (RowDiff entries already converted to cell_changes.added
                         by _diff_result_to_dict — no extra handling needed)
      - added/modified shapes

    Returns the highlighted xlsx as bytes.
    If anything goes wrong the original bytes are returned unchanged.
    """
    in_buf = io.BytesIO(raw_bytes)
    out_buf = io.BytesIO()

    try:
        with zipfile.ZipFile(in_buf, "r") as zf_in:
            names_in_zip = set(zf_in.namelist())

            # ── 1. Build sheet XML path ↔ sheet name maps ─────────────────────
            sheet_path_to_name: dict = {}
            try:
                wb_root = ET.fromstring(zf_in.read("xl/workbook.xml"))
                rels_root = ET.fromstring(zf_in.read("xl/_rels/workbook.xml.rels"))
                rel_map = {r.get("Id"): r.get("Target", "") for r in rels_root}
                for el in wb_root.iter():
                    if el.tag.split("}")[-1] == "sheet":
                        r_id = next((v for k, v in el.attrib.items() if k.endswith("}id")), None)
                        sname = el.get("name", "")
                        target = rel_map.get(r_id, "")
                        if target:
                            sheet_path_to_name[f"xl/{target.lstrip('../')}"] = sname
            except Exception:
                pass
            name_to_sheet_path = {v: k for k, v in sheet_path_to_name.items()}

            # Build old→new sheet name map for diffs stored before the new-name fix.
            # sheet_names_a = V1 names, sheet_names_b = V2 names, matched by position.
            names_a = diff_data.get("sheet_names_a", [])
            names_b = diff_data.get("sheet_names_b", [])
            old_to_new: dict = {}
            for i, old in enumerate(names_a):
                new = old if old in names_b else (names_b[i] if i < len(names_b) else old)
                old_to_new[old] = new

            # ── 2. Collect cell addresses per sheet (modified + added + added rows)
            sheet_cell_addrs: dict = {}

            # ── Format A: app per-sheet format  {"sheets": [{sheet_name, cell_changes,
            #   row_changes: [{change_type, row, data}]}, …]}
            for sheet_info in diff_data.get("sheets", []):
                sname = old_to_new.get(sheet_info.get("sheet_name", ""),
                                       sheet_info.get("sheet_name", ""))
                sheet_path = name_to_sheet_path.get(sname)
                if not sheet_path:
                    continue
                cc = sheet_info.get("cell_changes", {})
                addrs = (
                    set(cc.get("modified", {}).keys())
                    | set(cc.get("added", {}).keys())
                )
                # Per-sheet row_changes (Format A) — data keys are already coords
                for rc in sheet_info.get("row_changes", []):
                    if rc.get("change_type") == "added":
                        addrs.update(rc.get("data", {}).keys())
                if addrs:
                    sheet_cell_addrs[sheet_path] = addrs

            # ── Format B: flat DiffResult JSON  {"cell_changes": […], "row_changes":
            #   [{sheet, change_type, old_row, new_row, data}], …}
            #   (produced by excel_diff print_json / CLI output)
            for rc in diff_data.get("row_changes", []):
                if rc.get("change_type") != "added":
                    continue
                sname = rc.get("sheet", "")
                sheet_path = name_to_sheet_path.get(sname)
                if not sheet_path:
                    continue
                addrs = sheet_cell_addrs.setdefault(sheet_path, set())
                addrs.update(rc.get("data", {}).keys())

            for cd in diff_data.get("cell_changes", []):
                if not isinstance(cd, dict):
                    continue
                if cd.get("change_type") not in ("modified", "added"):
                    continue
                sname = cd.get("sheet", "")
                sheet_path = name_to_sheet_path.get(sname)
                if not sheet_path:
                    continue
                cell = cd.get("cell") or cd.get("new_coord")
                if cell:
                    sheet_cell_addrs.setdefault(sheet_path, set()).add(cell)

            # Scan each sheet XML to find current style indices for those cells
            cell_current_styles: dict = {}
            unique_xf_indices: set = set()
            for sheet_path, addrs in sheet_cell_addrs.items():
                if sheet_path in names_in_zip:
                    styles = _collect_cell_styles(zf_in.read(sheet_path), addrs)
                    cell_current_styles[sheet_path] = styles
                    unique_xf_indices.update(styles.values())

            # ── 3. Patch styles.xml — clone each unique style with green fill ──
            patched_styles: bytes | None = None
            xf_map: dict = {}
            if "xl/styles.xml" in names_in_zip and unique_xf_indices:
                try:
                    patched_styles, xf_map = _patch_styles_bytes(
                        zf_in.read("xl/styles.xml"), unique_xf_indices
                    )
                except Exception:
                    pass

            # ── 4. Build per-sheet cell → new_xf map ──────────────────────────
            file_cell_map: dict = {}
            if xf_map:
                for sheet_path, style_map in cell_current_styles.items():
                    cell_to_xf = {
                        addr: xf_map[orig_xf]
                        for addr, orig_xf in style_map.items()
                        if orig_xf in xf_map
                    }
                    if cell_to_xf:
                        file_cell_map[sheet_path] = cell_to_xf

            # ── 5. Build drawing path → shape names map ───────────────────────
            shapes_to_highlight: dict = {}
            for sheet_info in diff_data.get("sheets", []):
                sname = sheet_info.get("sheet_name", "")
                names: set = set()
                for entry in sheet_info.get("shape_changes", {}).get("added", []):
                    shape_name = entry.split(": ", 1)[0].strip()
                    if shape_name:
                        names.add(shape_name)
                if names:
                    shapes_to_highlight[sname] = names

            sheet_path_to_drawing: dict = {}
            for name in names_in_zip:
                if name.startswith("xl/worksheets/_rels/") and name.endswith(".xml.rels"):
                    try:
                        for rel in ET.fromstring(zf_in.read(name)):
                            if "drawing" in rel.get("Type", "").lower():
                                sheet_xml = name.replace("_rels/", "").replace(".rels", "")
                                sheet_path_to_drawing[sheet_xml] = (
                                    "xl/" + rel.get("Target", "").lstrip("../")
                                )
                    except Exception:
                        continue

            drawing_to_shapes: dict = {}
            for sheet_path, sname in sheet_path_to_name.items():
                if sname in shapes_to_highlight:
                    drw = sheet_path_to_drawing.get(sheet_path)
                    if drw and drw in names_in_zip:
                        drawing_to_shapes.setdefault(drw, set()).update(
                            shapes_to_highlight[sname]
                        )

            # ── 6. Single-pass ZIP rewrite ─────────────────────────────────────
            with zipfile.ZipFile(out_buf, "w", zipfile.ZIP_DEFLATED) as zf_out:
                for item in zf_in.infolist():
                    data = zf_in.read(item.filename)
                    if item.filename == "xl/styles.xml" and patched_styles is not None:
                        data = patched_styles
                    elif item.filename in file_cell_map:
                        try:
                            data = _patch_sheet_xml(data, file_cell_map[item.filename])
                        except Exception:
                            pass
                    elif item.filename in drawing_to_shapes:
                        try:
                            data = _apply_fill_to_shapes(
                                data, drawing_to_shapes[item.filename], HIGHLIGHT_COLOUR_RGB
                            )
                        except Exception:
                            pass
                    zf_out.writestr(item, data)

    except Exception:
        return raw_bytes

    out_buf.seek(0)
    return out_buf.getvalue()
