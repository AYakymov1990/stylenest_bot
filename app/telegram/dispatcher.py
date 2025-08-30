from aiogram import Dispatcher
from .handlers import router as handlers_router

# Создаём единый Dispatcher, чтобы переиспользовать и в polling, и в webhook
dp = Dispatcher()
dp.include_router(handlers_router)
