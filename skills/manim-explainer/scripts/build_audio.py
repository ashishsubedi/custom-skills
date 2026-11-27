#!/usr/bin/env python3
"""Generate per-subbeat edge-tts narration, exact WordBoundary timings, and subtitle cues."""
import argparse
import asyncio
import json
import re
import shutil
import subprocess
import wave
from pathlib import Path


def wrap_two_lines(text: str, max_line: int = 44) -> str:
    """Wrap subtitle text cleanly onto at most two balanced lines."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > max_line and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    if len(lines) <= 2 or len(words) < 2:
        return "\n".join(lines)
    mid = len(text) // 2
    best_idx = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - mid))
    return " ".join(words[:best_idx]) + "\n" + " ".join(words[best_idx:])


def split_sub_clauses(text: str, max_chars: int = 84) -> list[str]:
    """Split a long subtitle sentence into short readable clause cues."""
    if len(text) <= max_chars:
        return [text]
    parts = re.split(r"(?<=[.!?;—])\s+", text)
    if len(parts) == 1:
        parts = re.split(r"(?<=,)\s+", text)
    if len(parts) > 1:
        merged = []
        for p in parts:
            if merged and len(merged[-1]) + len(p) + 1 <= max_chars:
                merged[-1] = f"{merged[-1]} {p}"
            else:
                merged.append(p)
        final = []
        for m in merged:
            if len(m) <= max_chars:
                final.append(m)
            else:
                w = m.split()
                k = max(1, len(w) // 2)
                final.append(" ".join(w[:k]))
                final.append(" ".join(w[k:]))
        return final
    words = text.split()
    mid = max(1, len(words) // 2)
    return [" ".join(words[:mid]), " ".join(words[mid:])]


def map_clauses_to_words(clauses: list[str], words: list[dict], dur: float) -> list[dict]:
    """Align display clauses to spoken WordBoundary timestamps."""
    total_chars = max(1, sum(len(c) for c in clauses))
    cues = []
    if words:
        n_w = len(words)
        w_idx = 0
        for ci, clause in enumerate(clauses):
            if ci == len(clauses) - 1:
                end_w = n_w - 1
            else:
                step = max(1, int(round((len(clause) / total_chars) * n_w)))
                end_w = min(n_w - 1 - (len(clauses) - 1 - ci), w_idx + step - 1)
            c_start = max(0.0, words[w_idx]["start"] - 0.03) if ci > 0 else 0.0
            c_end = min(dur, words[end_w]["start"] + words[end_w]["dur"] + 0.08) if ci < len(clauses) - 1 else dur
            if cues and c_start < cues[-1]["end"]:
                cues[-1]["end"] = round(c_start, 4)
            cues.append({
                "start": round(c_start, 4),
                "end": round(max(c_start + 0.25, c_end), 4),
                "text": wrap_two_lines(clause),
            })
            w_idx = min(n_w - 1, end_w + 1)
        return cues

    off = 0.0
    for clause in clauses:
        span = dur * len(clause) / total_chars
        cues.append({"start": round(off, 4), "end": round(off + span, 4), "text": wrap_two_lines(clause)})
        off += span
    return cues


async def synth_one(sem: asyncio.Semaphore, sb: dict, audio_dir: Path, voice: str, rate: str, ffmpeg: str):
    import edge_tts

    sid = sb["id"]
    mp3 = audio_dir / f"{sid}.mp3"
    wav = audio_dir / f"{sid}.wav"
    meta = audio_dir / f"{sid}.words.json"
    if wav.exists() and meta.exists():
        print(f"  {sid:6s} cached", flush=True)
        return

    async with sem:
        for attempt in range(4):
            try:
                comm = edge_tts.Communicate(sb["tts"], voice=voice, rate=rate, boundary="WordBoundary")
                audio_bytes = bytearray()
                words = []
                async for ch in comm.stream():
                    if ch["type"] == "audio":
                        audio_bytes.extend(ch["data"])
                    elif ch["type"] == "WordBoundary":
                        words.append({
                            "start": round(ch["offset"] / 1e7, 4),
                            "dur": round(ch["duration"] / 1e7, 4),
                            "text": ch["text"],
                        })
                if not audio_bytes:
                    raise RuntimeError("Empty audio stream")
                mp3.write_bytes(audio_bytes)
                subprocess.run(
                    [
                        ffmpeg, "-y", "-v", "error", "-i", str(mp3),
                        "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le",
                        "-af", "silenceremove=stop_periods=-1:stop_duration=0.25:stop_threshold=-55dB",
                        str(wav),
                    ],
                    check=True,
                )
                meta.write_text(json.dumps(words, indent=2))
                print(f"  {sid:6s} generated ({len(words)} words)", flush=True)
                return
            except Exception as exc:
                if attempt == 3:
                    raise
                print(f"  {sid:6s} retry {attempt + 1}: {exc}", flush=True)
                await asyncio.sleep(1.0 + attempt)


async def run_pipeline(args):
    work_dir = Path(args.work_dir).resolve()
    beats_path = Path(args.beats) if args.beats else work_dir / "beats.json"
    audio_dir = work_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = args.ffmpeg or shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"

    beats = json.loads(beats_path.read_text())
    subbeats = [sb for scene in beats for sb in scene["subbeats"]]
    sem = asyncio.Semaphore(args.concurrency)
    print(f"Synthesizing {len(subbeats)} sub-beats via {args.voice} ({args.rate})...", flush=True)
    await asyncio.gather(*(synth_one(sem, sb, audio_dir, args.voice, args.rate, ffmpeg) for sb in subbeats))

    timings = {"scenes": {}, "subbeats": {}}
    cum = 0.0
    for scene in beats:
        s_start = cum
        for idx, sb in enumerate(scene["subbeats"]):
            sid = sb["id"]
            with wave.open(str(audio_dir / f"{sid}.wav"), "rb") as wf:
                dur = wf.getnframes() / float(wf.getframerate())
            words = json.loads((audio_dir / f"{sid}.words.json").read_text())
            clauses = split_sub_clauses(sb.get("sub") or sb["tts"])
            cues = map_clauses_to_words(clauses, words, dur)
            pad = args.scene_pad if idx == len(scene["subbeats"]) - 1 else args.subbeat_pad
            timings["subbeats"][sid] = {
                "scene": scene["id"],
                "duration": round(dur, 4),
                "pad": pad,
                "planned_start": round(cum, 4),
                "cues": cues,
                "words": words,
            }
            cum += dur + pad
        timings["scenes"][scene["id"]] = {
            "start": round(s_start, 4),
            "end": round(cum, 4),
            "duration": round(cum - s_start, 4),
        }

    timings["total_duration"] = round(cum, 4)
    (work_dir / "timings.json").write_text(json.dumps(timings, indent=2))
    print(f"DONE: {len(subbeats)} sub-beats | total planned duration: {cum:.2f}s ({cum / 60:.2f}m)")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work-dir", default=".", help="Animation workspace containing beats.json")
    p.add_argument("--beats", default=None, help="Explicit path to beats.json")
    p.add_argument("--voice", default="en-US-AndrewNeural")
    p.add_argument("--rate", default="+5%")
    p.add_argument("--subbeat-pad", type=float, default=0.20)
    p.add_argument("--scene-pad", type=float, default=0.40)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--ffmpeg", default=None)
    args = p.parse_args()
    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()
