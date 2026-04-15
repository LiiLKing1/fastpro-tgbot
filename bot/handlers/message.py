from aiogram import Router, F, Bot
from aiogram.types import Message
from bot.utils.validators import is_valid_url, detect_platform
from bot.database.db import get_user_lang, get_stats, get_all_user_ids, add_forced_channel, get_forced_channels
from bot.utils.messages import get_msg, LANGUAGES
from bot.keyboards.inline import format_selection_keyboard, get_language_keyboard, get_forced_channels_list_keyboard, get_help_reply_keyboard
from bot.keyboards.reply import get_admin_panel_menu, get_main_menu
from bot.services.downloader import DownloaderService
from bot.config import TEMP_DIR, ADMIN_IDS
from bot.utils.force_sub import check_subscription
import aiogram.exceptions
import asyncio
import logging

router = Router()
downloader = DownloaderService(temp_dir=TEMP_DIR)
URL_CACHE = {}

# Userlar holati: "help_mode", "broadcast_mode", "reply_user_mode:{target_id}", etc.
USER_STATE = {}


async def show_format_picker(message: Message, user_lang: str, user_id: int, url: str, title: str) -> None:
    URL_CACHE[user_id] = url
    reply_text = get_msg(user_lang, 'choose_format', title=title)
    keyboard = format_selection_keyboard(url, user_lang)
    await message.edit_text(reply_text, reply_markup=keyboard)

