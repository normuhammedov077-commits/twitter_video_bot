import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Settings:
    bot_token: str
    download_dir: str


def load_settings() -> Settings:
    # Load environment variables from .env if present
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is required")

    download_dir = os.getenv("DOWNLOAD_DIR", os.path.expanduser("~/.twitter_bot_downloads"))
    os.makedirs(download_dir, exist_ok=True)
    return Settings(bot_token=token, download_dir=download_dir)

