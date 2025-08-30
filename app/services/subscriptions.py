# app/services/subscriptions.py
from datetime import datetime, timedelta, timezone
from aiogram import Bot
from app.config import settings
from app.models import Subscription, SubscriptionStatus

# наши периоды (как и раньше)
PERIOD_DAYS = {"1m": 30, "2m": 60, "3m": 90}

async def ensure_active_subscription(db, bot: Bot, *, tg_id: int, tariff_code: str) -> Subscription:
    """Создаёт или продлевает подписку, пытается сгенерировать одноразовый инвайт в канал."""
    now = datetime.now(timezone.utc)
    days = PERIOD_DAYS[tariff_code]

    sub = db.query(Subscription).filter(
        Subscription.tg_id == tg_id,
        Subscription.status == SubscriptionStatus.active,
        Subscription.ends_at > now,
    ).one_or_none()

    if sub:
        sub.ends_at = sub.ends_at + timedelta(days=days)
    else:
        sub = Subscription(
            tg_id=tg_id,
            tariff_code=tariff_code,
            status=SubscriptionStatus.active,
            starts_at=now,
            ends_at=now + timedelta(days=days),
        )
        db.add(sub)

    # создаём одноразовый инвайт (1 клик, срок — 24 часа)
    invite_link = None
    try:
        if settings.CHANNEL_ID:
            expire_ts = int((now + timedelta(hours=24)).timestamp())
            invite = await bot.create_chat_invite_link(
                chat_id=settings.CHANNEL_ID,
                name=f"sub-{tg_id}-{tariff_code}",
                expire_date=expire_ts,
                member_limit=1,
            )
            invite_link = invite.invite_link
            sub.invite_link = invite_link
    except Exception as e:
        # не валим процессинг если у бота нет прав — просто не будет ссылки
        print("create_chat_invite_link error:", repr(e))

    db.commit()
    return sub
