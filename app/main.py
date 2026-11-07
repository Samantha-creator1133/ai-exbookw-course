"""Minimal aiogram 3.x Telegram bot."""

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message


logging.basicConfig(level=logging.INFO)

dp = Dispatcher()


def load_env_file() -> None:
    """Load simple KEY=VALUE entries from the project-root .env file."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            os.environ.setdefault(key, value)


@dp.message(CommandStart())
async def start(message: Message) -> None:
    logging.info("Користувач викликав /start")
    await message.answer("Привіт! Радий тебе бачити 👋")


@dp.message(Command("help"))
async def help_command(message: Message) -> None:
    logging.info("Користувачу треба /help")
    await message.answer(
        "Я книжковий бот і допомагаю знаходити книги за настроєм та вподобаннями."
    )


@dp.message(Command("age"))
async def age_command(message: Message) -> None:
    logging.info("Користувачу цікаво щодо /age")
    await message.answer("Вікові обмеження відсутні.")


@dp.message(Command("about"))
async def about_command(message: Message) -> None:
    logging.info("Користувачу цікаво /about")
    await message.answer(
        "Підбір книг за бажаними ключовими словами (наприклад: ліс, таємниця, міфи), "
        "настроєм (сумний, веселий, загадковий, злий і т.д.) та жанром "
        "(роман, детектив, психологія, історія і т.д.)."
    )


@dp.message()
async def unknown_message(message: Message) -> None:
    logging.info("Невідоме повідомлення!")


async def main() -> None:
    load_env_file()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Задайте BOT_TOKEN у змінних середовища.")

    async with Bot(token=token) as bot:
        logging.info("Бот почав роботу")
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
