"""Database operations for book recommendations."""

from sqlalchemy import Engine, text


def save_mood_search_and_find_books(
    engine: Engine,
    telegram_id: int,
    username: str | None,
    mood_text: str,
) -> tuple[str | None, list[dict[str, object]], list[str]]:
    """Save a user's mood search and return matching books and known moods."""
    with engine.begin() as connection:
        user_id = connection.execute(
            text(
                """
                INSERT INTO users (telegram_id, username)
                VALUES (:telegram_id, :username)
                ON CONFLICT (telegram_id) DO UPDATE
                SET username = COALESCE(EXCLUDED.username, users.username)
                RETURNING id
                """
            ),
            {"telegram_id": telegram_id, "username": username},
        ).scalar_one()

        moods = list(
            connection.execute(
                text("SELECT id, name FROM moods ORDER BY name")
            ).mappings()
        )
        normalized_text = mood_text.casefold()
        matched_mood = next(
            (mood for mood in moods if mood["name"].casefold() in normalized_text),
            None,
        )

        search_id = connection.execute(
            text(
                """
                INSERT INTO mood_searches (user_id, mood_text, matched_mood_id)
                VALUES (:user_id, :mood_text, :matched_mood_id)
                RETURNING id
                """
            ),
            {
                "user_id": user_id,
                "mood_text": mood_text,
                "matched_mood_id": matched_mood["id"] if matched_mood else None,
            },
        ).scalar_one()

        books: list[dict[str, object]] = []
        if matched_mood:
            books = [
                dict(book)
                for book in connection.execute(
                    text(
                        """
                        SELECT b.id, b.title, b.author, b.description, b.cover_url
                        FROM books AS b
                        JOIN book_moods AS bm ON bm.book_id = b.id
                        WHERE bm.mood_id = :mood_id
                        ORDER BY b.title
                        LIMIT 5
                        """
                    ),
                    {"mood_id": matched_mood["id"]},
                ).mappings()
            ]

            for position, book in enumerate(books, start=1):
                connection.execute(
                    text(
                        """
                        INSERT INTO recommendations (mood_search_id, book_id, position)
                        VALUES (:mood_search_id, :book_id, :position)
                        """
                    ),
                    {
                        "mood_search_id": search_id,
                        "book_id": book["id"],
                        "position": position,
                    },
                )

        known_moods = [str(mood["name"]) for mood in moods]
        matched_mood_name = str(matched_mood["name"]) if matched_mood else None
        return matched_mood_name, books, known_moods
