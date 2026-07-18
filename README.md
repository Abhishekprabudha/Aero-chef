# AeroChef Automated Voice-over Video

This repository contains the compressed AeroChef screen recording, an expanded narration script aligned to the 6 minute 25 second demo, a Google Colab compression notebook, and two GitHub Actions workflows:

1. **Generate narration MP3** with a Microsoft neural voice through `edge-tts`.
2. **Build final narrated MP4** by combining the compressed video and the generated narration with FFmpeg.

## Included video

`assets/aerochef_demo_compressed.mp4`

- Runtime: **6:25.4**
- Resolution: **960 × 540**
- Frame rate: **15 fps**
- Codec: **H.264 / AVC**
- Audio: removed because the source audio track was silent
- Size: approximately **18.1 MiB**, safely below the 25 MiB browser-upload limit

## Repository structure

```text
.
├── .github/workflows/
│   ├── 01-generate-narration.yml
│   └── 02-build-final-video.yml
├── assets/
│   └── aerochef_demo_compressed.mp4
├── notebooks/
│   └── Compress_Video_Under_25MB.ipynb
├── script/
│   ├── AeroChef_6_Minute_Narration.md
│   └── narration_segments.json
├── scripts/
│   ├── build_final_video.py
│   ├── compress_video.py
│   └── generate_narration.py
├── artifacts/
├── output/
├── requirements.txt
└── README.md
```

## Upload to GitHub

1. Extract the ZIP on your computer.
2. Create a new GitHub repository.
3. Use **Add file → Upload files** and upload the extracted files and folders, not the ZIP itself.
4. Commit the files to the default branch.
5. Open the repository’s **Actions** tab and enable workflows when prompted.

The included MP4 is below the browser’s 25 MiB per-file limit. The final narrated video is delivered as a workflow artifact, so it does not need to be committed to the repository.

## Generate the narration MP3

1. Open **Actions**.
2. Select **01 - Generate narration MP3**.
3. Choose **Run workflow**.
4. Keep the defaults or change the voice and speaking rate.
5. When the run finishes, download the `narration-audio` artifact if you want the MP3 separately.

Defaults:

- Voice: `en-US-AvaNeural`
- Rate: `-10%`

The script is divided into timeline segments. Each TTS segment is normalized, time-fitted, padded to its visual window, and concatenated into one MP3 matching the video duration.

## Create the final narrated MP4

Workflow **02 - Build final narrated video** starts automatically after workflow 01 succeeds. It downloads the narration artifact, combines it with the compressed video, and publishes:

`aerochef-final-video/aerochef_demo_with_narration.mp4`

You can also run workflow 02 manually. Leave the run ID blank to use the latest successful narration run, or enter a specific workflow 01 run ID.

## Change the narration

Edit either of these files:

- `script/AeroChef_6_Minute_Narration.md` for the readable version.
- `script/narration_segments.json` for the version used by automation.

The automation reads the JSON file. Keep every segment’s `start`, `end`, and `text` fields valid, and keep the final end time at approximately `385.4` seconds.

## Change the voice

Enter another `edge-tts` Microsoft neural voice when launching workflow 01. Examples include:

- `en-US-AvaNeural`
- `en-US-AndrewNeural`
- `en-GB-SoniaNeural`
- `en-IN-NeerjaNeural`
- `en-IN-PrabhatNeural`

## Compress another video

Open `notebooks/Compress_Video_Under_25MB.ipynb` in Google Colab, upload the replacement MP4, run all cells, and download the compressed result. Rename it to:

`assets/aerochef_demo_compressed.mp4`

For local use with FFmpeg installed:

```bash
python scripts/compress_video.py input.mp4 assets/aerochef_demo_compressed.mp4 --target-mib 24
```

## Local execution

```bash
python -m pip install -r requirements.txt
python scripts/generate_narration.py
python scripts/build_final_video.py
```

FFmpeg and ffprobe must be installed and available on your system path.
