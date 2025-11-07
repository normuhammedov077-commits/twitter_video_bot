from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import yt_dlp


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


QUALITY_ORDER = ["1080", "720", "480", "360", "240"]


def _create_ydl(params: Optional[Dict] = None) -> yt_dlp.YoutubeDL:
    base_opts = {
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "outtmpl": "%(id)s.%(ext)s",
        "noplaylist": True,
        # Work around rate limits/retries
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
    }
    if params:
        base_opts.update(params)
    return yt_dlp.YoutubeDL(base_opts)


def extract_variants(url: str) -> ExtractResult:
    with _create_ydl({"skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    # If this is a playlist-like (multi-video) post, select first entry for now
    if info.get("entries"):
        info = info["entries"][0]

    video_id = info.get("id") or "video"
    title = info.get("title") or ""
    uploader = info.get("uploader") or info.get("channel") or info.get("uploader_id")
    upload_date = info.get("upload_date")
    description = info.get("description")

    formats = info.get("formats", [])
    variants: List[VideoVariant] = []
    for f in formats:
        if not f.get("vcodec") or f.get("acodec") in ("none", None):
            # prefer muxed formats (contain audio)
            if f.get("acodec") in ("none", None):
                continue
        if f.get("vcodec") in ("none", None):
            continue

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
    )


def download_variant(url: str, format_id: str, output_dir: str, output_basename: Optional[str] = None) -> str:
    os.makedirs(output_dir, exist_ok=True)
    outtmpl = os.path.join(output_dir, f"{output_basename or '%(id)s'}.%(ext)s")
    opts = {
        "format": format_id,
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ],
    }
    with _create_ydl(opts) as ydl:
        result = ydl.extract_info(url, download=True)
        if result.get("requested_downloads"):
            filename = result["requested_downloads"][0]["filepath"]
        else:
            filename = ydl.prepare_filename(result)
    return filename



