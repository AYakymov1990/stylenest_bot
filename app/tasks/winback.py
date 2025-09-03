# app/tasks/winback.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

from app.config import settings
from app.deps import SessionLocal
from app.models import User, Payment, PaymentStatus

logger = logging.getLogger(__name__)

CHECK_EVERY_SECONDS = 60  # как часто проверять


def _tariffs_kb() -> InlineKeyboardMarkup:
    """Клавиатура с тарифами для winback-сообщений"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"1 місяць – {settings.TARIFF_1M_PRICE_EUR}€", callback_data="pay:1m")],
            [InlineKeyboardButton(text=f"2 місяці – {settings.TARIFF_2M_PRICE_EUR}€", callback_data="pay:2m")],
            [InlineKeyboardButton(text=f"3 місяці – {settings.TARIFF_3M_PRICE_EUR}€", callback_data="pay:3m")],
        ]
    )


async def _send_winback_message(bot: Bot, user: User) -> bool:
    """Отправляет winback-сообщение пользователю"""
    try:
        # Путь к изображению
        image_path = "app/assets/IMG_0796.PNG"
        
        # Текст сообщения
        message_text = (
            "Що вас чекає у вересні🍂\n\n"
            "- 3 готових капсули на осінь\n"
            "- огляди ваших улюблених магазинів (Zara, Mango, H&M, Reserved, Massimo Dutti, Cos, Stradivarius, Pull&bear, Bershka)\n"
            "- Лекція: Як підготувати гардероб до осені\n"
            "- Формули образів на осінь\n"
            "- Стильні прийоми в образах на осінь\n\n"
            "Обирай тариф та приєднуйся🖤"
        )
        
        # Отправляем фото с текстом
        photo = FSInputFile(image_path)
        await bot.send_photo(
            chat_id=user.tg_id,
            photo=photo,
            caption=message_text,
            reply_markup=_tariffs_kb()
        )
        
        logger.info(f"[WINBACK] Winback-сообщение отправлено пользователю {user.tg_id}")
        return True
        
    except Exception as e:
        logger.error(f"[WINBACK] Ошибка отправки winback-сообщения пользователю {user.tg_id}: {e}")
        return False


async def process_winback_once(bot: Bot) -> None:
    """Обрабатывает winback-сообщения для пользователей без оплаты"""
    now = datetime.now(timezone.utc)
    logger.info(f"[WINBACK] Проверка winback-сообщений на {now}")
    
    with SessionLocal() as db:
        # Находим пользователей, которые зарегистрировались, но не совершили оплату
        # Исключаем пользователей, у которых есть хотя бы одна успешная оплата
        users_without_payment = (
            db.query(User)
            .outerjoin(Payment, Payment.tg_id == User.tg_id)
            .filter(
                # Пользователь зарегистрирован
                User.created_at.isnot(None),
                # Нет успешных платежей
                ~User.tg_id.in_(
                    db.query(Payment.tg_id)
                    .filter(Payment.status == PaymentStatus.approved)
                )
            )
            .all()
        )
        
        logger.info(f"[WINBACK] Найдено {len(users_without_payment)} пользователей без оплаты")
        
        # Winback через 3 дня
        three_days_ago = now - timedelta(days=3)
        users_3d = [
            user for user in users_without_payment
            if (user.created_at.replace(tzinfo=timezone.utc) <= three_days_ago and 
                user.winback_3d_sent_at.is_(None))
        ]
        
        logger.info(f"[WINBACK] Найдено {len(users_3d)} пользователей для winback через 3 дня")
        
        for user in users_3d:
            success = await _send_winback_message(bot, user)
            if success:
                user.winback_3d_sent_at = now
                logger.info(f"[WINBACK] Winback 3d отправлен пользователю {user.tg_id} (зарегистрирован {user.created_at})")
        
        # Winback через 7 дней
        seven_days_ago = now - timedelta(days=7)
        users_7d = [
            user for user in users_without_payment
            if (user.created_at.replace(tzinfo=timezone.utc) <= seven_days_ago and 
                user.winback_7d_sent_at.is_(None) and
                user.winback_3d_sent_at.isnot(None))  # Только если уже отправили 3d
        ]
        
        logger.info(f"[WINBACK] Найдено {len(users_7d)} пользователей для winback через 7 дней")
        
        for user in users_7d:
            success = await _send_winback_message(bot, user)
            if success:
                user.winback_7d_sent_at = now
                logger.info(f"[WINBACK] Winback 7d отправлен пользователю {user.tg_id} (зарегистрирован {user.created_at})")
        
        # Winback через 30 дней
        thirty_days_ago = now - timedelta(days=30)
        users_30d = [
            user for user in users_without_payment
            if (user.created_at.replace(tzinfo=timezone.utc) <= thirty_days_ago and 
                user.winback_30d_sent_at.is_(None) and
                user.winback_7d_sent_at.isnot(None))  # Только если уже отправили 7d
        ]
        
        logger.info(f"[WINBACK] Найдено {len(users_30d)} пользователей для winback через 30 дней")
        
        for user in users_30d:
            success = await _send_winback_message(bot, user)
            if success:
                user.winback_30d_sent_at = now
                logger.info(f"[WINBACK] Winback 30d отправлен пользователю {user.tg_id} (зарегистрирован {user.created_at})")
        
        # Сохраняем изменения в БД
        if users_3d or users_7d or users_30d:
            db.commit()
            logger.info(f"[WINBACK] Обновлено {len(users_3d) + len(users_7d) + len(users_30d)} пользователей в БД")
        
        logger.info(f"[WINBACK] Обработка winback завершена. Отправлено: 3d - {len(users_3d)}, 7d - {len(users_7d)}, 30d - {len(users_30d)}")


async def main() -> None:
    """Основная функция для тестирования winback"""
    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    try:
        while True:
            await process_winback_once(bot)
            await asyncio.sleep(CHECK_EVERY_SECONDS)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
