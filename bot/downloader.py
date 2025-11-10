from __future__ import annotations

import asyncio
import os
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import yt_dlp


def normalize_twitter_url(url: str) -> str:
    """Normalizes Twitter/X URLs (x.com, mobile.twitter.com, t.co redirects)"""
    url = url.strip()
    url = url.replace("mobile.twitter.com", "twitter.com")
    if "x.com/" in url and "twitter.com" not in url:
        url = url.replace("x.com/", "twitter.com/")
    if "t.co/" in url and "twitter.com" not in url:
        url = url.replace("t.co/", "twitter.com/")
    return url


@dataclass
class VideoVariant:
    format_id: str
    quality_label: str  # e.g., 480p / 720p / 1080p
    ext: str
    filesize: Optional[int]


@dataclass
class ExtractResult:
    video_id: str
    title: str
    uploader: Optional[str]
    upload_date: Optional[str]
    description: Optional[str]
    variants: List[VideoVariant]
    media_type: str  # "video", "gif", "photo", "none"


QUALITY_ORDER = ["1080", "720", "480", "360", "240"]


async def extract_info(url: str) -> Dict:
    """
    Extracts video/gif/image information from a Tweet.
    Returns a dictionary with media information.
    """
    loop = asyncio.get_event_loop()
    url = normalize_twitter_url(url)

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
    }

    def _extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    info = await loop.run_in_executor(None, _extract)

    if not info:
        raise ValueError("Could not read post or URL is invalid.")

    # Handle playlist-like entries
    if info.get("entries"):
        entries = [e for e in info["entries"] if e]
        if entries:
            info = entries[0]

    formats = info.get("formats") or []
    images = info.get("thumbnails") or []
    media_urls = info.get("media_urls") or []
    is_gif = info.get("is_animated_gif", False) or info.get("animated_gif", False)

    # Identify video formats
    video_formats = []
    for f in formats:
        if f.get("vcodec") and f.get("vcodec") != "none" and f.get("ext") in ("mp4", "webm"):
            video_formats.append(f)

    media_type = "none"
    if video_formats:
        media_type = "video"
    elif is_gif:
        media_type = "gif"
    elif images or media_urls:
        media_type = "photo"

    return {
        "info": info,
        "media_type": media_type,
        "video_formats": video_formats,
        "images": images,
        "media_urls": media_urls,
        "is_gif": is_gif,
    }


def choose_best_format(formats: List[Dict]) -> Dict:
    """Selects the best (largest) MP4 format"""
    if not formats:
        raise ValueError("Video format not found.")
    mp4s = [f for f in formats if f.get("ext") == "mp4"]
    candidates = mp4s if mp4s else formats
    sorted_formats = sorted(candidates, key=lambda x: (x.get("height") or 0), reverse=True)
    return sorted_formats[0]


async def extract_variants(url: str) -> ExtractResult:
    """
    Extracts video variants from a Twitter/X URL.
    Returns ExtractResult with available video qualities.
    """
    data = await extract_info(url)
    info = data["info"]
    video_formats = data["video_formats"]
    media_type = data["media_type"]

    video_id = info.get("id") or "video"
    title = info.get("title") or ""
    uploader = info.get("uploader") or info.get("channel") or info.get("uploader_id")
    upload_date = info.get("upload_date")
    description = info.get("description")

    # Convert formats to VideoVariant objects
    variants: List[VideoVariant] = []
    for f in video_formats:
        height = f.get("height")
        if not height:
            continue
        q_label = f"{height}p"
        variants.append(
            VideoVariant(
                format_id=str(f.get("format_id")),
                quality_label=q_label,
                ext=f.get("ext", "mp4"),
                filesize=f.get("filesize") or f.get("filesize_approx"),
            )
        )

    # Deduplicate by best per quality label
    best_by_label: Dict[str, VideoVariant] = {}
    for v in variants:
        existing = best_by_label.get(v.quality_label)
        if existing is None:
            best_by_label[v.quality_label] = v
            continue
        if (v.filesize or 0) > (existing.filesize or 0):
            best_by_label[v.quality_label] = v

    # Sort by our preferred order
    def sort_key(v: VideoVariant) -> Tuple[int, int]:
        num = ''.join([c for c in v.quality_label if c.isdigit()]) or "0"
        order_score = QUALITY_ORDER.index(num) if num in QUALITY_ORDER else len(QUALITY_ORDER)
        return (order_score, -(v.filesize or 0))

    final_variants = sorted(best_by_label.values(), key=sort_key)

    return ExtractResult(
        video_id=video_id,
        title=title,
        uploader=uploader,
        upload_date=upload_date,
        description=description,
        variants=final_variants,
        media_type=media_type,
    )


async def download_format(url: str, format_id: str, out_dir: Optional[str] = None, output_basename: Optional[str] = None) -> str:
    """Downloads the selected format"""
    loop = asyncio.get_event_loop()
    url = normalize_twitter_url(url)
    
    if out_dir is None:
        out_dir = tempfile.mkdtemp(prefix="xvid_")
    else:
        os.makedirs(out_dir, exist_ok=True)

    # Use output_basename if provided, otherwise use video ID
    if output_basename:
        outtmpl = os.path.join(out_dir, f"{output_basename}.%(ext)s")
    else:
        outtmpl = os.path.join(out_dir, "%(id)s.%(ext)s")
    
    ydl_opts = {
        "outtmpl": outtmpl,
        "format": format_id,
        "quiet": True,
        "no_warnings": True,
        "retries": 10,
        "fragment_retries": 10,
        "merge_output_format": "mp4",
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ],
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    await loop.run_in_executor(None, _download)
    
    # If output_basename was provided, the file should be named with that basename
    if output_basename:
        expected_path = os.path.join(out_dir, f"{output_basename}.mp4")
        if os.path.exists(expected_path):
            return expected_path
        # Fallback: try with other extensions
        for ext in ['.webm', '.mkv', '.mp4']:
            candidate = os.path.join(out_dir, f"{output_basename}{ext}")
            if os.path.exists(candidate):
                return candidate
    
    # Otherwise, find the downloaded file
    files = [f for f in os.listdir(out_dir) if f.endswith(('.mp4', '.webm', '.mkv'))]
    if not files:
        raise ValueError("Download failed.")
    
    return os.path.join(out_dir, files[0])


# Backward compatibility alias
async def download_variant(url: str, format_id: str, output_dir: str, output_basename: Optional[str] = None) -> str:
    """Backward compatible wrapper for download_format"""
    return await download_format(url, format_id, output_dir, output_basename)
