"""HTTP API endpoints for the book recommendation bot."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError


def _get_database_url() -> str | None:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url.strip().strip("\"'")

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip("\"'")

    return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database_url = _get_database_url()
    if not database_url:
        raise RuntimeError("Задайте DATABASE_URL у файлі .env.")

    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")

    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )
    app.state.database_engine = engine
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(lifespan=lifespan)


class MoodOption(BaseModel):
    id: int
    name: str


class BookResult(BaseModel):
    title: str
    author: str | None
    description: str | None
    cover_url: str | None


class MoodResult(BaseModel):
    mood: str
    books: list[BookResult]


class SearchRecommendation(BaseModel):
    title: str
    author: str | None


class MoodSearch(BaseModel):
    id: int
    username: str | None
    mood_text: str
    matched_mood: str | None
    created_at: str
    recommendations: list[SearchRecommendation]


class DashboardStats(BaseModel):
    request_count: int
    book_count: int
    mood_count: int
    search_phrase_count: int


@app.get("/api/users-mood", response_model=list[MoodOption])
def get_users_mood() -> list[MoodOption]:
    engine: Engine = app.state.database_engine
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT id, name FROM moods ORDER BY name")
            ).mappings()
            return [MoodOption(id=row["id"], name=row["name"]) for row in rows]
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="Не вдалося отримати список настроїв із бази даних.",
        ) from error


@app.get("/api/result", response_model=MoodResult)
def get_result(mood_id: int = Query(gt=0)) -> MoodResult:
    """Return up to five books associated with the selected mood."""
    engine: Engine = app.state.database_engine
    try:
        with engine.connect() as connection:
            rows = list(
                connection.execute(
                    text(
                        """
                        SELECT m.name AS mood_name,
                               b.title,
                               b.author,
                               b.description,
                               b.cover_url
                        FROM moods AS m
                        LEFT JOIN book_moods AS bm ON bm.mood_id = m.id
                        LEFT JOIN books AS b ON b.id = bm.book_id
                        WHERE m.id = :mood_id
                        ORDER BY b.title
                        LIMIT 5
                        """
                    ),
                    {"mood_id": mood_id},
                ).mappings()
            )

        if not rows:
            raise HTTPException(status_code=404, detail="Настрій не знайдено.")

        books = [
            BookResult(
                title=row["title"],
                author=row["author"],
                description=row["description"],
                cover_url=row["cover_url"],
            )
            for row in rows
            if row["title"] is not None
        ]
        return MoodResult(mood=rows[0]["mood_name"], books=books)
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="Не вдалося отримати рекомендації з бази даних.",
        ) from error


@app.get("/api/admin/mood-searches", response_model=list[MoodSearch])
def get_mood_searches(limit: int = Query(default=100, ge=1, le=500)) -> list[MoodSearch]:
    """Return recent mood searches and the books recommended for each search."""
    engine: Engine = app.state.database_engine
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    WITH recent_searches AS (
                        SELECT id, user_id, mood_text, matched_mood_id, created_at
                        FROM mood_searches
                        ORDER BY created_at DESC, id DESC
                        LIMIT :row_limit
                    )
                    SELECT ms.id, u.username, ms.mood_text,
                           m.name AS matched_mood, ms.created_at,
                           b.title AS book_title, b.author AS book_author,
                           r.position
                    FROM recent_searches AS ms
                    JOIN users AS u ON u.id = ms.user_id
                    LEFT JOIN moods AS m ON m.id = ms.matched_mood_id
                    LEFT JOIN recommendations AS r ON r.mood_search_id = ms.id
                    LEFT JOIN books AS b ON b.id = r.book_id
                    ORDER BY ms.created_at DESC, ms.id DESC, r.position
                    """
                ),
                {"row_limit": limit},
            ).mappings()

        searches: dict[int, MoodSearch] = {}
        for row in rows:
            search = searches.get(row["id"])
            if search is None:
                search = MoodSearch(
                    id=row["id"],
                    username=row["username"],
                    mood_text=row["mood_text"],
                    matched_mood=row["matched_mood"],
                    created_at=row["created_at"].isoformat(),
                    recommendations=[],
                )
                searches[search.id] = search
            if row["book_title"] is not None:
                search.recommendations.append(
                    SearchRecommendation(
                        title=row["book_title"], author=row["book_author"]
                    )
                )
        return list(searches.values())[:limit]
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="Не вдалося отримати історію запитів із бази даних.",
        ) from error


@app.get("/api/admin/stats", response_model=DashboardStats)
def get_dashboard_stats() -> DashboardStats:
    """Return live dashboard totals from the catalog and search history."""
    engine: Engine = app.state.database_engine
    try:
        with engine.connect() as connection:
            counts = connection.execute(
                text(
                    """
                    SELECT (SELECT COUNT(*) FROM mood_searches) AS request_count,
                           (SELECT COUNT(*) FROM books) AS book_count,
                           (SELECT COUNT(*) FROM moods) AS mood_count
                    """
                )
            ).mappings().one()
        # The current bot recognizes the mood catalog names as search phrases.
        return DashboardStats(
            request_count=counts["request_count"],
            book_count=counts["book_count"],
            mood_count=counts["mood_count"],
            search_phrase_count=counts["mood_count"],
        )
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="Не вдалося отримати статистику адмінки з бази даних.",
        ) from error
