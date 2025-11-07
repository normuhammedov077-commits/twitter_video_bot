import asyncio
import os
from typing import Dict

from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from .config import load_settings
from .utils import extract_url
from .downloader import extract_variants, download_variant
from .keyboards import build_quality_keyboard
from .cache import build_cache_key, get_cached_file_path, is_cached
from .db import init_db, record_stat


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Send me a Twitter/X post URL (https://x.com/... or https://twitter.com/...)\n"
        "I will fetch available video qualities."
    )


@router.message(F.text)
async def handle_url(message: Message):
    url = extract_url(message.text or "")
    if not url:
        await message.answer("Invalid or unsupported link.")
        return

    status = await message.answer("Checking the post...")
    try:
        result = await asyncio.to_thread(extract_variants, url)
    except Exception:
        await status.edit_text("An error occurred while fetching video info.")
        return

    if not result.variants:
        await status.edit_text("This post does not contain a video.")
        return

    # Build quality options
    options = [(v.format_id, v.quality_label) for v in result.variants]
    kb = build_quality_keyboard(result.video_id, options)

    caption_lines = []
    if result.uploader:
        caption_lines.append(f"Author: {result.uploader}")
    if result.title:
        caption_lines.append(f"Title: {result.title}")
    if result.upload_date:
        caption_lines.append(f"Date: {result.upload_date}")
    caption_lines.append("Choose video quality:")

    await status.edit_text("\n".join(caption_lines), reply_markup=kb)

    # Stash URL for this user/video session in memory
    ctx_key = (message.chat.id, result.video_id)
    CONTEXT[ctx_key] = {"url": url}


@router.callback_query(F.data.startswith("q:"))
async def handle_quality_choice(callback: CallbackQuery):
    try:
        _, video_id, format_id, label = (callback.data or "").split(":", 3)
    except Exception:
        await callback.answer("Invalid selection.", show_alert=True)
        return

    ctx_key = (callback.message.chat.id if callback.message else callback.from_user.id, video_id)
    ctx = CONTEXT.get(ctx_key)
    if not ctx:
        await callback.answer("Session expired. Send the URL again.", show_alert=True)
        return

    await callback.answer("Downloading...")
    url = ctx["url"]

    settings = load_settings()
    cache_key = build_cache_key(video_id, label)
    cached = is_cached(settings.download_dir, cache_key)
    file_path: str

    if cached:
        file_path = cached
    else:
        try:
            temp_path = await asyncio.to_thread(
                download_variant,
                url,
                format_id,
                settings.download_dir,
                cache_key,
            )
        except Exception:
            await callback.message.edit_text("An error occurred while downloading.")
            return
        # Ensure final path ends with .mp4 using our cache path helper
        file_path = get_cached_file_path(settings.download_dir, cache_key)
        if temp_path != file_path:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            os.replace(temp_path, file_path)

    # Send video
    from aiogram.types import FSInputFile
    await callback.message.answer_video(
        video=FSInputFile(file_path), caption=f"Quality: {label}", parse_mode=ParseMode.HTML
    )

    # Record stat (best-effort)
    try:
        record_stat(str(callback.from_user.id), url, video_id, label)
    except Exception:
        pass


CONTEXT: Dict[tuple[int, str], Dict] = {}


async def main():
    settings = load_settings()
    init_db()
    bot = Bot(settings.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