@router.message(F.text)
async def handle_text_message(message: Message, bot: Bot) -> None:
    text = message.text.strip()
    user_id = message.from_user.id
    user_lang = await get_user_lang(user_id)
    is_admin = user_id in ADMIN_IDS

    state = USER_STATE.get(user_id)

    # ============ Admin: Reply to user mode ============
    if state and state.startswith("reply_user_mode:") and is_admin:
        target_id = int(state.split(":")[1])
        USER_STATE.pop(user_id, None)
        
        target_lang = await get_user_lang(target_id)
        try:
            await bot.send_message(target_id, get_msg(target_lang, 'help_reply_received', text=text))
            await message.answer(get_msg(user_lang, 'help_reply_sent'), reply_markup=get_admin_panel_menu(user_lang))
        except Exception as e:
            await message.answer(f"❌ Xatolik: {e}")
        return

    # ============ Admin: Broadcast rejimi ============
    if state == "broadcast_mode" and is_admin:
        if text == get_msg(user_lang, 'btn_back'):
            USER_STATE.pop(user_id, None)
            await message.answer(get_msg(user_lang, 'admin_panel_title'), reply_markup=get_admin_panel_menu(user_lang))
            return

        USER_STATE.pop(user_id, None)
        all_ids = await get_all_user_ids()
        success = 0
        failed = 0
        
        status_msg = await message.answer(get_msg(user_lang, 'broadcast_progress', current=0, total=len(all_ids)))

        for uid in all_ids:
            try:
                await bot.send_message(uid, text)
                success += 1
            except Exception:
                failed += 1
            
            if (success + failed) % 20 == 0:
                try:
                    await status_msg.edit_text(get_msg(user_lang, 'broadcast_progress', current=success+failed, total=len(all_ids)))
                except Exception:
                    pass
            await asyncio.sleep(0.05)

        await status_msg.edit_text(get_msg(user_lang, 'broadcast_done', success=success, failed=failed, total=len(all_ids)))
        return

    # ============ Admin: Kanal/Guruh/Bot qo'shish rejimi ============
    if state and state.startswith("add_") and is_admin:
        if text == get_msg(user_lang, 'btn_back'):
            USER_STATE.pop(user_id, None)
            await message.answer(get_msg(user_lang, 'admin_panel_title'), reply_markup=get_admin_panel_menu(user_lang))
            return

        chat_type_map = {"add_channel": "channel", "add_group": "group", "add_bot": "bot"}
        chat_type = chat_type_map.get(state, "channel")
        USER_STATE.pop(user_id, None)

        chat_id_input = text.strip()
        chat_title = chat_id_input
        try:
            chat_info = await bot.get_chat(chat_id_input)
            chat_title = chat_info.title or chat_info.first_name or chat_id_input
        except Exception:
            pass

        await add_forced_channel(chat_id_input, chat_title, chat_type)
        await message.answer(
            get_msg(user_lang, 'channel_added', title=chat_title, chat_type=chat_type),
            reply_markup=get_admin_panel_menu(user_lang)
        )
        return

    # ============ User: Yordam rejimi (adminga xabar yuborish) ============
    if state == "help_mode":
        if text == get_msg(user_lang, 'btn_back'):
            USER_STATE.pop(user_id, None)
            await message.answer(get_msg(user_lang, 'welcome'), reply_markup=get_main_menu(is_admin, user_lang))
            return

        USER_STATE.pop(user_id, None)
        user = message.from_user
        user_info = f"{user.first_name or ''} {user.last_name or ''}"
        if user.username:
            user_info += f" (@{user.username})"
            
        admin_info_html = f"👤 <b>{user_info}</b>\n🆔 ID: <code>{user_id}</code>"

        admin_text = get_msg(user_lang, 'help_admin_msg', user_info=admin_info_html, text=text)

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id, 
                    admin_text, 
                    reply_markup=get_help_reply_keyboard(user_id, await get_user_lang(admin_id))
                )
            except Exception:
                pass

        await message.answer(get_msg(user_lang, 'help_sent'), reply_markup=get_main_menu(is_admin, user_lang))
        return

    # ============ Navigatsiya tugmalari (Ko'p tilli) ============
    
    # Tugma matnlarini barcha tillarda tekshirish (agar user tilini o'zgartirgan bo'lsa butonnlar eskirishi mumkin)
    all_home = [LANGUAGES[l]['btn_home'] for l in LANGUAGES]
    all_refresh = [LANGUAGES[l]['btn_refresh'] for l in LANGUAGES]
    all_lang = [LANGUAGES[l]['btn_lang'] for l in LANGUAGES]
    all_help = [LANGUAGES[l]['btn_help'] for l in LANGUAGES]
    all_admin = [LANGUAGES[l]['btn_admin'] for l in LANGUAGES]
    all_back = [LANGUAGES[l]['btn_back'] for l in LANGUAGES]
    
    if text in all_home:
        await message.answer(get_msg(user_lang, 'welcome'), reply_markup=get_main_menu(is_admin, user_lang))
        return
    elif text in all_refresh:
        await message.answer(get_msg(user_lang, 'welcome'), reply_markup=get_main_menu(is_admin, user_lang))
        return
    elif text in all_lang:
        await message.answer(get_msg(user_lang, 'select_lang'), reply_markup=get_language_keyboard())
        return
    elif text in all_help:
        USER_STATE[user_id] = "help_mode"
        # Back tugmasi bilan menu yuboramiz
        back_kb = [[KeyboardButton(text=get_msg(user_lang, 'btn_back'))]]
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        await message.answer(get_msg(user_lang, 'help_prompt'), reply_markup=ReplyKeyboardMarkup(keyboard=back_kb, resize_keyboard=True))
        return
    elif text in all_admin and is_admin:
        await message.answer(get_msg(user_lang, 'admin_panel_title'), reply_markup=get_admin_panel_menu(user_lang))
        return
    elif text in all_back:
        USER_STATE.pop(user_id, None)
        await message.answer(get_msg(user_lang, 'welcome'), reply_markup=get_main_menu(is_admin, user_lang))
        return

    # ============ Admin panel funksiyalari ============
    if is_admin:
        all_stats = [LANGUAGES[l]['btn_stats'] for l in LANGUAGES]
        all_broadcast = [LANGUAGES[l]['btn_broadcast'] for l in LANGUAGES]
        all_add_chan = [LANGUAGES[l]['btn_add_channel'] for l in LANGUAGES]
        all_add_group = [LANGUAGES[l]['btn_add_group'] for l in LANGUAGES]
        all_add_bot = [LANGUAGES[l]['btn_add_bot'] for l in LANGUAGES]
        all_chan_list = [LANGUAGES[l]['btn_channel_list'] for l in LANGUAGES]

        if text in all_stats:
            stats = await get_stats()
            await message.answer(get_msg(
                user_lang, 'stats_text', 
                total_users=stats['total_users'], today_users=stats['today_users'],
                total_downloads=stats['total_downloads'], today_downloads=stats['today_downloads'],
                failed_downloads=stats['failed_downloads'], most_used_platform=stats['most_used_platform']
            ))
            return
        elif text in all_broadcast:
            USER_STATE[user_id] = "broadcast_mode"
            ids = await get_all_user_ids()
            await message.answer(get_msg(user_lang, 'broadcast_prompt', count=len(ids)))
            return
        elif text in all_add_chan:
            USER_STATE[user_id] = "add_channel"
            await message.answer(get_msg(user_lang, 'add_channel_prompt'))
            return
        elif text in all_add_group:
            USER_STATE[user_id] = "add_group"
            await message.answer(get_msg(user_lang, 'add_group_prompt'))
            return
        elif text in all_add_bot:
            USER_STATE[user_id] = "add_bot"
            await message.answer(get_msg(user_lang, 'add_bot_prompt'))
            return
        elif text in all_chan_list:
            channels = await get_forced_channels()
            if not channels:
                await message.answer(get_msg(user_lang, 'channel_list_empty'))
            else:
                await message.answer(get_msg(user_lang, 'channel_list_title'), reply_markup=get_forced_channels_list_keyboard(channels))
            return

    # ============ URL tekshiruvi ============
    if not is_valid_url(text):
        await message.answer(get_msg(user_lang, 'error_invalid_url'))
        return

    # Majburiy obuna (Adminlar uchun kerak emas)
    if not is_admin:
        is_subscribed = await check_subscription(bot, user_id)
        if not is_subscribed:
            return

    platform = detect_platform(text)
    status_msg = await message.answer(get_msg(user_lang, 'analyzing'))
    
    try:
        info = await downloader.extract_info(text)
        if not info:
            if platform == 'Instagram':
                await show_format_picker(status_msg, user_lang, user_id, text, platform)
            else:
                await status_msg.edit_text(get_msg(user_lang, 'error_private'))
            return
            
        title = info.get("title") or platform
        await show_format_picker(status_msg, user_lang, user_id, text, title)
        
    except Exception as e:
        logging.error(f"Error extracting info for {platform}: {e}")
        try:
            if platform == 'Instagram':
                await show_format_picker(status_msg, user_lang, user_id, text, platform)
            else:
                await status_msg.edit_text(get_msg(user_lang, 'error_private'))
        except aiogram.exceptions.TelegramBadRequest:
            pass
