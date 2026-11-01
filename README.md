# YouTube Comments Analytics

A Telegram bot that analyzes comments on YouTube videos. Send a video link in a private chat. The bot collects comments, uses a local Ollama model to analyze them, and sends the results back.

You receive:

- Two short summaries as text messages, one in Russian and one in English: 3–5 sentences about the comments, with no advice for the video creator.
- Three chart images: comment sentiment (positive, neutral, or negative), main topics, and average likes and replies by sentiment.
- Two full reports: `ru_analysis.pdf` in Russian and `en_analysis.pdf` in English.

The bot's messages are in English. The model first writes the report and summary in Russian. It then translates both into clear English at B1 level.

## Requirements

- Python 3.10 or newer.
- A YouTube Data API v3 key. Enable this API in Google Cloud.
- A Telegram bot created with `@BotFather` and its token.
- Ollama with the `qwen3:8b` model.
- An internet connection for YouTube and Telegram. With the default settings, Ollama analyzes the comments on your computer.

The PDF needs Arial fonts on Windows/macOS or DejaVu Sans fonts on Linux.

## Setup in VS Code on Windows

Open the project folder in VS Code. Select **Terminal → New Terminal**. Run all commands below from the project folder.

### 1. Set up Python

Create a virtual environment. This keeps the project's Python packages in one folder. Skip this command if `.venv` already exists:

```powershell
py -m venv .venv
```

Install the required packages:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

You do not need to activate the environment. These commands use Python from `.venv` directly.

### 2. Create the settings file

Create a file named `.env` in the project folder:

```dotenv
YOUTUBE_API_KEY=your_youtube_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Optional settings. These are the default values.
OLLAMA_MODEL=qwen3:8b
OLLAMA_URL=http://localhost:11434
```

Replace the example key and token with your own values. Keep them private. Git ignores the `.env` file.

You do not need to set a Telegram user ID. Anyone can use the bot in a private chat. The bot ignores group messages.

Each user can complete **3 free video analyses in total**. This limit does not
reset each day or after a restart. The bot counts an analysis after it sends
both summaries, all three charts, and both PDFs. Failed requests do not use an
attempt. Analyzing the same video again uses another attempt.

The bot saves counts by Telegram user ID in `data/user_limits.sqlite3`. Keep
this file to preserve the limits. Git ignores it. Requests beyond the limit
receive a message without starting analysis. Payments are not set up yet.

### 3. Start Ollama

Open Ollama from the Windows Start menu. Download the model before your first use:

```powershell
ollama pull qwen3:8b
```

Keep Ollama running while you use the bot.

## Start and stop the bot

Run this command in the VS Code terminal:

```powershell
.\.venv\Scripts\python.exe telegram_bot.py
```

Wait for this message:

```text
Telegram bot is running. Send it a YouTube video URL.
```

Then send a video link to your bot in Telegram.

The bot accepts `youtube.com/watch`, `youtu.be`, Shorts, embed, and live video links. For example:

```text
https://www.youtube.com/watch?v=hT_MAAwFLIc&t=109s
```

The time value `t=109s` does not change the analysis. The bot collects comments for the whole video.

Keep your computer, Ollama, and the terminal running. To stop the bot, click inside the terminal and press **Ctrl+C**. Run the same command to start it again.

### When several people send links

The bot handles one request at a time. It finishes the first request and sends the results before it starts the next one. Each person receives the results in their own chat.

The bot sends a start message only when it begins that person's request. People who are waiting do not get an immediate reply.

Run only one copy of the bot. All scripts use the same results folder.

## How it works

The bot runs these scripts in order:

| Script | What it does |
| --- | --- |
| `main.py` | Gets the latest and top comments from the YouTube API and saves two CSV files. |
| `analyze.py` | Uses Ollama to create Russian and English reports and summaries, plus chart data. |
| `report_pdf.py` | Converts both Markdown reports to PDF with support for Russian text. |
| `graphs.py` | Creates an HTML chart page and separate SVG and PNG images. |

After all steps finish successfully, the bot sends both summaries, the images, and both PDFs to the chat that sent the link. If a step fails, the bot sends an error message. You can find the error details in the terminal.

