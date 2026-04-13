from aiogram import Router, filters, F
from aiogram.types import Message
from bot.database.db import get_stats, add_user, get_user_lang, user_exists
from bot.keyboards.inline import get_language_keyboard
from bot.keyboards.reply import get_main_menu
from bot.config import ADMIN_IDS
from bot.utils.messages import get_msg

router = Router()

@router.message(filters.CommandStart())
async def command_start_handler(message: Message) -> None:
    already_exists = await user_exists(message.from_user.id)
    
    await add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    user_lang = await get_user_lang(message.from_user.id)
    is_admin = message.from_user.id in ADMIN_IDS
    
    # Faqat yangi user bo'lsagina til tanlashni ko'rsatamiz
    if not already_exists:
        await message.answer(get_msg(user_lang, 'select_lang'), reply_markup=get_language_keyboard())
    else:
        await message.answer(get_msg(user_lang, 'welcome'), reply_markup=get_main_menu(is_admin, user_lang))

@router.message(filters.Command("stats"))
async def command_stats_handler(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
        
    stats = await get_stats()
    user_lang = await get_user_lang(message.from_user.id)
    
    text = get_msg(
        user_lang, 
        'stats_text', 
        total_users=stats['total_users'],
        today_users=stats['today_users'],
        total_downloads=stats['total_downloads'],
        today_downloads=stats['today_downloads'],
        failed_downloads=stats['failed_downloads'],
        most_used_platform=stats['most_used_platform']
    )
    await message.answer(text)
