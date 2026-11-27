#!/usr/bin/env python3
"""Mux frame-locked narration, generate SRT, burn Pillow RGBA subtitles, and verify streams."""
import argparse
import bisect
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SUB_W = 1920
SUB_H = 155
SUB_Y = 1080 - SUB_H


def probe(path: Path, ffprobe: str, entries: str = "format=duration") -> str:
    return subprocess.check_output(
        [ffprobe, "-v", "error", "-show_entries", entries, "-of", "default=nw=1:nk=1", str(path)],
        text=True,
    ).strip()


def srt_time(t: float) -> str:
    ms = max(0, int(round(t * 1000)))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def render_sub_strip(text: str, font: ImageFont.FreeTypeFont) -> bytes:
    """Render a centered dark-pill subtitle onto a 1920x155 RGBA strip."""
    img = Image.new("RGBA", (SUB_W, SUB_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lines = text.split("\n")
    bboxes = [draw.textbbox((0, 0), ln, font=font) for ln in lines]
    line_ws = [bb[2] - bb[0] for bb in bboxes]
    line_hs = [max(34, bb[3] - bb[1]) for bb in bboxes]
    gap = 8
    total_h = sum(line_hs) + gap * (len(lines) - 1)
    max_w = max(line_ws)

    pad_x, pad_y = 26, 12
    box_w = max_w + 2 * pad_x
    box_h = total_h + 2 * pad_y
    x0 = (SUB_W - box_w) // 2
    y1 = SUB_H - 22
    y0 = max(4, y1 - box_h)

    draw.rounded_rectangle(
        [x0, y0, x0 + box_w, y1],
        radius=12,
        fill=(8, 12, 24, 212),
        outline=(88, 196, 221, 70),
        width=2,
    )

    cy = y0 + pad_y
    for ln, lw, lh, bb in zip(lines, line_ws, line_hs, bboxes):
        tx = (SUB_W - lw) // 2 - bb[0]
        ty = cy - bb[1] + 2
        draw.text((tx + 1, ty + 1), ln, font=font, fill=(0, 0, 0, 180))
        draw.text((tx, ty), ln, font=font, fill=(242, 246, 252, 255))
        cy += lh + gap

    return img.tobytes()


DEFAULT_FONTS = (
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)


def resolve_font(font_arg: str | None, size: int = 34) -> ImageFont.FreeTypeFont:
    """Resolve an explicit or OS-default TrueType font for subtitle rendering."""
    candidates = [font_arg] if font_arg else list(DEFAULT_FONTS)
    for fp in candidates:
        if fp and Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work-dir", default=".", help="Animation workspace containing beats.json & timings.json")
    p.add_argument("--raw", required=True, help="Rendered 1080p Manim MP4 path (relative to work-dir or abs)")
    p.add_argument("--out", required=True, help="Final output MP4 path (relative to work-dir or abs)")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--font", default=None, help="Optional TrueType font path")
    p.add_argument("--ffmpeg", default=None)
    p.add_argument("--ffprobe", default=None)
    args = p.parse_args()

    work_dir = Path(args.work_dir).resolve()
    raw = Path(args.raw) if Path(args.raw).is_absolute() else work_dir / args.raw
    out = Path(args.out) if Path(args.out).is_absolute() else work_dir / args.out
    if not raw.exists():
        raise SystemExit(f"Missing rendered Manim video at {raw}")

    ffmpeg = args.ffmpeg or shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    ffprobe = args.ffprobe or shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
    audio_dir = work_dir / "audio"
    frames_dir = work_dir / "frames"

    video_dur = float(probe(raw, ffprobe))
    nb_frames = int(round(video_dur * args.fps))
    beats = json.loads((work_dir / "beats.json").read_text())
    timings = json.loads((work_dir / "timings.json").read_text())
    marks = json.loads((work_dir / "video_timings.json").read_text())
    subbeats = [sb for sc in beats for sb in sc["subbeats"]]

    padded_wav = audio_dir / "narration_raw.wav"
    norm_wav = audio_dir / "narration_norm.wav"
    cmd = [ffmpeg, "-y", "-v", "error"]
    parts = []
    for i, sb in enumerate(subbeats):
        sid = sb["id"]
        cmd += ["-i", str(audio_dir / f"{sid}.wav")]
        ms_delay = int(round(marks["subbeats"][sid]["start"] * 1000))
        parts.append(f"[{i}:a]adelay={ms_delay}[a{i}]")
    fc = (
        ";".join(parts)
        + ";"
        + "".join(f"[a{i}]" for i in range(len(subbeats)))
        + f"amix=inputs={len(subbeats)}:normalize=0[out]"
    )
    cmd += ["-filter_complex", fc, "-map", "[out]", "-t", f"{video_dur:.4f}", "-c:a", "pcm_s16le", str(padded_wav)]
    subprocess.run(cmd, check=True)

    subprocess.run(
        [
            ffmpeg, "-y", "-v", "error", "-i", str(padded_wav),
            "-af", "highpass=f=75,loudnorm=I=-16:TP=-1.5:LRA=9",
            "-ar", "48000", "-c:a", "pcm_s16le", str(norm_wav),
        ],
        check=True,
    )

    font = resolve_font(args.font, 34)
    blank_buf = bytes(SUB_W * SUB_H * 4)
    srt_lines, cues_abs = [], []
    cue_idx = 0
    for sb in subbeats:
        sid = sb["id"]
        v_start = marks["subbeats"][sid]["start"]
        for cue in timings["subbeats"][sid]["cues"]:
            cue_idx += 1
            t0 = v_start + cue["start"]
            t1 = min(video_dur - 0.05, v_start + cue["end"])
            srt_lines.append(f"{cue_idx}\n{srt_time(t0)} --> {srt_time(t1)}\n{cue['text']}\n")
            cues_abs.append((t0, t1, render_sub_strip(cue["text"], font)))

    (work_dir / "subtitles.srt").write_text("\n".join(srt_lines))
    starts = [c[0] for c in cues_abs]

    ff_cmd = [
        ffmpeg, "-y", "-v", "error",
        "-i", str(raw),
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{SUB_W}x{SUB_H}", "-r", str(args.fps), "-i", "pipe:0",
        "-i", str(norm_wav),
        "-filter_complex", f"[0:v][1:v]overlay=0:{SUB_Y}:shortest=1[v]",
        "-map", "[v]", "-map", "2:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        str(out),
    ]
    proc = subprocess.Popen(ff_cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for f in range(nb_frames):
        t = f / args.fps
        idx = bisect.bisect_right(starts, t) - 1
        buf = cues_abs[idx][2] if (idx >= 0 and cues_abs[idx][0] <= t <= cues_abs[idx][1]) else blank_buf
        proc.stdin.write(buf)
    proc.stdin.close()
    ret = proc.wait()
    if ret != 0:
        raise SystemExit(f"ffmpeg overlay failed with exit code {ret}")

    streams = json.loads(
        subprocess.check_output(
            [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(out)],
            text=True,
        )
    )
    out_dur = float(streams["format"]["duration"])
    drift = [
        marks["subbeats"][sb["id"]]["start"] - timings["subbeats"][sb["id"]]["planned_start"]
        for sb in subbeats
    ]
    report = [
        f"output: {out}",
        f"duration: {out_dur:.2f}s ({out_dur / 60:.2f} min)",
        f"size: {int(streams['format']['size']) / 1e6:.1f} MB",
        f"subbeats: {len(subbeats)} | cues: {cue_idx}",
        f"max video-plan drift: {max(abs(d) for d in drift):.4f}s (audio & subs locked directly to video marks)",
    ]
    for s in streams["streams"]:
        if s["codec_type"] == "video":
            report.append(f"video: {s['codec_name']} {s['width']}x{s['height']} @ {s['r_frame_rate']} fps")
        elif s["codec_type"] == "audio":
            report.append(f"audio: {s['codec_name']} {s['sample_rate']} Hz {s['channels']}ch")

    vol = subprocess.check_output(
        [ffmpeg, "-v", "info", "-i", str(out), "-af", "volumedetect", "-f", "null", "-"],
        stderr=subprocess.STDOUT, text=True,
    )
    for ln in vol.splitlines():
        if "mean_volume" in ln or "max_volume" in ln:
            report.append(ln.strip())

    frames_dir.mkdir(exist_ok=True)
    for old in frames_dir.glob("*.png"):
        old.unlink()
    for sc in beats:
        sc_id = sc["id"]
        s0, s1 = marks["scenes"][sc_id]["start"], marks["scenes"][sc_id]["end"]
        for tag, frac in (("mid1", 0.35), ("mid2", 0.78)):
            ts = min(out_dur - 0.1, s0 + (s1 - s0) * frac)
            subprocess.run(
                [ffmpeg, "-y", "-v", "error", "-ss", f"{ts:.2f}", "-i", str(out), "-frames:v", "1", str(frames_dir / f"{sc_id}_{tag}.png")],
                check=True,
            )

    txt = "\n".join(report) + "\n"
    (work_dir / "verification.txt").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
