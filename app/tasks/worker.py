# app/tasks/worker.py
from __future__ import annotations
import asyncio
import signal
import contextlib

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from app.config import settings
from app.telegram.dispatcher import dp
from app.tasks.reminders import process_reminders_once
from app.tasks.expiry import process_expiry_once

CHECK_INTERVAL = 60
RUN = True


def _graceful(*_):
    global RUN
    RUN = False


async def reminders_loop(bot: Bot):
    while RUN:
        try:
            await process_reminders_once(bot)
        except Exception as e:
            print("[worker] reminders_loop error:", repr(e))
        await asyncio.sleep(CHECK_INTERVAL)


async def expiry_loop(bot: Bot):
    while RUN:
        try:
            await process_expiry_once(bot)
        except Exception as e:
            print("[worker] expiry_loop error:", repr(e))
        await asyncio.sleep(CHECK_INTERVAL)


async def main():
    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    poller = asyncio.create_task(dp.start_polling(bot))
    rloop = asyncio.create_task(reminders_loop(bot))
    eloop = asyncio.create_task(expiry_loop(bot))

    done, pending = await asyncio.wait({poller, rloop, eloop}, return_when=asyncio.FIRST_EXCEPTION)

    for t in pending:
        t.cancel()
        with contextlib.suppress(Exception):
            await t
    await bot.session.close()


if __name__ == "__main__":
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _graceful)
    asyncio.run(main())