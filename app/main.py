"""Minimal aiogram 3.x Telegram bot."""

import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer("Привіт! Радий тебе бачити 👋")


@dp.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Я книжковий бот і допомагаю знаходити книги за настроєм та вподобаннями."
    )


@dp.message(Command("age"))
async def age_command(message: Message) -> None:
    await message.answer("Вікові обмеження відсутні.")


@dp.message(Command("about"))
async def about_command(message: Message) -> None:
    await message.answer(
        "Підбір книг за бажаними ключовими словами (наприклад: ліс, таємниця, міфи), "
        "настроєм (сумний, веселий, загадковий, злий і т.д.) та жанром "
        "(роман, детектив, психологія, історія і т.д.)."
    )


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Задайте BOT_TOKEN у змінних середовища.")

    async with Bot(token=token) as bot:
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
