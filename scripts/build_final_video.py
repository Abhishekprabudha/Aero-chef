#!/usr/bin/env python3
"""Mux the compressed AeroChef demo video with the generated narration."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--video",
        type=Path,
        default=Path("assets/aerochef_demo_compressed.mp4"),
    )
    parser.add_argument(
        "--narration",
        type=Path,
        default=Path("artifacts/narration.mp3"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/aerochef_demo_with_narration.mp4"),
    )
    args = parser.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("FFmpeg and ffprobe must be installed and available on PATH")
    if not args.video.exists():
        raise SystemExit(f"Video not found: {args.video}")
    if not args.narration.exists():
        raise SystemExit(f"Narration not found: {args.narration}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    video_duration = probe_duration(args.video)
    audio_filter = (
        "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,"
        "apad,"
        f"atrim=duration={video_duration:.3f},"
        "aresample=48000[narration]"
    )
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(args.video),
        "-i",
        str(args.narration),
        "-filter_complex",
        audio_filter,
        "-map",
        "0:v:0",
        "-map",
        "[narration]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-shortest",
        str(args.output),
    ]
    print("+ " + " ".join(command))
    subprocess.run(command, check=True)
    print(f"Created {args.output}")
    print(f"Final duration: {probe_duration(args.output):.3f} seconds")


if __name__ == "__main__":
    main()
