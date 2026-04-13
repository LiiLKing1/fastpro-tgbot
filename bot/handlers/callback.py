import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from bot.services.downloader import DownloaderService
from bot.database.db import log_download, get_user_lang, set_user_lang
from bot.utils.messages import get_msg
from bot.config import TEMP_DIR
from bot.utils.validators import detect_platform

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

@router.callback_query(F.data.startswith("dl|"))
async def handle_format_selection(callback: CallbackQuery):
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
        if file_size_mb > 50:
            os.remove(file_path)
            await log_download(user_id, url, platform, 'failed_size')
            await callback.message.edit_text(get_msg(user_lang, 'error_size'))
            return

        await callback.message.edit_text(get_msg(user_lang, 'uploading'))
        
        input_file = FSInputFile(file_path)
        
        caption_text = get_msg(user_lang, 'caption', title=title, platform=platform, url=url)
        
        try:
            if media_type == "audio":
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
            print(f"Telegram upload error: {e}")
            await log_download(user_id, url, platform, 'failed_upload')
            await callback.message.edit_text(get_msg(user_lang, 'error_failed'))
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        print(f"Download service error: {e}")
        await log_download(user_id, url, platform, 'failed_exception')
        await callback.message.edit_text(get_msg(user_lang, 'error_failed'))
