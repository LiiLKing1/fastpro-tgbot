from aiogram import Router, F
from aiogram.types import Message
from bot.utils.validators import is_valid_url, detect_platform
from bot.database.db import get_user_lang
from bot.utils.messages import get_msg
from bot.keyboards.inline import format_selection_keyboard, get_language_keyboard
from bot.services.downloader import DownloaderService
from bot.config import TEMP_DIR, ADMIN_IDS
import aiogram.exceptions

router = Router()
downloader = DownloaderService(temp_dir=TEMP_DIR)
URL_CACHE = {}

@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    text = message.text.strip()
    user_id = message.from_user.id
    user_lang = await get_user_lang(user_id)
    is_admin = user_id in ADMIN_IDS
    
    if text == "🏠 Bosh sahifa":
        await message.answer(get_msg(user_lang, 'welcome'))
        return
    elif text == "🔄 Yangilash":
        await message.answer(get_msg(user_lang, 'welcome'))
        return
    elif text == "🌐 Tilni o'zgartirish":
        await message.answer(get_msg(user_lang, 'select_lang'), reply_markup=get_language_keyboard())
        return
    elif text == "🆘 Yordam":
        await message.answer("Yordam uchun adminga murojaat qiling.")
        return
    elif text == "🛠 Admin panel" and is_admin:
        await message.answer("Admin panelga kirdingiz. /stats buyrug'ini tekshiring.")
        return

    if not is_valid_url(text):
        await message.answer(get_msg(user_lang, 'error_invalid_url'))
        return

    platform = detect_platform(text)
    status_msg = await message.answer(get_msg(user_lang, 'analyzing'))
    
    try:
        info = await downloader.extract_info(text)
        if not info:
            await status_msg.edit_text(get_msg(user_lang, 'error_private'))
            return
            
        title = info.get("title", "Unknown Title")
        URL_CACHE[user_id] = text
        
        reply_text = get_msg(user_lang, 'choose_format', title=title)
        keyboard = format_selection_keyboard(text, user_lang)
        
        await status_msg.edit_text(reply_text, reply_markup=keyboard)
        
    except Exception as e:
        print(f"Error extracting info: {e}")
        try:
            await status_msg.edit_text(get_msg(user_lang, 'error_private'))
        except aiogram.exceptions.TelegramBadRequest:
            pass
