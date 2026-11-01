import os
import csv
import re
from urllib.parse import parse_qs, urlparse
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()
api_key = os.getenv("YOUTUBE_API_KEY")

youtube = build("youtube", "v3", developerKey=api_key)


video_id = os.getenv(
    "YOUTUBE_VIDEO_URL",
    "https://www.youtube.com/watch?v=kC_v3ufGoGs",
)
comments_count = 20  # Количество комментариев в каждом файле (1–100)


def extract_video_id(value):
    """Accept a YouTube video ID or a standard YouTube video URL."""
    value = value.strip()
    if "://" not in value:
        video_id_value = value
    else:
        parsed = urlparse(value)
        host = parsed.netloc.lower().split(":", 1)[0]
        if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            if parsed.path == "/watch":
                video_id_value = parse_qs(parsed.query).get("v", [""])[0]
            else:
                parts = parsed.path.strip("/").split("/")
                video_id_value = parts[1] if len(parts) > 1 and parts[0] in {
                    "shorts", "embed", "live"
                } else ""
        elif host in {"youtu.be", "www.youtu.be"}:
            video_id_value = parsed.path.strip("/").split("/")[0]
        else:
            video_id_value = ""

    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id_value):
        raise ValueError("Enter a valid 11-character YouTube video ID or video URL")
    return video_id_value


video_id = extract_video_id(video_id)


def save_comments(order, filename):
    response = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=comments_count,
        order=order,
        textFormat="plainText"
    ).execute()

    with open(filename, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")

        writer.writerow([
            "number",
            "comment",
            "likes",
            "replies"
        ])

        for number, item in enumerate(response.get("items", []), start=1):
            thread = item["snippet"]
            comment = thread["topLevelComment"]["snippet"]

            writer.writerow([
                number,
                comment["textDisplay"],
                comment["likeCount"],
                thread["totalReplyCount"]
            ])

    print(f"Save: {os.path.abspath(filename)}")


save_comments("time", "data/comments_latest.csv")
save_comments("relevance", "data/comments_relevant.csv")
