import re
from typing import Optional


X_URL_RE = re.compile(r"https?://(x|twitter|mobile\.twitter|t\.co)\.com?/[\w\-_/%.?=&]+", re.IGNORECASE)


def extract_url(text: str) -> Optional[str]:
    if not text:
        return None
    match = X_URL_RE.search(text.strip())
    return match.group(0) if match else None


def human_readable_filesize(num_bytes: int) -> str:
    step = 1024.0
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < step:
            return f"{size:.1f} {unit}"
        size /= step
    return f"{size:.1f} PB"



