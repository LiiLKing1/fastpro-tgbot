from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from bot.utils.messages import get_msg

def get_main_menu(is_admin: bool = False, lang: str = 'uz'):
    keyboard = [
        [KeyboardButton(text=get_msg(lang, 'btn_home')), KeyboardButton(text=get_msg(lang, 'btn_refresh'))],
        [KeyboardButton(text=get_msg(lang, 'btn_lang')), KeyboardButton(text=get_msg(lang, 'btn_help'))],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text=get_msg(lang, 'btn_admin'))])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_admin_panel_menu(lang: str = 'uz'):
    keyboard = [
        [KeyboardButton(text=get_msg(lang, 'btn_stats'))],
        [KeyboardButton(text=get_msg(lang, 'btn_broadcast'))],
        [KeyboardButton(text=get_msg(lang, 'btn_add_channel')), KeyboardButton(text=get_msg(lang, 'btn_add_group'))],
        [KeyboardButton(text=get_msg(lang, 'btn_add_bot'))],
        [KeyboardButton(text=get_msg(lang, 'btn_channel_list'))],
        [KeyboardButton(text=get_msg(lang, 'btn_back'))],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
