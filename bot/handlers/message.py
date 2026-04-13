from aiogram import Router, F, Bot
from aiogram.types import Message
from bot.utils.validators import is_valid_url, detect_platform
from bot.database.db import get_user_lang, get_stats, get_all_user_ids, add_forced_channel, get_forced_channels
from bot.utils.messages import get_msg
from bot.keyboards.inline import format_selection_keyboard, get_language_keyboard, get_forced_channels_list_keyboard
from bot.keyboards.reply import get_admin_panel_menu, get_main_menu
from bot.services.downloader import DownloaderService
from bot.config import TEMP_DIR, ADMIN_IDS
import aiogram.exceptions
import asyncio
import logging

router = Router()
downloader = DownloaderService(temp_dir=TEMP_DIR)
URL_CACHE = {}

# Userlar holati: "help_mode" yoki "broadcast_mode" yoki "add_channel/group/bot"
USER_STATE = {}

@router.message(F.text)
async def handle_text_message(message: Message, bot: Bot) -> None:
    text = message.text.strip()
    user_id = message.from_user.id
    user_lang = await get_user_lang(user_id)
    is_admin = user_id in ADMIN_IDS

    # ============ Admin: Broadcast rejimi ============
    state = USER_STATE.get(user_id)

    if state == "broadcast_mode" and is_admin:
        USER_STATE.pop(user_id, None)
        all_ids = await get_all_user_ids()
        success = 0
        failed = 0
        status_msg = await message.answer(f"📢 Xabar yuborilmoqda... 0/{len(all_ids)}")

        for uid in all_ids:
            try:
                await bot.send_message(uid, text)
                success += 1
            except Exception:
                failed += 1
            # Har 20 tadan keyin status yangilaymiz
            if (success + failed) % 20 == 0:
                try:
                    await status_msg.edit_text(f"📢 Xabar yuborilmoqda... {success + failed}/{len(all_ids)}")
                except Exception:
                    pass
            await asyncio.sleep(0.05)  # flood limitdan himoya

        await status_msg.edit_text(
            f"📢 <b>Broadcast yakunlandi!</b>\n\n"
            f"✅ Yuborildi: {success}\n"
            f"❌ Xatolik: {failed}\n"
            f"👥 Jami: {len(all_ids)}"
        )
        return

    # ============ Admin: Kanal/Guruh/Bot qo'shish rejimi ============
    if state and state.startswith("add_") and is_admin:
        chat_type_map = {"add_channel": "channel", "add_group": "group", "add_bot": "bot"}
        chat_type = chat_type_map.get(state, "channel")
        USER_STATE.pop(user_id, None)

        chat_id_input = text.strip()
        # chat_title ni aniqlashga urinamiz
        chat_title = chat_id_input
        try:
            chat_info = await bot.get_chat(chat_id_input)
            chat_title = chat_info.title or chat_info.first_name or chat_id_input
        except Exception:
            pass

        await add_forced_channel(chat_id_input, chat_title, chat_type)
        await message.answer(
            f"✅ <b>{chat_title}</b> ({chat_type}) majburiy obuna ro'yxatiga qo'shildi!",
            reply_markup=get_admin_panel_menu()
        )
        return

    # ============ User: Yordam rejimi (adminga xabar yuborish) ============
    if state == "help_mode":
        USER_STATE.pop(user_id, None)
        user = message.from_user
        user_info = f"👤 <b>{user.first_name or ''} {user.last_name or ''}</b>"
        if user.username:
            user_info += f" (@{user.username})"
        user_info += f"\n🆔 ID: <code>{user.id}</code>"

        admin_text = (
            f"📩 <b>Yangi murojaat!</b>\n\n"
            f"{user_info}\n\n"
            f"💬 <b>Xabar:</b>\n{text}"
        )

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, admin_text)
            except Exception:
                pass

        await message.answer("✅ Xabaringiz adminga yuborildi! Tez orada javob olasiz.")
        return

    # ============ Bosh sahifa / Yangilash tugmalari ============
    if text == "🏠 Bosh sahifa":
        await message.answer(get_msg(user_lang, 'welcome'), reply_markup=get_main_menu(is_admin))
        return
    elif text == "🔄 Yangilash":
        await message.answer(get_msg(user_lang, 'welcome'))
        return
    elif text == "🌐 Tilni o'zgartirish":
        await message.answer(get_msg(user_lang, 'select_lang'), reply_markup=get_language_keyboard())
        return

    # ============ Yordam tugmasi ============
    elif text == "🆘 Yordam":
        USER_STATE[user_id] = "help_mode"
        await message.answer(
            "🆘 <b>Yordam</b>\n\n"
            "Adminga murojaat qilish uchun xabaringizni yozing.\n"
            "Keyingi yozgan xabaringiz to'g'ridan-to'g'ri adminga yuboriladi. ✉️"
        )
        return

    # ============ Admin panel ============
    elif text == "🛠 Admin panel" and is_admin:
        await message.answer("🛠 <b>Admin panel</b>\nQuyidagilardan birini tanlang:", reply_markup=get_admin_panel_menu())
        return

    elif text == "🔙 Orqaga" and is_admin:
        USER_STATE.pop(user_id, None)
        await message.answer(get_msg(user_lang, 'welcome'), reply_markup=get_main_menu(is_admin))
        return

    # ============ Admin: Statistika ============
    elif text == "📊 Statistika" and is_admin:
        stats = await get_stats()
        stats_text = (
            f"📊 <b>Bot Statistikasi</b>\n\n"
            f"👥 Jami userlar: <b>{stats['total_users']}</b>\n"
            f"📅 Bugun qo'shilgan: <b>{stats['today_users']}</b>\n\n"
            f"📥 Jami yuklamalar: <b>{stats['total_downloads']}</b>\n"
            f"📅 Bugungi yuklamalar: <b>{stats['today_downloads']}</b>\n"
            f"❌ Xatoliklar: <b>{stats['failed_downloads']}</b>\n\n"
            f"🏆 Eng ko'p ishlatiladigan: <b>{stats['most_used_platform']}</b>"
        )
        await message.answer(stats_text)
        return

    # ============ Admin: Broadcast ============
    elif text == "📢 Barcha userlarga elon" and is_admin:
        USER_STATE[user_id] = "broadcast_mode"
        all_ids = await get_all_user_ids()
        await message.answer(
            f"📢 <b>Broadcast rejimi</b>\n\n"
            f"👥 Jami userlar: <b>{len(all_ids)}</b>\n\n"
            f"Endi yozgan xabaringiz barcha userlarga yuboriladi.\n"
            f"Bekor qilish uchun <b>🔙 Orqaga</b> ni bosing."
        )
        return

    # ============ Admin: Kanal qo'shish ============
    elif text == "➕ Kanal qo'shish" and is_admin:
        USER_STATE[user_id] = "add_channel"
        await message.answer(
            "📢 <b>Kanal qo'shish</b>\n\n"
            "Kanal username yoki ID sini yuboring.\n"
            "Masalan: <code>@your_channel</code> yoki <code>-1001234567890</code>\n\n"
            "⚠️ Bot kanalda admin bo'lishi kerak!"
        )
        return

    elif text == "➕ Guruh qo'shish" and is_admin:
        USER_STATE[user_id] = "add_group"
        await message.answer(
            "👥 <b>Guruh qo'shish</b>\n\n"
            "Guruh username yoki ID sini yuboring.\n"
            "Masalan: <code>@your_group</code> yoki <code>-1001234567890</code>\n\n"
            "⚠️ Bot guruhda admin bo'lishi kerak!"
        )
        return

    elif text == "➕ Bot qo'shish" and is_admin:
        USER_STATE[user_id] = "add_bot"
        await message.answer(
            "🤖 <b>Bot qo'shish</b>\n\n"
            "Bot username ni yuboring.\n"
            "Masalan: <code>@another_bot</code>"
        )
        return

    # ============ Admin: Majburiy obuna ro'yxati ============
    elif text == "📋 Majburiy obuna ro'yxati" and is_admin:
        channels = await get_forced_channels()
        if not channels:
            await message.answer("📭 Majburiy obuna ro'yxati bo'sh.\nYuqoridagi tugmalar orqali qo'shing.")
        else:
            await message.answer(
                "📋 <b>Majburiy obuna ro'yxati</b>\n\nO'chirish uchun ustiga bosing:",
                reply_markup=get_forced_channels_list_keyboard(channels)
            )
        return

    # ============ URL ni tekshirish va mediaga ishlov berish ============
    if not is_valid_url(text):
        await message.answer(get_msg(user_lang, 'error_invalid_url'))
        return

    # Majburiy obuna tekshiruvi
    from bot.utils.force_sub import check_subscription
    is_subscribed = await check_subscription(bot, user_id)
    if not is_subscribed:
        return  # check_subscription ichida xabar yuboriladi

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
        logging.error(f"Error extracting info: {e}")
        try:
            await status_msg.edit_text(get_msg(user_lang, 'error_private'))
        except aiogram.exceptions.TelegramBadRequest:
            pass
