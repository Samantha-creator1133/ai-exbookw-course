"""Minimal aiogram 3.x Telegram bot."""

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from app.database import save_mood_search_and_find_books


logging.basicConfig(level=logging.INFO)

dp = Dispatcher(storage=MemoryStorage())
database_engine: Engine | None = None


class MoodSearch(StatesGroup):
    waiting_for_mood = State()


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
        "Я книжковий бот і допомагаю знаходити книги за настроєм та вподобаннями.\n"
        "Щоб підібрати книгу за настроєм, введи /mood."
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


@dp.message(Command("mood"))
async def mood_command(message: Message, state: FSMContext) -> None:
    logging.info("Користувач викликав /mood")
    await state.set_state(MoodSearch.waiting_for_mood)
    await message.answer(
        "Напиши свій настрій, наприклад: веселий, сумний, загадковий або злий."
    )


@dp.message(MoodSearch.waiting_for_mood)
async def receive_mood(message: Message, state: FSMContext) -> None:
    mood_text = (message.text or "").strip()
    if not mood_text:
        await message.answer("Будь ласка, напиши свій настрій текстом.")
        return

    await state.clear()
    if database_engine is None:
        logging.error("База даних не ініціалізована.")
        await message.answer("Не вдалося звернутися до каталогу книг. Спробуй пізніше.")
        return

    user = message.from_user
    if user is None:
        await message.answer("Не вдалося визначити користувача. Спробуй ще раз.")
        return

    try:
        matched_mood, books, known_moods = await asyncio.to_thread(
            save_mood_search_and_find_books,
            database_engine,
            user.id,
            user.username,
            mood_text,
        )
    except Exception:
        logging.error("Помилка під час пошуку рекомендацій у базі даних.")
        await message.answer("Не вдалося підібрати книги зараз. Спробуй пізніше.")
        return

    if not known_moods:
        await message.answer(
            "Запит збережено, але каталог настроїв і книг поки порожній. "
            "Спершу потрібно додати настрої та книги до каталогу."
        )
        return

    if matched_mood is None:
        await message.answer(
            "Не знайшла відповідний настрій. Спробуй один із цих: "
            f"{', '.join(known_moods)}."
        )
        return

    if not books:
        await message.answer(
            f"Для настрою «{matched_mood}» поки немає книг у каталозі."
        )
        return

    recommendations = []
    for position, book in enumerate(books, start=1):
        author = book["author"] or "автор невідомий"
        item = f"{position}. {book['title']} — {author}"
        description = (book["description"] or "").strip()
        if description:
            item += f"\n{description[:300]}"
        if book["cover_url"]:
            item += f"\nОбкладинка: {book['cover_url']}"
        recommendations.append(item)

    await message.answer(
        f"Ось книги для настрою «{matched_mood}»:\n\n"
        + "\n\n".join(recommendations)
    )


@dp.message()
async def unknown_message(message: Message) -> None:
    logging.info("Невідоме повідомлення!")


async def main() -> None:
    global database_engine

    load_env_file()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Задайте BOT_TOKEN у змінних середовища.")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Задайте DATABASE_URL у файлі .env.")

    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    database_engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )

    try:
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        async with Bot(token=token) as bot:
            logging.info("Бот почав роботу")
            await dp.start_polling(bot)
    finally:
        database_engine.dispose()
        database_engine = None


if __name__ == "__main__":
    asyncio.run(main())
