"""Run the YouTube comment analysis pipeline for anyone in a private Telegram chat."""

import os
import re
import subprocess
import sys
import time
import argparse
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
REQUEST_TIMEOUT = 40
STAGES = ["main.py", "analyze.py", "report_pdf.py", "graphs.py"]


def extract_video_id(value: str) -> str | None:
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None
    host = parsed.netloc.lower().split(":", 1)[0]
    if parsed.scheme not in {"http", "https"}:
        return None
    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            parts = parsed.path.strip("/").split("/")
            video_id = parts[1] if len(parts) > 1 and parts[0] in {
                "shorts", "embed", "live"
            } else ""
    elif host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
    else:
        return None
    return video_id if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id) else None


def telegram(method: str, data: dict | None = None, files: dict | None = None,
             timeout: int = REQUEST_TIMEOUT) -> dict:
    response = requests.post(
        f"{API_BASE}/{method}", data=data, files=files, timeout=timeout
    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(result.get("description", "Telegram API error"))
    return result["result"]


def send_message(chat_id: int, text: str) -> None:
    telegram("sendMessage", {"chat_id": chat_id, "text": text})


def send_document(chat_id: int, path: Path, caption: str = "") -> None:
    with path.open("rb") as file:
        telegram(
            "sendDocument",
            {"chat_id": chat_id, "caption": caption},
            {"document": (path.name, file)},
        )


def send_photo(chat_id: int, path: Path) -> None:
    with path.open("rb") as file:
        telegram(
            "sendPhoto",
            {"chat_id": chat_id},
            {"photo": (path.name, file, "image/png")},
        )


def run_pipeline(video_url: str) -> None:
    environment = os.environ.copy()
    environment["YOUTUBE_VIDEO_URL"] = video_url
    for stage in STAGES:
        print(f"Running {stage} for {video_url}", flush=True)
        result = subprocess.run(
            [sys.executable, str(ROOT / stage)],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3600,
            check=False,
        )
        if result.stdout:
            print(result.stdout[-5000:], flush=True)
        if result.returncode:
            detail = (result.stderr or result.stdout or "No error details").strip()
            raise RuntimeError(f"{stage} failed (exit {result.returncode}): {detail[-2500:]}")


def process_video(chat_id: int, video_url: str) -> None:
    send_message(chat_id, 'Link received. Collecting comments, analyzing them, and generating charts. This may take a few minutes.')
    try:
        run_pipeline(video_url)
        summary = ROOT / "data" / "analysis_summary.txt"
        report = ROOT / "data" / "analysis.pdf"
        images = [
            ROOT / "data" / "graphs" / "sentiment_distribution.png",
            ROOT / "data" / "graphs" / "topic_distribution.png",
            ROOT / "data" / "graphs" / "engagement_by_sentiment.png",
        ]
        required = [summary, report, *images]
        missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError("Pipeline completed but output files are missing: " + ", ".join(missing))

        summary_text = summary.read_text(encoding="utf-8").strip()
        if not summary_text:
            raise RuntimeError("Pipeline completed but the summary is empty")
        send_message(chat_id, summary_text)
        for image in images:
            send_photo(chat_id, image)
        send_document(chat_id, report, 'Full report')
        send_message(chat_id, 'Done. All files have been sent.')
    except Exception as error:
        print(f"Pipeline error: {error}", file=sys.stderr, flush=True)
        message = 'Processing failed. Please try again later.'
        send_message(chat_id, message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local YouTube analysis Telegram bot.")
    parser.add_argument(
        "--print-user-id",
        action="store_true",
        help="Print Telegram user IDs from pending messages for diagnostics.",
    )
    args = parser.parse_args()
    if not BOT_TOKEN:
        print("Set TELEGRAM_BOT_TOKEN in .env", file=sys.stderr)
        return 1
    if args.print_user_id:
        try:
            updates = telegram(
                "getUpdates",
                {"timeout": 15, "allowed_updates": '["message"]'},
                timeout=25,
            )
            for update in updates:
                message = update.get("message", {})
                sender = message.get("from", {})
                if sender.get("id"):
                    print(f"{sender['id']}  {message.get('text', '')}")
            return 0
        except requests.RequestException as error:
            print(f"Could not read Telegram updates: {error}", file=sys.stderr)
            return 1
    print("Telegram bot is running. Send it a YouTube video URL.", flush=True)
    offset = None
    while True:
        try:
            payload = {"timeout": 25, "allowed_updates": '["message"]'}
            if offset is not None:
                payload["offset"] = offset
            updates = telegram("getUpdates", payload, timeout=35)
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message", {})
                chat = message.get("chat", {})
                chat_id = chat.get("id")
                text = (message.get("text") or "").strip()
                if chat.get("type") != "private":
                    continue
                if text in {"/start", "/help"}:
                    send_message(chat_id, 'Send a YouTube video link. I will collect the comments, analyze them, and send you the reports and charts.')
                    continue
                if not extract_video_id(text):
                    send_message(chat_id, 'Please send a valid YouTube video link, for example: https://www.youtube.com/watch?v=kC_v3ufGoGs')
                    continue
                process_video(chat_id, text)
        except requests.RequestException as error:
            print(f"Telegram connection error: {error}", file=sys.stderr, flush=True)
            time.sleep(5)
        except KeyboardInterrupt:
            print("Telegram bot stopped.", flush=True)
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
