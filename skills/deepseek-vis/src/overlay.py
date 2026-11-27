def get_region_name(left: float, top: float) -> str:
    """Helper to convert normalized coordinates to human-readable region names."""
    v_pos = "Top" if top < 0.33 else ("Center" if top < 0.66 else "Bottom")
    h_pos = "Left" if left < 0.33 else ("Center" if left < 0.66 else "Right")
    return f"{v_pos}-{h_pos}"

def overlay_ocr_on_ascii(
    ascii_str: str,
    grid_w: int,
    grid_h: int,
    ocr_items: list[dict]
) -> str:
    """
    Overlays detected OCR text onto the ASCII grid at exact coordinate positions.
    """
    lines = [list(line) for line in ascii_str.split("\n")]
    if not lines:
        return ascii_str

    for item in ocr_items:
        text = item.get("text", "").strip()
        bbox = item.get("bbox", [])
        if not text or len(bbox) < 4:
            continue

        left, top, w, h = bbox
        start_col = int(left * grid_w)
        start_row = int(top * grid_h)

        if 0 <= start_row < len(lines):
            line = lines[start_row]
            # Replace characters in line with text
            for i, ch in enumerate(text):
                col = start_col + i
                if 0 <= col < len(line):
                    line[col] = ch

    return "\n".join("".join(line) for line in lines)

def format_ocr_metadata(ocr_items: list[dict], grid_w: int, grid_h: int) -> str:
    """Formats OCR findings into a concise Markdown table."""
    if not ocr_items:
        return "*No OCR text detected.*"

    md = "| # | Region | Position | Text | Conf |\n"
    md += "|---|--------|----------|------|------|\n"
    for i, item in enumerate(ocr_items, 1):
        text = item.get("text", "").replace("|", "\\|")
        bbox = item.get("bbox", [0, 0, 0, 0])
        conf = item.get("confidence", 1.0)
        region = get_region_name(bbox[0], bbox[1])
        col = int(bbox[0] * grid_w)
        row = int(bbox[1] * grid_h)
        md += f"| {i} | {region} | ({col},{row}) | `{text}` | {conf:.0%} |\n"
    return md
