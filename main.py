import os
import csv
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()
api_key = os.getenv("YOUTUBE_API_KEY")

youtube = build("youtube", "v3", developerKey=api_key)


video_id = "dQw4w9WgXcQ"
comments_count = 100  # Количество комментариев в каждом файле (1–100)


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