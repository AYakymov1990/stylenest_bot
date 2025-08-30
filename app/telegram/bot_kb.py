# app/telegram/bot_kb.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [
                KeyboardButton(text="💳 Тарифы"),
                KeyboardButton(text="🧾 Моя подписка"),
            ]
        ],
    )
