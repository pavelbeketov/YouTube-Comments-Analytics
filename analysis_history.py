"""Keep a text history of video analysis starts."""

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
HISTORY_FILE = ROOT / "data" / "analysis_history.txt"


def record_analysis_start(video_url: str, path: Path | None = None) -> None:
    path = path if path is not None else HISTORY_FILE
    video_url = video_url.strip()
    if not video_url or "\n" in video_url or "\r" in video_url:
        raise ValueError("History requires a single-line video URL")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Read the existing numbers each time so numbering survives restarts.
    with path.open("a+", encoding="utf-8", newline="") as file:
        file.seek(0)
        content = file.read()
        numbers = [int(value) for value in re.findall(r"^\((\d+)\) ", content, re.MULTILINE)]
        number = max(numbers, default=0) + 1
        timestamp = datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%Y-%m-%d %H:%M:%S %z")
        if content and not content.endswith("\n"):
            file.write("\n")
        file.write(f"({number}) ({timestamp}) ({video_url})\n")
