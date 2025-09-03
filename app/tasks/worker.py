# app/tasks/worker.py
from __future__ import annotations
import asyncio
import logging
import signal
import contextlib

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from app.config import settings
from app.logging_config import setup_logging
from app.telegram.dispatcher import dp
from app.tasks.reminders import process_reminders_once
from app.tasks.expiry import process_expiry_once
from app.tasks.winback import process_winback_once

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 60
RUN = True


def _graceful(*_):
    global RUN
    RUN = False


async def reminders_loop(bot: Bot):
    """Цикл обработки напоминаний"""
    logger.info("[WORKER] Запуск цикла напоминаний")
    while RUN:
        try:
            await process_reminders_once(bot)
        except Exception as e:
            logger.error(f"[WORKER] Ошибка в цикле напоминаний: {e}")
        await asyncio.sleep(CHECK_INTERVAL)
    logger.info("[WORKER] Остановка цикла напоминаний")


async def expiry_loop(bot: Bot):
    """Цикл обработки истекших подписок"""
    logger.info("[WORKER] Запуск цикла обработки истекших подписок")
    while RUN:
        try:
            await process_expiry_once(bot)
        except Exception as e:
            logger.error(f"[WORKER] Ошибка в цикле обработки истекших подписок: {e}")
        await asyncio.sleep(CHECK_INTERVAL)
    logger.info("[WORKER] Остановка цикла обработки истекших подписок")


async def winback_loop(bot: Bot):
    """Цикл обработки winback-сообщений"""
    logger.info("[WORKER] Запуск цикла winback-сообщений")
    while RUN:
        try:
            await process_winback_once(bot)
        except Exception as e:
            logger.error(f"[WORKER] Ошибка в цикле winback-сообщений: {e}")
        await asyncio.sleep(CHECK_INTERVAL)
    logger.info("[WORKER] Остановка цикла winback-сообщений")


async def main():
    """Основная функция worker'а"""
    logger.info("[WORKER] Запуск worker'а")
    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    
    poller = asyncio.create_task(dp.start_polling(bot))
    rloop = asyncio.create_task(reminders_loop(bot))
    eloop = asyncio.create_task(expiry_loop(bot))
    wloop = asyncio.create_task(winback_loop(bot))

    logger.info("[WORKER] Все задачи запущены: polling, reminders, expiry, winback")
    
    try:
        done, pending = await asyncio.wait({poller, rloop, eloop, wloop}, return_when=asyncio.FIRST_EXCEPTION)
        logger.info("[WORKER] Одна из задач завершилась")
    except Exception as e:
        logger.error(f"[WORKER] Ошибка в main: {e}")
    finally:
        logger.info("[WORKER] Остановка всех задач")
        for t in pending:
            t.cancel()
            with contextlib.suppress(Exception):
                await t
        await bot.session.close()
        logger.info("[WORKER] Worker остановлен")


if __name__ == "__main__":
    # Настройка логирования
    setup_logging()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _graceful)
    asyncio.run(main())