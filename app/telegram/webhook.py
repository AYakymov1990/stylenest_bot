from fastapi import APIRouter, Request, Response, HTTPException
from aiogram import Bot
from aiogram.types import Update
from .dispatcher import dp
from app.config import settings

router = APIRouter()

@router.post("/tg/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    # простая защита: секрет в пути
    if secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")

    payload = await request.json()
    update = Update.model_validate(payload)

    bot = Bot(token=settings.BOT_TOKEN, parse_mode="HTML")
    try:
        await dp.feed_update(bot, update)
    finally:
        await bot.session.close()

    return Response(status_code=200)

# небольшая проверка, что секрет верный и роут подключён
@router.get("/tg/webhook/{secret}/ping")
async def webhook_ping(secret: str):
    if secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")
    return {"ok": True, "mode": "webhook-ready"}
