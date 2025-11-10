import asyncio
import os
from typing import Dict

from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, InputMediaPhoto, FSInputFile
from aiogram.client.default import DefaultBotProperties

from .config import load_settings
from .utils import extract_url
from .downloader import extract_info, download_format, choose_best_format, normalize_twitter_url
from .db import init_db


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Menga X (Twitter) link yuboring — video, gif yoki rasmni yuklab beraman."
    )


@router.message(F.text)
async def handle_tweet(message: Message):
    url = extract_url(message.text or "")
    if not url:
        # Check if it contains twitter.com or x.com directly
        text = message.text or ""
        if "twitter.com" in text or "x.com" in text:
            url = text.strip()
        else:
            return  # Not a Twitter URL, ignore
    
    # Normalize URL
    url = normalize_twitter_url(url)
    
    loading = await message.answer("⏳ Tekshirilmoqda...")
    
    try:
        meta = await extract_info(url)
    except Exception as e:
        await loading.edit_text(f"⚠️ Xato: {e}")
        return
    
    media_type = meta["media_type"]
    info = meta["info"]
    
    if media_type == "video" or media_type == "gif":
        formats = meta["video_formats"]
        if not formats:
            await loading.edit_text("⚠️ Video formati topilmadi.")
            return
        
        best = choose_best_format(formats)
        await loading.edit_text(f"🎥 {media_type.upper()} aniqlandi. Yuklab olinmoqda...")
        
        try:
            settings = load_settings()
            filepath = await download_format(url, best["format_id"], settings.download_dir)
            
            size = os.path.getsize(filepath)
            
            # Telegram file size limit is ~50MB for videos
            if size < 49 * 1024 * 1024:
                await message.answer_video(
                    video=FSInputFile(filepath),
                    caption=f"🎥 {media_type.upper()}"
                )
            else:
                await message.answer_document(
                    document=FSInputFile(filepath),
                    caption=f"🎥 {media_type.upper()} (fayl juda katta)"
                )
            
            await loading.delete()
            await message.answer("✅ Media yuborildi.")
            
            # Clean up downloaded file
            try:
                os.remove(filepath)
            except Exception:
                pass
                
        except Exception as e:
            await loading.edit_text(f"❌ Yuklab bo'lmadi: {e}")
        return
    
    elif media_type == "photo":
        imgs = meta.get("media_urls") or []
        
        if not imgs:
            await loading.edit_text("⚠️ Hech qanday rasm topilmadi.")
            return
        
        await loading.edit_text("🖼 Rasm(lar) topildi, yuborilmoqda...")
        
        # Send up to 10 photos as media group
        try:
            if len(imgs) == 1:
                # Single photo
                await message.answer_photo(photo=imgs[0])
            else:
                # Multiple photos (media group, max 10)
                media_group = [InputMediaPhoto(media=img_url) for img_url in imgs[:10]]
                await message.answer_media_group(media_group)
            await loading.delete()
            await message.answer("✅ Rasmlar yuborildi.")
        except Exception as e:
            await loading.edit_text(f"❌ Rasmlarni yuborishda xato: {e}")
        return
    
    else:
        await loading.edit_text("🚫 Bu postda video yoki rasm mavjud emas.")


async def main():
    settings = load_settings()
    init_db()
    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
