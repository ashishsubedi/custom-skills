import json
import os
import platform
import subprocess
import sys
from PIL import Image

def ensure_swift_binary(binary_name: str) -> str | None:
    """Compiles a Swift helper in src/ to bin/ on demand. Returns binary path or None."""
    base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    bin_path = os.path.join(base_dir, "bin", binary_name)
    swift_src = os.path.join(base_dir, "src", f"{binary_name}.swift")

    if not os.path.exists(bin_path) and os.path.exists(swift_src):
        os.makedirs(os.path.join(base_dir, "bin"), exist_ok=True)
        try:
            subprocess.run(["swiftc", "-O", swift_src, "-o", bin_path], check=True, capture_output=True)
        except Exception as e:
            print(f"⚠️ Warning: Failed to compile {binary_name}.swift: {e}", file=sys.stderr)

    return bin_path if os.path.exists(bin_path) else None

def run_mac_ocr(image_path: str) -> list[dict]:
    """Runs the compiled Swift Apple Vision OCR binary on macOS."""
    bin_path = ensure_swift_binary("mac_ocr")
    if bin_path:
        res = subprocess.run([bin_path, image_path], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            try:
                return json.loads(res.stdout)
            except json.JSONDecodeError as err:
                print(f"⚠️ Warning: Failed to parse Apple Vision JSON output: {err}", file=sys.stderr)
        elif res.returncode != 0:
            print(f"⚠️ Apple Vision OCR error (Exit code {res.returncode}):\n  {res.stderr.strip()}", file=sys.stderr)

    return []

def run_tesseract_ocr(image_path: str) -> list[dict]:
    """Fallback OCR using tesseract CLI for Linux/Windows/macOS."""
    # Get image dimensions for coordinate normalization
    try:
        with Image.open(image_path) as img:
            img_w, img_h = img.size
    except Exception as err:
        print(f"⚠️ Warning: Could not read image dimensions for OCR: {err}", file=sys.stderr)
        img_w, img_h = 1, 1

    try:
        res = subprocess.run(
            ["tesseract", image_path, "stdout", "--oem", "1", "-c", "tessedit_create_tsv=1"],
            capture_output=True,
            text=True
        )

        if res.returncode != 0:
            err_msg = res.stderr.strip() or "Unknown Tesseract error"
            print(
                f"⚠️ Tesseract OCR execution error (Exit Code {res.returncode}):\n  {err_msg}",
                file=sys.stderr
            )
            return []

        lines = res.stdout.strip().split("\n")
        items = []
        if len(lines) > 1:
            for line in lines[1:]:
                parts = line.split("\t")
                if len(parts) >= 12:
                    text = parts[11].strip()
                    conf = float(parts[10]) if parts[10] != "-1" else 0.0
                    if text and conf > 0:
                        left_px = float(parts[6])
                        top_px = float(parts[7])
                        w_px = float(parts[8])
                        h_px = float(parts[9])

                        norm_bbox = [
                            min(1.0, max(0.0, left_px / img_w)),
                            min(1.0, max(0.0, top_px / img_h)),
                            min(1.0, max(0.0, w_px / img_w)),
                            min(1.0, max(0.0, h_px / img_h)),
                        ]

                        items.append({
                            "text": text,
                            "confidence": round(conf / 100.0, 2),
                            "bbox": norm_bbox
                        })
        return items

    except FileNotFoundError:
        print(
            "\n⚠️ Tesseract OCR is not installed on this system. OCR text extraction will be skipped.\n"
            "   To enable OCR on Linux/Windows, please install Tesseract:\n"
            "     - Ubuntu/Debian:  sudo apt install tesseract-ocr\n"
            "     - RHEL/Fedora:    sudo dnf install tesseract\n"
            "     - Arch Linux:     sudo pacman -S tesseract\n"
            "     - macOS (brew):   brew install tesseract\n",
            file=sys.stderr
        )
        return []
    except Exception as err:
        print(f"⚠️ Unexpected error executing Tesseract OCR:\n  {err}", file=sys.stderr)
        return []

def perform_ocr(image_path: str) -> list[dict]:
    """Executes platform-specific OCR engine."""
    system = platform.system()
    if system == "Darwin":
        results = run_mac_ocr(image_path)
        if results:
            return results

    # Linux / Windows / macOS fallback
    return run_tesseract_ocr(image_path)
