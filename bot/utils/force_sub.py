from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from bot.database.db import get_forced_channels
from bot.keyboards.inline import get_forced_sub_keyboard
import logging


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """
    Foydalanuvchi barcha majburiy kanallarga obuna bo'lganini tekshiradi.
    Agar obuna bo'lmasa, obuna bo'lish tugmalarini yuboradi va False qaytaradi.
    """
    channels = await get_forced_channels()
    if not channels:
        return True  # Majburiy obuna yo'q

    not_subscribed = []

    for ch in channels:
        chat_id = ch["chat_id"]
        chat_type = ch["chat_type"]

        # Bot tipi uchun tekshiruv qilmaymiz
        if chat_type == "bot":
            continue

        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status in [
                ChatMemberStatus.LEFT,
                ChatMemberStatus.KICKED,
            ]:
                not_subscribed.append(ch)
        except Exception as e:
            logging.warning(f"Could not check subscription for {chat_id}: {e}")
            # Agar tekshirib bo'lmasa, o'tkazib yuboramiz
            continue

    if not_subscribed:
        await bot.send_message(
            user_id,
            "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>",
            reply_markup=get_forced_sub_keyboard(not_subscribed)
        )
        return False

    return True
