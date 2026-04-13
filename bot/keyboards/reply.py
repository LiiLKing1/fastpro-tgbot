from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu(is_admin: bool = False):
    keyboard = [
        [KeyboardButton(text="🏠 Bosh sahifa"), KeyboardButton(text="🔄 Yangilash")],
        [KeyboardButton(text="🌐 Tilni o'zgartirish"), KeyboardButton(text="🆘 Yordam")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="🛠 Admin panel")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_admin_panel_menu():
    keyboard = [
        [KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📢 Barcha userlarga elon")],
        [KeyboardButton(text="➕ Kanal qo'shish"), KeyboardButton(text="➕ Guruh qo'shish")],
        [KeyboardButton(text="➕ Bot qo'shish")],
        [KeyboardButton(text="📋 Majburiy obuna ro'yxati")],
        [KeyboardButton(text="🔙 Orqaga")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
