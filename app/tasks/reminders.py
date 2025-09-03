from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import settings
from app.deps import SessionLocal
from app.models import Subscription, SubscriptionStatus

logger = logging.getLogger(__name__)

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
    """Отправляет уведомление пользователю"""
    try:
        await bot.send_message(chat_id=tg_id, text=text, reply_markup=_tariffs_kb())
        logger.info(f"[REMINDERS] Уведомление отправлено пользователю {tg_id}")
    except Exception as e:
        logger.error(f"[REMINDERS] Ошибка отправки уведомления пользователю {tg_id}: {e}")


async def process_reminders_once(bot: Bot) -> None:
    """Обрабатывает напоминания о заканчивающихся подписках"""
    now = datetime.now(timezone.utc)
    logger.info(f"[REMINDERS] Проверка напоминаний на {now}")
    
    with SessionLocal() as db:
        # ---- Напоминание за 3 дня ----
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
        
        logger.info(f"[REMINDERS] Найдено {len(subs3)} подписок для напоминания за 3 дня")
        
        for s in subs3:
            logger.info(f"[REMINDERS] Отправка напоминания за 3 дня пользователю {s.tg_id} (подписка {s.id}, истекает {s.ends_at})")
            await _notify(
                bot,
                s.tg_id,
                "Ваша підписка на STYLENEST CLUB закінчиться через 3 дні. "
                "Продовжіть підписку, щоб залишатись з нами 👜",
            )
            s.reminded_3d_at = now
        db.commit()

        # ---- Напоминание за 1 день ----
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
        
        logger.info(f"[REMINDERS] Найдено {len(subs1)} подписок для напоминания за 1 день")
        
        for s in subs1:
            logger.info(f"[REMINDERS] Отправка напоминания за 1 день пользователю {s.tg_id} (подписка {s.id}, истекает {s.ends_at})")
            await _notify(
                bot,
                s.tg_id,
                "Ваша підписка на STYLENEST CLUB закінчиться завтра. "
                "Продовжіть підписку, щоб залишатись з нами 👜",
            )
            s.reminded_1d_at = now
        db.commit()

        # ---- Уведомление об уже истекших (дублирование с expiry.py - убираем) ----
        # Эта логика перенесена в expiry.py для избежания дублирования
        logger.info(f"[REMINDERS] Обработка напоминаний завершена. Отправлено: за 3 дня - {len(subs3)}, за 1 день - {len(subs1)}")


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