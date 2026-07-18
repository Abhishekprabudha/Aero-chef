#!/usr/bin/env python3
"""Compress a screen-recording MP4 to a safe size for GitHub browser upload."""

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
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--target-mib", type=float, default=24.0)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--fps", type=int, default=15)
    args = parser.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("FFmpeg and ffprobe must be installed and available on PATH")
    if not args.input.exists():
        raise SystemExit(f"Input video not found: {args.input}")

    duration = probe_duration(args.input)
    target_bits = args.target_mib * 1024 * 1024 * 8
    # Reserve 8% for the MP4 container and bitrate variability.
    bitrate_kbps = max(150, int((target_bits / duration / 1000) * 0.92))
    args.output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(args.input),
        "-an",
        "-vf",
        f"fps={args.fps},scale={args.width}:-2:flags=bilinear",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-tune",
        "zerolatency",
        "-b:v",
        f"{bitrate_kbps}k",
        "-maxrate",
        f"{int(bitrate_kbps * 1.18)}k",
        "-bufsize",
        f"{int(bitrate_kbps * 2.36)}k",
        "-profile:v",
        "baseline",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(args.output),
    ]
    print("+ " + " ".join(command))
    subprocess.run(command, check=True)
    size_mib = args.output.stat().st_size / 1024 / 1024
    print(f"Created {args.output} ({size_mib:.2f} MiB)")
    if size_mib >= 25:
        raise SystemExit("Output is still 25 MiB or larger; lower --target-mib and rerun")


if __name__ == "__main__":
    main()
