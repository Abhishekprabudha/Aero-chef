#!/usr/bin/env python3
"""Generate a time-aligned narration MP3 from segmented AeroChef script JSON."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import edge_tts


def run(command: list[str]) -> None:
    printable = " ".join(command)
    print(f"+ {printable}")
    subprocess.run(command, check=True)


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


def atempo_chain(value: float) -> str:
    """Create a valid FFmpeg atempo chain for any positive tempo value."""
    if value <= 0:
        raise ValueError("Tempo must be positive")
    factors: list[float] = []
    while value < 0.5:
        factors.append(0.5)
        value /= 0.5
    while value > 2.0:
        factors.append(2.0)
        value /= 2.0
    factors.append(value)
    return ",".join(f"atempo={factor:.6f}" for factor in factors)


def seconds_to_srt(value: float) -> str:
    milliseconds = int(round(value * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


async def synthesize(text: str, voice: str, rate: str, output: Path) -> None:
    communicator = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await communicator.save(str(output))


async def build_narration(
    segments_file: Path,
    output_file: Path,
    voice: str | None,
    rate: str | None,
) -> None:
    data: dict[str, Any] = json.loads(segments_file.read_text(encoding="utf-8"))
    segments = data.get("segments", [])
    if not segments:
        raise ValueError("No narration segments were found")

    chosen_voice = voice or data.get("default_voice", "en-US-AvaNeural")
    chosen_rate = rate or data.get("default_rate", "-10%")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="aerochef_tts_") as tmp:
        temp_dir = Path(tmp)
        wav_files: list[Path] = []
        report: list[dict[str, Any]] = []

        for index, segment in enumerate(segments, start=1):
            start = float(segment["start"])
            end = float(segment["end"])
            duration = end - start
            if duration <= 0:
                raise ValueError(f"Segment {index} has a non-positive duration")

            raw_mp3 = temp_dir / f"segment_{index:02d}_raw.mp3"
            fitted_wav = temp_dir / f"segment_{index:02d}.wav"
            print(f"Synthesizing segment {index}: {segment['title']}")
            await synthesize(segment["text"], chosen_voice, chosen_rate, raw_mp3)

            raw_duration = probe_duration(raw_mp3)
            speech_window = max(1.0, duration - 0.45)
            exact_tempo = raw_duration / speech_window
            # Keep the voice natural. Any remaining room is filled with silence.
            applied_tempo = min(max(exact_tempo, 0.78), 1.30)
            filter_chain = (
                f"{atempo_chain(applied_tempo)},"
                "loudnorm=I=-16:TP=-1.5:LRA=11,"
                "adelay=120,"
                "apad,"
                f"atrim=duration={duration:.3f},"
                "aresample=48000"
            )
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(raw_mp3),
                    "-filter:a",
                    filter_chain,
                    "-ac",
                    "1",
                    "-c:a",
                    "pcm_s16le",
                    str(fitted_wav),
                ]
            )
            wav_files.append(fitted_wav)
            report.append(
                {
                    "segment": index,
                    "title": segment["title"],
                    "timeline_seconds": duration,
                    "raw_tts_seconds": round(raw_duration, 3),
                    "exact_tempo": round(exact_tempo, 4),
                    "applied_tempo": round(applied_tempo, 4),
                }
            )

        concat_file = temp_dir / "concat.txt"
        concat_file.write_text(
            "".join(f"file '{path.as_posix()}'\n" for path in wav_files),
            encoding="utf-8",
        )
        run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c:a",
                "libmp3lame",
                "-b:a",
                "128k",
                str(output_file),
            ]
        )

    srt_path = output_file.with_suffix(".srt")
    srt_parts: list[str] = []
    for index, segment in enumerate(segments, start=1):
        srt_parts.extend(
            [
                str(index),
                f"{seconds_to_srt(float(segment['start']))} --> {seconds_to_srt(float(segment['end']))}",
                segment["text"],
                "",
            ]
        )
    srt_path.write_text("\n".join(srt_parts), encoding="utf-8")

    report_path = output_file.with_name("generation_report.json")
    report_path.write_text(
        json.dumps(
            {
                "voice": chosen_voice,
                "rate": chosen_rate,
                "output_duration_seconds": round(probe_duration(output_file), 3),
                "segments": report,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Created {output_file}")
    print(f"Created {srt_path}")
    print(f"Created {report_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--segments",
        type=Path,
        default=Path("script/narration_segments.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/narration.mp3"),
    )
    parser.add_argument("--voice", default=None)
    parser.add_argument(
        "--rate",
        nargs="?",
        default=None,
        const=None,
        help=(
            "Speaking-rate adjustment for edge-tts. If --rate is provided "
            "without a value, the narration JSON default_rate is used."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("FFmpeg and ffprobe must be installed and available on PATH")
    asyncio.run(build_narration(args.segments, args.output, args.voice, args.rate))


if __name__ == "__main__":
    main()
