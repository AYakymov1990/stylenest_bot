# app/telegram/handlers.py
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)

from app.config import settings
from app.deps import SessionLocal
from app.models import User, Payment, PaymentStatus, Subscription, SubscriptionStatus
from app.payments.wayforpay import WayForPayClient
from app.telegram.bot_kb import main_kb

router = Router()

# ====== вспомогательные штуки ======

TITLES_UA = {"1m": "1 місяць", "2m": "2 місяці", "3m": "3 місяці"}

def _eur_price(code: str) -> int:
    return {
        "1m": settings.TARIFF_1M_PRICE_EUR,
        "2m": settings.TARIFF_2M_PRICE_EUR,
        "3m": settings.TARIFF_3M_PRICE_EUR,
    }[code]

def _local_price(code: str) -> int:
    return {
        "1m": settings.TARIFF_1M_PRICE_LOCAL,
        "2m": settings.TARIFF_2M_PRICE_LOCAL,
        "3m": settings.TARIFF_3M_PRICE_LOCAL,
    }[code]

def _tariffs_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"1 місяць - {_eur_price('1m')}€ 💳", callback_data="tariff:1m")],
        [InlineKeyboardButton(text=f"2 місяці - {_eur_price('2m')}€ 💳", callback_data="tariff:2m")],
        [InlineKeyboardButton(text=f"3 місяці - {_eur_price('3m')}€ 💳", callback_data="tariff:3m")],
    ])

def _tariff_details_text(code: str) -> str:
    title = TITLES_UA[code]
    eur = _eur_price(code)
    local = _local_price(code)
    return (
        f"{title} - {eur}€ 💳\n"
        f"Ціна: {local}₴\n"
        f"Тривалість: {title}\n\n"
        f"Ви отримаєте запрошення в канал 👇\n"
        f"— STYLENEST CLUB"
    )

def _tariff_details_kb(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay:{code}")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back:tariffs")],
    ])

def _ensure_user(tg_id: int, username: Optional[str], lang: Optional[str]) -> None:
    with SessionLocal() as db:
        u = db.query(User).filter(User.tg_id == tg_id).one_or_none()
        if not u:
            u = User(
                tg_id=tg_id,
                username=username,
                lang=lang,
                created_at=datetime.now(timezone.utc),
            )
            db.add(u)
            db.commit()

async def _send_tariffs_block(msg: Message) -> None:
    """Фото + список тарифов (первый экран) + меню-клавиатура."""
    # 1) Фото (если задано)
    file_id = getattr(settings, "START_PHOTO_FILE_ID", "") or ""
    local_path = getattr(settings, "START_IMAGE_PATH", "") or ""
    try:
        if file_id:
            await msg.answer_photo(photo=file_id, reply_markup=main_kb())
        elif local_path and os.path.exists(local_path):
            await msg.answer_photo(photo=FSInputFile(local_path), reply_markup=main_kb())
        else:
            await msg.answer("Спасибо за ваш интерес 🕊", reply_markup=main_kb())
    except Exception:
        await msg.answer("Спасибо за ваш интерес 🕊", reply_markup=main_kb())

    # 2) Текст + inline-кнопки тарифов
    await msg.answer(
        "Виберіть бажаний для вас тариф 🤍",
        reply_markup=_tariffs_kb(),
    )

# ---- TZ utils ----
def _as_aware_utc(dt: datetime) -> datetime:
    """Сделать дату timezone-aware в UTC (если naive — проставим tzinfo=UTC)."""
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _human_left(dt_to: datetime) -> str:
    now = datetime.now(timezone.utc)
    dt_to_utc = _as_aware_utc(dt_to)
    delta = dt_to_utc - now
    if delta.total_seconds() <= 0:
        return "закінчилась"
    days = delta.days
    hours = int(delta.seconds // 3600)
    mins = int((delta.seconds % 3600) // 60)
    parts = []
    if days:
        parts.append(f"{days} дн.")
    if hours:
        parts.append(f"{hours} год.")
    if not days and mins:
        parts.append(f"{mins} хв.")
    return "менше хвилини" if not parts else " ".join(parts)

# ====== хендлеры ======

@router.message(CommandStart())
async def cmd_start(msg: Message, command: CommandObject):
    """Обрабатываем /start и deep-link /start paid. Всегда показываем меню."""
    _ensure_user(msg.from_user.id, msg.from_user.username, msg.from_user.language_code)

    payload = (command.args or "").strip()
    if payload == "paid":
        await msg.answer("Дякуємо за оплату 🤍 Перевіряю статус…", reply_markup=main_kb())
        await _send_tariffs_block(msg)
        return

    await _send_tariffs_block(msg)

@router.callback_query(F.data.startswith("tariff:"))
async def show_tariff_details(cb: CallbackQuery):
    code = cb.data.split(":", 1)[1]
    await cb.message.answer(
        _tariff_details_text(code),
        reply_markup=_tariff_details_kb(code),
    )
    await cb.answer()

@router.callback_query(F.data == "back:tariffs")
async def back_to_tariffs(cb: CallbackQuery):
    await _send_tariffs_block(cb.message)
    await cb.answer()

@router.callback_query(F.data.startswith("pay:"))
async def pay_create_invoice(cb: CallbackQuery):
    code = cb.data.split(":", 1)[1]
    amount_local = _local_price(code)

    wfp = WayForPayClient()
    order_reference, invoice_id, invoice_url = await wfp.create_invoice(
        tg_id=cb.from_user.id,
        tariff_code=code,
        amount=amount_local,
    )

    with SessionLocal() as db:
        p = Payment(
            tg_id=cb.from_user.id,
            tariff_code=code,
            amount=amount_local,
            currency=getattr(settings, "WFP_CURRENCY", "UAH"),
            order_reference=order_reference,
            invoice_id=invoice_id,
            invoice_url=invoice_url,
            status=PaymentStatus.pending,
            created_at=datetime.now(timezone.utc),
        )
        db.add(p)
        db.commit()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", url=invoice_url)],
    ])
    await cb.message.answer("✅ Счёт создан.\nНажмите «Перейти к оплате».", reply_markup=kb)
    await cb.answer()

# ==== Меню-кнопки ====

@router.message(F.text.in_({"Тарифы", "💳 Тарифы", "Тарифи", "💳 Тарифи"}))
async def menu_tariffs(msg: Message):
    await _send_tariffs_block(msg)

@router.message(F.text.in_({"Моя подписка", "🧾 Моя подписка", "Моя підписка", "🧾 Моя підписка"}))
async def menu_my_subscription(msg: Message):
    with SessionLocal() as db:
        sub = db.query(Subscription).filter(
            Subscription.tg_id == msg.from_user.id,
            Subscription.status == SubscriptionStatus.active
        ).order_by(Subscription.id.desc()).first()

    if not sub:
        await msg.answer("Підписка не знайдена. Оформіть її в розділі «💳 Тарифы».", reply_markup=main_kb())
        return

    ends_local = _as_aware_utc(sub.ends_at).astimezone()
    left_str = _human_left(sub.ends_at)
    title = TITLES_UA.get(sub.tariff_code, sub.tariff_code)
    await msg.answer(
        f"🧾 Ваша підписка: <b>{title}</b>\n"
        f"Статус: <b>активна</b>\n"
        f"Діє до: <b>{ends_local:%d.%m.%Y %H:%M}</b>\n"
        f"Залишилось: <b>{left_str}</b>",
        reply_markup=main_kb()
    )
