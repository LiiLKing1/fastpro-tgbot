from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu(is_admin: bool = False):
    keyboard = [
        [KeyboardButton(text="🏠 Bosh sahifa"), KeyboardButton(text="🔄 Yangilash")],
        [KeyboardButton(text="🌐 Tilni o'zgartirish"), KeyboardButton(text="🆘 Yordam")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="🛠 Admin panel")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
