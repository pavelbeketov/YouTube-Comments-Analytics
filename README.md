# YouTube Comments Analytics

This small Python project gets comments from a YouTube video and saves them as CSV files. It gets up to 100 comments in two orders: by time (`latest`) and by relevance (`relevant`).

## Requirements

- Python 3.10 or newer
- A YouTube Data API v3 key. Enable the YouTube Data API v3 in Google Cloud.

## Setup

1. Clone the repository and open the project folder.
2. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   On macOS or Linux, use: `source .venv/bin/activate`.

3. Install the packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a file named `.env` in the project folder. Add your API key:

   ```dotenv
   YOUTUBE_API_KEY=your_api_key
   ```

Keep your API key private. The `.env` file is ignored by Git.

## Run the project

Run this command from the project folder:

```bash
python main.py
```

The script uses the video ID in `main.py`. It replaces these files:

- `data/comments_latest.csv` — comments sorted by time;
- `data/comments_relevant.csv` — comments sorted by relevance.

The CSV files use UTF-8 with BOM encoding and a semicolon (`;`) between columns. They have these columns: `number` (row number), `comment` (comment text), `likes` (like count), and `replies` (number of replies).

To use another video, change `video_id` in `main.py` to the ID from the video URL. Change `comments_count` to set the number of comments. The YouTube API allows 1 to 100 results in one request.

## Limits

- The script makes one request for each order. It does not load more pages, so each file has up to 100 comments.
- It saves top-level comments only. It saves the number of replies, but not the reply text.
- Comments must be turned on for the video. API problems, such as a wrong key or a quota limit, stop the script.
- The `data` folder must exist before you run the script.
