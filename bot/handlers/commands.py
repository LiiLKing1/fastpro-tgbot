from aiogram import Router, filters, F
from aiogram.types import Message
from bot.database.db import get_stats, add_user, get_user_lang
from bot.keyboards.inline import get_language_keyboard
from bot.keyboards.reply import get_main_menu
from bot.config import ADMIN_IDS
from bot.utils.messages import get_msg

router = Router()

@router.message(filters.CommandStart())
async def command_start_handler(message: Message) -> None:
    await add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    user_lang = await get_user_lang(message.from_user.id)
    is_admin = message.from_user.id in ADMIN_IDS
    
    await message.answer(get_msg(user_lang, 'welcome'), reply_markup=get_main_menu(is_admin))
    await message.answer(get_msg(user_lang, 'select_lang'), reply_markup=get_language_keyboard())

@router.message(filters.Command("stats"))
async def command_stats_handler(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
        
    stats = await get_stats()
    text = (
        f"📊 <b>Bot Statistics</b>\n\n"
        f"👥 Total Users: {stats['total_users']}\n"
        f"📥 Total Downloads: {stats['total_downloads']}\n"
        f"❌ Failed Downloads: {stats['failed_downloads']}\n"
        f"🏆 Most Used Platform: {stats['most_used_platform']}"
    )
    await message.answer(text)
