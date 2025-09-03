# app/tasks/expiry.py
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from app.config import settings
from app.deps import SessionLocal
from app.models import Subscription, SubscriptionStatus

CHECK_EVERY_SECONDS = 60  # период проверки

async def process_expired_once(bot: Bot):
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        q = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.active,
            Subscription.ends_at <= now,
        )
        expired = q.all()

        for sub in expired:
            try:
                if settings.CHANNEL_ID:
                    # в каналах удаление = бан на 1 сек. + анбан, чтобы можно было вступить снова
                    await bot.ban_chat_member(chat_id=settings.CHANNEL_ID, user_id=sub.tg_id)
                    await bot.unban_chat_member(chat_id=settings.CHANNEL_ID, user_id=sub.tg_id)
            except Exception as e:
                print("kick error:", sub.tg_id, repr(e))

            sub.status = SubscriptionStatus.expired
            db.add(sub)

        if expired:
            db.commit()

async def main():
    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    try:
        while True:
            await process_expired_once(bot)
            await asyncio.sleep(CHECK_EVERY_SECONDS)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())