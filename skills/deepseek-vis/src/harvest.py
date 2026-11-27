import base64
import glob
import json
import os
import sqlite3
import tempfile

def _write_temp(data: bytes, suffix: str) -> str:
    fd, path = tempfile.mkstemp(prefix="vis_harvest_", suffix=suffix)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    return path

def harvest_opencode(cwd: str, db: str | None = None) -> list[str]:
    """Recovers pasted images from the active opencode session (SQLite part table)."""
    if db is None:
        db = os.path.expanduser("~/.local/share/opencode/opencode.db")
    if not os.path.exists(db):
        return []

    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error:
        return []

    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT p.message_id, m.time_created, p.data FROM part p
               JOIN message m ON m.id = p.message_id
               JOIN session s ON s.id = m.session_id
               WHERE s.directory = ? AND p.data LIKE '%data:image%'
               ORDER BY s.time_updated DESC, m.time_created DESC, p.time_created""",
            (cwd,),
        )
        rows = cur.fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()

    images: list[str] = []
    current_mid = None
    for message_id, _time, data in rows:
        if message_id != current_mid:
            if images:
                return images
            current_mid = message_id
            images = []
        try:
            part = json.loads(data)
        except json.JSONDecodeError:
            continue
        if part.get("type") != "file":
            continue
        url = part.get("url", "")
        mime = part.get("mime", "")
        if not url.startswith("data:image") or "base64," not in url:
            continue
        b64 = url.split("base64,", 1)[1]
        try:
            content = base64.b64decode(b64)
        except Exception:
            continue
        ext = {
            "png": "png", "jpeg": "jpg", "gif": "gif", "webp": "webp",
        }.get(mime.split("/")[-1], "png")
        images.append(_write_temp(content, f".{ext}"))
    return images


def harvest_pi() -> list[str]:
    """Recovers pasted images from the active Pi session (PI_SESSION_FILE)."""
    session_file = os.environ.get("PI_SESSION_FILE")
    if not session_file or not os.path.exists(session_file):
        return []

    paths: list[str] = []
    try:
        with open(session_file, "r") as f:
            for line in f:
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") != "message":
                    continue
                content = (msg.get("message") or {}).get("content")
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "image":
                            data = item.get("data", "")
                            mime = item.get("mimeType", "image/png")
                            try:
                                raw = base64.b64decode(data)
                                ext = mime.split("/")[-1].replace("+", "").lower()
                                paths.append(_write_temp(raw, f".{ext or 'png'}"))
                            except Exception:
                                pass
                elif isinstance(content, str):
                    # Pi inserts pasted image paths as plain text
                    for found in glob.glob(os.path.join(tempfile.gettempdir(), "pi-clipboard-*")):
                        if found in content and os.path.exists(found) and found not in paths:
                            paths.append(found)
    except Exception:
        return []

    return paths


def harvest_antigravity() -> list[str]:
    """Recovers uploaded/pasted images from Antigravity / Gemini CLI session storage."""
    brain_dir = os.path.expanduser("~/.gemini/antigravity-cli/brain")
    if not os.path.exists(brain_dir):
        return []
    media_files = glob.glob(os.path.join(brain_dir, "*", ".user_uploaded", "*"))
    if not media_files:
        return []
    media_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    latest = media_files[0]
    if os.path.exists(latest) and os.path.getsize(latest) > 0:
        return [latest]
    return []


def harvest_clipboard() -> list[str]:
    """Recovers image directly from OS clipboard if available."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grabclipboard()
        if img is not None:
            if hasattr(img, "save"):
                path = _write_temp(b"", ".png")
                img.save(path, "PNG")
                return [path]
            elif isinstance(img, list):
                valid = [
                    p for p in img
                    if isinstance(p, str) and os.path.exists(p) and p.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
                ]
                if valid:
                    return valid
    except Exception:
        pass
    return []


def harvest_images(harness: str | None = None) -> list[str]:
    """Recover pasted images from the running harness. Returns temp file paths.

    Tries the named harness first (if recognized). Otherwise evaluates all known
    harvesters and picks images from the most recently updated source.
    """
    harvesters: dict[str, callable] = {
        "opencode": lambda: harvest_opencode(os.getcwd()),
        "pi": harvest_pi,
        "antigravity": harvest_antigravity,
        "clipboard": harvest_clipboard,
    }
    if harness and harness in harvesters:
        images = harvesters[harness]()
        if images:
            return images

    candidates: list[tuple[float, list[str]]] = []
    for name, fn in harvesters.items():
        try:
            imgs = fn()
            if imgs:
                mtime = max(os.path.getmtime(f) for f in imgs if os.path.exists(f))
                candidates.append((mtime, imgs))
        except Exception:
            pass

    if candidates:
        candidates.sort(key=lambda c: c[0], reverse=True)
        return candidates[0][1]

    return []
