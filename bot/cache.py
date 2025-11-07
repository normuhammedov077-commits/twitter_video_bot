import hashlib
import os
from typing import Optional


def build_cache_key(video_id: str, quality_label: str) -> str:
    base = f"{video_id}:{quality_label}".encode("utf-8")
    return hashlib.sha256(base).hexdigest()[:32]


def get_cached_file_path(cache_dir: str, cache_key: str) -> str:
    return os.path.join(cache_dir, f"{cache_key}.mp4")


def is_cached(cache_dir: str, cache_key: str) -> Optional[str]:
    file_path = get_cached_file_path(cache_dir, cache_key)
    return file_path if os.path.exists(file_path) else None



