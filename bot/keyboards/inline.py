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