## Result files

The project saves results in `data/`. Each new run replaces these files. It does not keep a separate history for each user or video.

The link history is different: `data/analysis_history.txt` keeps all new starts.
It adds one line when comment collection starts, both from Telegram and from a
manual run. Each line has a number, the start date and time in `Asia/Jerusalem`
(with the UTC offset), and the video link. Numbers continue after a restart.
Repeated links get a new line. A start stays in the history even if a later step fails.
Requests that are still waiting are not recorded yet.

Example:

```text
(1) (2026-11-01 15:30:00 +0200) (https://www.youtube.com/watch?v=hT_MAAwFLIc&t=109s)
```

| Path | Contents |
| --- | --- |
| `data/analysis_history.txt` | A text history of video links and analysis start times. This file is not replaced. |
| `data/comments_latest.csv` | Comments sorted by time. |
| `data/comments_relevant.csv` | Top comments, sorted by YouTube relevance. |
| `data/analysis_summary.txt` | The Russian summary, sent as a text message. |
| `data/en_analysis_summary.txt` | The English summary, sent as a text message. |
| `data/analysis.md` | The full Russian report in Markdown format. |
| `data/en_analysis.md` | The full English report in Markdown format. |
| `data/ru_analysis.pdf` | The Russian PDF report sent to Telegram. |
| `data/en_analysis.pdf` | The English PDF report sent to Telegram. |
| `data/analysis_data.json` | Comment numbers, sentiment labels, and topics for the charts. |
| `data/graphs.html` | A chart page that you can open in a browser. |
| `data/graphs/` | Three charts, each saved as SVG and PNG. |

The CSV files use UTF-8 with BOM encoding and a semicolon (`;`) between columns. The columns are `number`, `comment`, `likes`, and `replies`.

The PNG files are `sentiment_distribution.png`, `topic_distribution.png`, and `engagement_by_sentiment.png`.

## Run without Telegram

You can run each step yourself in the same terminal. First, set the video link:

```powershell
$env:YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?v=hT_MAAwFLIc"
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe analyze.py
.\.venv\Scripts\python.exe report_pdf.py
.\.venv\Scripts\python.exe graphs.py
```

Run each command after the previous one finishes successfully. This saves the results on your computer. It does not send them to Telegram.

To create both PDFs or the charts again from existing data, run only the script you need.

You can change the model and the time limit for each Ollama request. The time limit is in seconds. English translation needs two more model requests, so each run takes longer:

```powershell
.\.venv\Scripts\python.exe analyze.py --model qwen3:8b --timeout 600
```

On macOS/Linux, create the environment with `python3 -m venv .venv`. Use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`. To choose a video for a manual run, use `export YOUTUBE_VIDEO_URL="https://www.youtube.com/watch?v=hT_MAAwFLIc"`.

## Limits

- The current setting is up to **20 comments in each group**. To change it, edit `comments_count` in `main.py`. You can use a value from 1 to 100.
- The script makes one API request for each group. It does not load more pages.
- It saves main comments only. It saves the number of replies, but not their text.
- The latest and top groups may include the same comments. The charts add both groups together without removing copies. The total can count the same comment twice.
- Comments must be available for the video. Problems with access, the API key, or the YouTube API usage limit stop the process.
- The `data/` folder must exist before you collect comments. It is already included in this project.
- The model can make mistakes. The charts show its labels for the collected comments. They do not show the views of all viewers.

## Common problems

| Problem | What to check |
| --- | --- |
| `Set TELEGRAM_BOT_TOKEN in .env` | Add your bot token to `.env` and save the file. |
| `ModuleNotFoundError` | Install the packages with the command in the setup section. |
| Cannot connect to Ollama | Start Ollama. Check `OLLAMA_URL` and make sure the model is downloaded. |
| YouTube API error | Check the key, API settings, usage limit, and whether comments are available. |
| `PDF fonts not found` | Make sure Arial is available, or install DejaVu Sans. |
| No reply to a new link | Check the terminal. The bot may still be working on another request. |

After you change `.env` or the code, stop the bot with **Ctrl+C** and start it again.
