# app/web/payments.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, HTTPException
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import settings
from app.deps import SessionLocal
from app.models import Payment, PaymentStatus
from app.services.subscriptions import ensure_active_subscription

router = APIRouter()


# ---------- helpers ----------

def _extract_paid_at(gw: Dict[str, Any]) -> datetime:
    """
    Забираем timestamp оплаты из полей WayForPay:
    processingDate / createdDate / settlementDate / orderTime / orderDate (unix).
    Если ничего нет — текущее UTC.
    """
    for key in ("processingDate", "createdDate", "settlementDate", "orderTime", "orderDate"):
        v = gw.get(key)
        if isinstance(v, (int, float)) and v > 0:
            try:
                return datetime.fromtimestamp(int(v), tz=timezone.utc)
            except Exception:
                pass
        if isinstance(v, str) and v.isdigit():
            try:
                return datetime.fromtimestamp(int(v), tz=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


async def _approve_flow(db, p: Payment, data: Dict[str, Any]) -> None:
    """
    Отмечаем платёж успешным (в ЭТОЙ ЖЕ сессии db),
    ставим paid_at, активируем/продлеваем подписку, отправляем инвайт.
    """
    # 1) обновляем платёж в той же сессии
    paid_at = _extract_paid_at(data)
    if hasattr(p, "paid_at"):
        p.paid_at = paid_at
    p.status = PaymentStatus.approved
    db.flush()   # объект уже привязан к этой сессии — add() НЕ НУЖЕН
    db.commit()

    # 2) подписка и инвайт
    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    try:
        sub = await ensure_active_subscription(
            db=db,
            bot=bot,
            tg_id=p.tg_id,
            tariff_code=p.tariff_code,
        )

        text = "Дякуємо за оплату 🤍 Підписку активовано."
        kb = None
        invite_link = getattr(sub, "invite_link", None)
        if invite_link:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Вступити", url=invite_link)]
            ])
        await bot.send_message(p.tg_id, text if kb else text + "\nНе вдалося створити інвайт автоматично.")
        if kb:
            # отправим инвайт отдельным сообщением, чтобы точно не потерялся
            await bot.send_message(p.tg_id, "Ваше запрошення:", reply_markup=kb)
    finally:
        await bot.session.close()


# ---------- core processor ----------

async def _process_wfp_callback(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обработка серверного колбэка WayForPay.
    ВСЕГДА возвращаем {"status":"accept"} во избежание ретраев на стороне WFP.
    Внутренние ошибки просто логируем.
    """
    print("WFP CALLBACK:", payload)

    order_reference = payload.get("orderReference") or payload.get("order_reference")
    status_raw = payload.get("transactionStatus") or payload.get("orderStatus") or ""
    status = str(status_raw).strip().capitalize()

    if not order_reference:
        # даже в этом случае вернём accept, иначе WFP будет долбить ретраями
        return {"status": "accept", "orderReference": order_reference or ""}

    with SessionLocal() as db:
        p: Optional[Payment] = db.query(Payment).filter(
            Payment.order_reference == order_reference
        ).one_or_none()

        if not p:
            # неизвестный платёж — просто примем
            return {"status": "accept", "orderReference": order_reference}

        try:
            if status == "Approved":
                if p.status != PaymentStatus.approved:
                    # делаем основной поток строго один раз
                    await _approve_flow(db, p, payload)
                # если уже Approved — идемпотентно ничего не делаем
            elif status in {"Declined", "Expired"}:
                # обновим статус и зафиксируем
                p.status = (PaymentStatus.declined if status == "Declined"
                            else PaymentStatus.expired)
                db.flush()
                db.commit()
            else:
                # InProcessing / Waiting и т.п. — просто принимаем
                pass
        except Exception as e:
            # Лог и всё равно accept, чтобы WFP не слал повторно.
            print("WFP PROCESS ERROR:", repr(e))

    return {"status": "accept", "orderReference": order_reference}


# ---------- routes ----------

@router.post("/wfp/callback")
async def wfp_callback(request: Request):
    data = await request.json()
    return await _process_wfp_callback(data)

# дубликат со слэшем — некоторые проксики/конфиги отдают именно так
@router.post("/wfp/callback/")
async def wfp_callback_slash(request: Request):
    data = await request.json()
    return await _process_wfp_callback(data)

# локальный мок для удобного теста
# curl -X POST http://localhost:8080/wfp/mock/callback \
#   -H 'Content-Type: application/json' \
#   -d '{"orderReference":"tg123_1700000000_1m","transactionStatus":"Approved"}'
@router.post("/wfp/mock/callback")
async def wfp_mock_callback(request: Request):
    data = await request.json()
    return await _process_wfp_callback(data)