# app/tasks/expiry.py
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import settings
from app.deps import SessionLocal
from app.models import Subscription, SubscriptionStatus

logger = logging.getLogger(__name__)

CHECK_EVERY_SECONDS = int(os.getenv("CHECK_INTERVAL", "60"))


def _tariffs_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Оплатити 1 місяць – {settings.TARIFF_1M_PRICE_EUR}€", callback_data="pay:1m")],
        [InlineKeyboardButton(text=f"Оплатити 2 місяці – {settings.TARIFF_2M_PRICE_EUR}€", callback_data="pay:2m")],
        [InlineKeyboardButton(text=f"Оплатити 3 місяці – {settings.TARIFF_3M_PRICE_EUR}€", callback_data="pay:3m")],
    ])


async def _remove_from_channel(bot: Bot, user_id: int) -> None:
    """Удаляет пользователя из канала после окончания подписки"""
    logger.info(f"[EXPIRY] Удаление пользователя {user_id} из канала {settings.CHANNEL_ID}")
    
    try:
        # Сначала баним пользователя
        await bot.ban_chat_member(chat_id=settings.CHANNEL_ID, user_id=user_id)
        logger.info(f"[EXPIRY] Пользователь {user_id} забанен в канале")
    except Exception as e:
        logger.error(f"[EXPIRY] Ошибка при бане пользователя {user_id}: {e}")
    
    try:
        # Затем разбаниваем (это удаляет из канала)
        await bot.unban_chat_member(chat_id=settings.CHANNEL_ID, user_id=user_id, only_if_banned=True)
        logger.info(f"[EXPIRY] Пользователь {user_id} удален из канала")
    except Exception as e:
        logger.error(f"[EXPIRY] Ошибка при удалении пользователя {user_id} из канала: {e}")


async def process_expiry_once(bot: Bot) -> None:
    """Обрабатывает истекшие подписки: удаляет из канала и уведомляет"""
    now = datetime.now(timezone.utc)
    logger.info(f"[EXPIRY] Проверка истекших подписок на {now}")
    
    with SessionLocal() as db:
        # Находим активные подписки, которые уже истекли
        rows = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.active,
            Subscription.ends_at <= now,
        ).all()

        logger.info(f"[EXPIRY] Найдено {len(rows)} истекших подписок")

        for sub in rows:
            logger.info(f"[EXPIRY] Обработка подписки {sub.id} для пользователя {sub.tg_id} (истекла {sub.ends_at})")
            
            # Удаляем пользователя из канала
            await _remove_from_channel(bot, sub.tg_id)
            
            # Помечаем подписку как истекшую
            sub.status = SubscriptionStatus.expired
            sub.reminded_expired_at = now
            db.add(sub)

        if rows:
            db.commit()
            logger.info(f"[EXPIRY] Обновлено {len(rows)} подписок в БД")

        # Отправляем уведомления
        for sub in rows:
            try:
                await bot.send_message(
                    sub.tg_id,
                    "Ваша підписка на STYLENEST CLUB закінчилась. "
                    "Продовжіть її, щоб нічого не пропустити 🙌🏻",
                    reply_markup=_tariffs_kb(),
                )
                logger.info(f"[EXPIRY] Уведомление об истечении отправлено пользователю {sub.tg_id}")
            except Exception as e:
                logger.error(f"[EXPIRY] Ошибка отправки уведомления пользователю {sub.tg_id}: {e}")


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