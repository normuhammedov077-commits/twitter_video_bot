# X (Twitter) Video Downloader Bot

A Telegram bot that downloads videos from X (Twitter) via a shared post URL, lets users choose available quality (e.g., 480p/720p/1080p), downloads with caching, and sends the video back.

## Features
- Paste an `https://x.com/...` or `https://twitter.com/...` link
- Detect available video qualities and choose one
- Download via `yt-dlp` and send as Telegram video
- Includes post author, text, and date in the caption (when available)
- Simple file-based caching to avoid re-downloading the same file
- (Optional) Stats scaffolding with SQLite

## Requirements
- Python 3.10+
- Telegram bot token from BotFather

## Setup
1. Create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set environment variables (use your real token):

```bash
export BOT_TOKEN="123456:ABC..."
# Optional: customize download/cache directory
export DOWNLOAD_DIR="/tmp/twitter_bot_downloads"
```

4. Run the bot:

```bash
python -m bot.main
```

## Usage
- Send a valid X (Twitter) post URL to the bot chat
- If multiple videos are present, the bot will list each; otherwise it shows quality options
- Choose the desired quality; the bot downloads and sends the video

## Notes
- Telegram file size limits apply (often ~50 MB for standard bots). Very large videos may fail to send.
- yt-dlp changes and X platform policies can affect availability of formats. If formats are missing, try again later.

## Project Structure
```
/Users/muhammad/twitter_video_bot
  ├─ requirements.txt
  └─ bot/
     ├─ __init__.py
     ├─ config.py
     ├─ main.py
     ├─ downloader.py
     ├─ keyboards.py
     ├─ utils.py
     ├─ cache.py
     └─ db.py  # optional stats scaffolding
```

## Security
- Do not commit your `BOT_TOKEN` to source control.
- If you deploy to a VPS, store secrets in environment variables or a secrets manager.

## License
MIT



