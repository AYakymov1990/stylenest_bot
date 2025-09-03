# app/tasks/expiry.py
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import settings
from app.deps import SessionLocal
from app.models import Subscription, SubscriptionStatus

CHECK_EVERY_SECONDS = int(os.getenv("CHECK_INTERVAL", "60"))


def _tariffs_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Оплатити 1 місяць – {settings.TARIFF_1M_PRICE_EUR}€", callback_data="pay:1m")],
        [InlineKeyboardButton(text=f"Оплатити 2 місяці – {settings.TARIFF_2M_PRICE_EUR}€", callback_data="pay:2m")],
        [InlineKeyboardButton(text=f"Оплатити 3 місяці – {settings.TARIFF_3M_PRICE_EUR}€", callback_data="pay:3m")],
    ])


async def _remove_from_channel(bot: Bot, user_id: int) -> None:
    try:
        await bot.ban_chat_member(chat_id=settings.CHANNEL_ID, user_id=user_id)
    except Exception as e:
        print("ban_chat_member error:", user_id, repr(e))
    try:
        await bot.unban_chat_member(chat_id=settings.CHANNEL_ID, user_id=user_id, only_if_banned=True)
    except Exception as e:
        print("unban_chat_member error:", user_id, repr(e))


async def process_expiry_once(bot: Bot) -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        rows = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.active,
            Subscription.ends_at <= now,
        ).all()

        for sub in rows:
            await _remove_from_channel(bot, sub.tg_id)
            sub.status = SubscriptionStatus.expired
            db.add(sub)

        if rows:
            db.commit()

        for sub in rows:
            try:
                await bot.send_message(
                    sub.tg_id,
                    "Ваша підписка на STYLENEST CLUB закінчилась. "
                    "Продовжіть її, щоб нічого не пропустити 🙌🏻",
                    reply_markup=_tariffs_kb(),
                )
            except Exception as e:
                print("notify expired send error:", sub.tg_id, repr(e))


# Optional standalone loop (not used by worker, but handy for local runs)
async def _loop() -> None:
    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    try:
        while True:
            await process_expiry_once(bot)
            await asyncio.sleep(CHECK_EVERY_SECONDS)
    finally:
        await bot.session.close()


# Backward compatibility alias (if old code imported wrong name)
process_expired_once = process_expiry_once

if __name__ == "__main__":
    asyncio.run(_loop())