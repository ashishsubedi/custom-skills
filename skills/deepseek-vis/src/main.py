import argparse
import json
import os
import sys
import tempfile

from ascii import convert_to_ascii
from harvest import harvest_images
from ocr import perform_ocr
from overlay import format_ocr_metadata, overlay_ocr_on_ascii

def generate_markdown(
    display_name: str,
    ascii_art: str,
    overlay_art: str,
    ocr_items: list[dict],
    grid_w: int,
    grid_h: int,
    mode: str,
    index: int = 1,
    total: int = 1
) -> str:
    ocr_table = format_ocr_metadata(ocr_items, grid_w, grid_h)

    header_prefix = f"## Image {index}/{total}: `{display_name}`" if total > 1 else f"## Image Analysis: `{display_name}`"
    output = f"{header_prefix}\n"
    output += f"**Grid:** {grid_w}x{grid_h}\n\n"

    if mode in ["hybrid", "overlay"]:
        output += "### ASCII Layout & Overlay\n"
        output += "```text\n"
        output += overlay_art + "\n"
        output += "```\n\n"
    elif mode == "ascii":
        output += "### ASCII Layout\n"
        output += "```text\n"
        output += ascii_art + "\n"
        output += "```\n\n"

    if mode in ["hybrid", "ocr"]:
        output += "### OCR Text & Coordinates\n"
        output += ocr_table + "\n"

    return output

def process_single_image(target_path: str, display_name: str, width: int, mode: str, no_edge: bool) -> dict:
    """Processes a single image file into ASCII layout and OCR metadata."""
    raw_ascii, grid_w, grid_h = convert_to_ascii(
        target_path, target_width=width, edge_enhance=not no_edge
    )
    ocr_items = perform_ocr(target_path)
    overlay_ascii = overlay_ocr_on_ascii(raw_ascii, grid_w, grid_h, ocr_items)
    return {
        "display_name": display_name,
        "grid_w": grid_w,
        "grid_h": grid_h,
        "raw_ascii": raw_ascii,
        "overlay_ascii": overlay_ascii,
        "ocr_items": ocr_items,
    }

def main():
    parser = argparse.ArgumentParser(
        description="DeepSeek Vision Bridge: Converts images to ASCII layout & OCR text for text-only LLMs."
    )
    parser.add_argument(
        "image_paths",
        nargs="*",
        default=[],
        help="One or more image file paths (omit to harvest pasted images from the active harness)"
    )
    parser.add_argument(
        "-w", "--width", type=int, default=90, help="Target ASCII width in characters (default: 90)"
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["hybrid", "ascii", "ocr", "overlay"],
        default="hybrid",
        help="Output mode (default: hybrid)",
    )
    parser.add_argument(
        "--harness",
        help="agent harness pasted images came from (opencode, pi, ...); falls back through all if unknown/omitted",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output raw JSON data"
    )
    parser.add_argument(
        "--no-edge", action="store_true", help="Disable edge sharpening for ASCII art"
    )

    args = parser.parse_args()

    targets: list[tuple[str, str, bool]] = []

    if args.image_paths:
        for p in args.image_paths:
            if not os.path.exists(p):
                kw = p.lower()
                if kw in ["clipboard", "opencode", "pi", "antigravity"]:
                    harvest_files = harvest_images(kw)
                    if harvest_files:
                        for idx, fpath in enumerate(harvest_files, 1):
                            disp_name = "Clipboard Image" if kw == "clipboard" else f"Pasted Image ({kw})"
                            if len(harvest_files) > 1:
                                disp_name += f" {idx}"
                            targets.append((fpath, disp_name, True))
                        continue
                    else:
                        msg = "No image found on system clipboard." if kw == "clipboard" else f"No images found for harness '{kw}'."
                        print(f"Error: {msg}", file=sys.stderr)
                        sys.exit(1)
                print(f"Error: File not found at '{p}'", file=sys.stderr)
                sys.exit(1)
            targets.append((p, os.path.basename(p), False))
    else:
        # No explicit files: recover images pasted into the active harness session.
        harvest_files = harvest_images(args.harness)
        if not harvest_files:
            print(
                "Error: No images found in the current harness session.\n"
                "Paste an image into opencode/pi, or pass file path(s).\n"
                "Examples:\n"
                "  deepseek-vis                    # harvest pasted images from active harness\n"
                "  deepseek-vis shot1.png shot2.png",
                file=sys.stderr
            )
            sys.exit(1)
        for idx, fpath in enumerate(harvest_files, 1):
            name = f"Pasted Image {idx}" if len(harvest_files) > 1 else "Pasted Image"
            targets.append((fpath, name, True))

    temp_files = []
    results = []
    total_targets = len(targets)

    try:
        for idx, (fpath, name, is_tmp) in enumerate(targets, 1):
            if is_tmp:
                temp_files.append(fpath)
            res = process_single_image(fpath, name, args.width, args.mode, args.no_edge)
            results.append((res, idx))

        if args.json:
            json_output = []
            for res, idx in results:
                json_output.append({
                    "image": res["display_name"],
                    "grid": {"width": res["grid_w"], "height": res["grid_h"]},
                    "ascii": res["raw_ascii"],
                    "overlay_ascii": res["overlay_ascii"],
                    "ocr": res["ocr_items"],
                })
            print(json.dumps(json_output if total_targets > 1 else json_output[0], indent=2))
        else:
            md_blocks = []
            for res, idx in results:
                md = generate_markdown(
                    res["display_name"],
                    res["raw_ascii"],
                    res["overlay_ascii"],
                    res["ocr_items"],
                    res["grid_w"],
                    res["grid_h"],
                    args.mode,
                    index=idx,
                    total=total_targets
                )
                md_blocks.append(md)
            print("\n---\n\n".join(md_blocks))
    finally:
        for tmp in temp_files:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass

if __name__ == "__main__":
    main()