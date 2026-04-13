import os
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, FSInputFile
from bot.services.downloader import DownloaderService
from bot.database.db import log_download, get_user_lang, set_user_lang, remove_forced_channel, get_forced_channels
from bot.utils.messages import get_msg
from bot.config import TEMP_DIR
from bot.utils.validators import detect_platform
from bot.utils.force_sub import check_subscription
from bot.keyboards.inline import get_forced_channels_list_keyboard

router = Router()
downloader = DownloaderService(temp_dir=TEMP_DIR)
from bot.handlers.message import URL_CACHE

@router.callback_query(F.data.startswith("lang|"))
async def handle_lang_selection(callback: CallbackQuery):
    lang_choice = callback.data.split("|")[1]
    user_id = callback.from_user.id
    await set_user_lang(user_id, lang_choice)
    new_lang = await get_user_lang(user_id)
    await callback.message.edit_text(get_msg(new_lang, 'success'))
    await callback.answer()

@router.callback_query(F.data == "check_sub")
async def handle_check_sub(callback: CallbackQuery, bot: Bot):
    """Foydalanuvchi obunasini tekshirish"""
    user_id = callback.from_user.id
    is_subscribed = await check_subscription(bot, user_id)
    if is_subscribed:
        user_lang = await get_user_lang(user_id)
        await callback.message.edit_text("✅ Obuna tasdiqlandi! Endi botdan foydalanishingiz mumkin.")
        await callback.answer("✅ Obuna tasdiqlandi!", show_alert=True)
    else:
        await callback.answer("❌ Hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)

@router.callback_query(F.data.startswith("remove_fc|"))
async def handle_remove_forced_channel(callback: CallbackQuery):
    """Admin: Majburiy obuna kanalini o'chirish"""
    channel_db_id = int(callback.data.split("|")[1])
    await remove_forced_channel(channel_db_id)
    # Yangilangan ro'yxatni ko'rsatamiz
    channels = await get_forced_channels()
    if channels:
        await callback.message.edit_text(
            "📋 <b>Majburiy obuna ro'yxati</b>\n\nO'chirish uchun ustiga bosing:",
            reply_markup=get_forced_channels_list_keyboard(channels)
        )
    else:
        await callback.message.edit_text("📭 Majburiy obuna ro'yxati bo'sh.")
    await callback.answer("✅ O'chirildi!")

@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery):
    await callback.answer()

@router.callback_query(F.data.startswith("dl|"))
async def handle_format_selection(callback: CallbackQuery, bot: Bot):
    format_choice = callback.data.split("|")[1]
    user_id = callback.from_user.id
    user_lang = await get_user_lang(user_id)
    
    url = URL_CACHE.get(user_id)
    if not url:
        await callback.answer(get_msg(user_lang, 'error_invalid_url'), show_alert=True)
        return
        
    platform = detect_platform(url)
    
    await callback.message.edit_text(get_msg(user_lang, 'downloading'))
    
    try:
        file_path, title, media_type = await downloader.download(url, format_choice, user_id)
        
        if not file_path or not os.path.exists(file_path):
            await log_download(user_id, url, platform, 'failed')
            await callback.message.edit_text(get_msg(user_lang, 'error_failed'))
            return

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        await callback.message.edit_text(get_msg(user_lang, 'uploading'))
        
        input_file = FSInputFile(file_path)
        caption_text = get_msg(user_lang, 'caption', title=title, platform=platform, url=url)
        
        try:
            if file_size_mb > 50:
                # 50MB dan kattalarni document sifatida yuboramiz (2GB gacha)
                await callback.message.answer_document(input_file, caption=caption_text)
            elif media_type == "audio":
                await callback.message.answer_audio(input_file, caption=caption_text, title=title)
            elif media_type == "thumbnail":
                await callback.message.answer_photo(input_file, caption=caption_text)
            elif media_type == "video":
                await callback.message.answer_video(input_file, caption=caption_text)
            else:
                await callback.message.answer_document(input_file, caption=caption_text)
                
            await log_download(user_id, url, platform, 'success')
            await callback.message.delete()
            
        except Exception as e:
            logging.error(f"Telegram upload error: {e}")
            await log_download(user_id, url, platform, 'failed_upload')
            await callback.message.edit_text(get_msg(user_lang, 'error_failed'))
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        logging.error(f"Download service error: {e}")
        await log_download(user_id, url, platform, 'failed_exception')
        await callback.message.edit_text(get_msg(user_lang, 'error_failed'))
