# AsciiVideo Tool

Ultra High Definition Video to ASCII Tool.

This tool converts standard video files into ASCII art representations. It can output to a proprietary `.asvid` format or back to a standard video format with ASCII visuals.

## Features (Planned)

*   Convert video files (e.g., MP4, AVI) to ASCII.
*   Adjustable ASCII output dimensions (width, height in characters).
*   Customizable ASCII character ramps.
*   Handles audio:
    *   Extracts audio from the original video.
    *   Can re-attach audio to the ASCII-rendered standard video output.
    *   Stores audio reference in `.asvid` format.
*   Output formats:
    *   `.asvid`: A custom format for storing ASCII frames and metadata.
    *   Standard video (e.g., MP4): ASCII frames rendered as images and compiled into a video.
*   Command-line interface for ease of use.
*   Efficient processing with FFmpeg.

## Prerequisites

*   Python 3.x
*   FFmpeg and FFprobe:
    *   The tool expects FFmpeg binaries at specific paths (currently hardcoded for development but will be packaged).
    *   FFMPEG_PATH = r"C:\Users\artur\Desktop\Asciiv2\ffmpeg\ffmpeg.exe"
    *   FFPROBE_PATH = r"C:\Users\artur\Desktop\Asciiv2\ffmpeg\ffprobe.exe"
*   Python libraries (see `requirements.txt`)

## Setup (Development)

1.  Clone the repository.
2.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Ensure FFmpeg and FFprobe are available at the configured paths or update paths in `asciivideo/video_utils.py`.

## Usage (Planned CLI)

```bash
python -m asciivideo.main <input_video_path> -o <output_path> [options]
```

Example:
```bash
python -m asciivideo.main my_video.mp4 -o my_ascii_video.asvid --format asvid --width 120
python -m asciivideo.main my_video.mp4 -o my_rendered_ascii.mp4 --format mp4 --width 120 --audio keep
```

## Project Structure

```
asciivideo/
├── asciivideo/           # Main package
│   ├── __init__.py
│   ├── main.py           # CLI entry point
│   ├── converter.py      # Core ASCII conversion logic
│   ├── video_utils.py    # FFmpeg/video utilities
│   ├── audio_utils.py    # Audio utilities
│   └── formats.py        # .asvid and video output generation
├── tests/                # Unit tests
│   └── ...
├── README.md             # This file
└── requirements.txt      # Python dependencies
```

## `.asvid` Format

*   **Magic Number**: `ASVID01` (followed by newline)
*   **Header**: JSON object containing metadata (e.g., dimensions, FPS, audio reference), terminated by `%%HEADER_END%%\n`.
*   **Frame Data**: ASCII frames, each followed by `\nASCIIVIDEO_FRAME_DELIMITER\n`.

(More details to be added as the format is finalized.)
```
