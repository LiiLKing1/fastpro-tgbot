from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.messages import get_msg

def get_language_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang|uz"), 
         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang|en")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang|ru"), 
         InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang|uk")],
        [InlineKeyboardButton(text="🇹🇷 Türkçe", callback_data="lang|tr")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def format_selection_keyboard(url: str, lang: str) -> InlineKeyboardMarkup:
    buttons = []
    buttons.append([InlineKeyboardButton(text=get_msg(lang, "format_best"), callback_data="dl|bestvideo")])
    buttons.append([InlineKeyboardButton(text=get_msg(lang, "format_720"), callback_data="dl|720p")])
    buttons.append([InlineKeyboardButton(text=get_msg(lang, "format_360"), callback_data="dl|360p")])
    buttons.append([InlineKeyboardButton(text=get_msg(lang, "format_audio"), callback_data="dl|audio")])
    buttons.append([InlineKeyboardButton(text=get_msg(lang, "format_thumb"), callback_data="dl|thumbnail")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_forced_sub_keyboard(channels: list, lang: str = 'uz') -> InlineKeyboardMarkup:
    """Majburiy obuna bo'lmagan userga ko'rsatiladigan tugmalar"""
    buttons = []
    for ch in channels:
        chat_id = ch["chat_id"]
        title = ch["chat_title"] or ch["chat_id"]
        if chat_id.startswith("@"):
            url = f"https://t.me/{chat_id[1:]}"
        else:
            url = f"https://t.me/{chat_id}"
        buttons.append([InlineKeyboardButton(text=f"➡️ {title}", url=url)])
    buttons.append([InlineKeyboardButton(text=get_msg(lang, 'force_sub_check'), callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_forced_channels_list_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Admin uchun: majburiy obuna ro'yxatini ko'rsatish va o'chirish tugmalari"""
    buttons = []
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(
                text=f"❌ {ch['chat_title']} ({ch['chat_type']})",
                callback_data=f"remove_fc|{ch['id']}"
            )
        ])
    if not buttons:
        buttons.append([InlineKeyboardButton(text="📭 Ro'yxat bo'sh", callback_data="noop")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_help_reply_keyboard(user_id: int, lang: str = 'uz') -> InlineKeyboardMarkup:
    """Admin uchun: userga javob berish tugmasi"""
    buttons = [
        [InlineKeyboardButton(text=get_msg(lang, 'help_reply_btn'), callback_data=f"reply_user|{user_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
