from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, String, Integer, DateTime, Enum, Text, JSON
from enum import Enum as PyEnum
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class PaymentStatus(str, PyEnum):
    pending = "pending"
    approved = "approved"
    declined = "declined"
    expired = "expired"

class SubscriptionStatus(str, PyEnum):
    active = "active"
    expired = "expired"
    cancelled = "cancelled"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    lang: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    order_reference: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    invoice_id: Mapped[str | None] = mapped_column(String(128))
    invoice_url: Mapped[str | None] = mapped_column(Text)
    tariff_code: Mapped[str] = mapped_column(String(8))     # '1m' | '2m' | '3m'
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8))
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending, index=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    tariff_code: Mapped[str] = mapped_column(String(8))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus), default=SubscriptionStatus.active, index=True)
    invite_link: Mapped[str | None] = mapped_column(Text)
    last_notified_3d: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_notified_1d: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
