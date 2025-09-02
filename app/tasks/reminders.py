from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import settings
from app.deps import SessionLocal
from app.models import Subscription, SubscriptionStatus

CHECK_EVERY_SECONDS = 60  # как часто проверять


def _tariffs_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"1 місяць – {settings.TARIFF_1M_PRICE_EUR}€", callback_data="tariff:1m")],
            [InlineKeyboardButton(text=f"2 місяці – {settings.TARIFF_2M_PRICE_EUR}€", callback_data="tariff:2m")],
            [InlineKeyboardButton(text=f"3 місяці – {settings.TARIFF_3M_PRICE_EUR}€", callback_data="tariff:3m")],
        ]
    )


async def _notify(bot: Bot, tg_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id=tg_id, text=text, reply_markup=_tariffs_kb())
    except Exception as e:
        print(f"[reminders] send_message failed tg_id={tg_id}: {e}")


async def process_reminders_once(bot: Bot) -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        # ---- 3 дні ----
        three_from = now + timedelta(days=3)
        three_to = now + timedelta(days=3, hours=1)  # «окно» 1 час

        subs3 = (
            db.query(Subscription)
            .filter(
                Subscription.status == SubscriptionStatus.active,
                Subscription.reminded_3d_at.is_(None),
                Subscription.ends_at >= three_from,
                Subscription.ends_at < three_to,
            )
            .all()
        )
        for s in subs3:
            await _notify(
                bot,
                s.tg_id,
                "Ваша підписка на STYLENEST CLUB закінчиться через 3 дні. "
                "Продовжіть підписку, щоб залишатись з нами 👜",
            )
            s.reminded_3d_at = now
        db.commit()

        # ---- завтра (1 день) ----
        one_from = now + timedelta(days=1)
        one_to = now + timedelta(days=1, hours=1)

        subs1 = (
            db.query(Subscription)
            .filter(
                Subscription.status == SubscriptionStatus.active,
                Subscription.reminded_1d_at.is_(None),
                Subscription.ends_at >= one_from,
                Subscription.ends_at < one_to,
            )
            .all()
        )
        for s in subs1:
            await _notify(
                bot,
                s.tg_id,
                "Ваша підписка на STYLENEST CLUB закінчиться завтра. "
                "Продовжіть підписку, щоб залишатись з нами 👜",
            )
            s.reminded_1d_at = now
        db.commit()

        # ---- уже закінчилась ----
        expired_subs = (
            db.query(Subscription)
            .filter(
                Subscription.reminded_expired_at.is_(None),
                Subscription.ends_at <= now,
            )
            .all()
        )
        for s in expired_subs:
            await _notify(
                bot,
                s.tg_id,
                "Ваша підписка на STYLENEST CLUB закінчилась. "
                "Продовжіть її, щоб нічого не пропустити 🙌🏻",
            )
            s.reminded_expired_at = now
        db.commit()


async def main() -> None:
    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    try:
        while True:
            await process_reminders_once(bot)
            await asyncio.sleep(CHECK_EVERY_SECONDS)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
