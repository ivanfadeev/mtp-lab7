"""Подключение SQLAlchemy: движок, фабрика сессий и базовый класс."""

import os
import sqlite3

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase

DEFAULT_URL = "sqlite:///library.db"


class Base(DeclarativeBase):
    """Базовый класс ORM-моделей."""


def make_engine(url: str | None = None, **options: object) -> Engine:
    """Создать движок SQLAlchemy.

    Адрес базы берётся из аргумента, затем из переменной окружения
    DATABASE_URL, иначе используется файл library.db. Для SQLite
    при каждом подключении включаются внешние ключи — по умолчанию
    SQLite их не проверяет.
    """
    engine = create_engine(
        url or os.environ.get("DATABASE_URL", DEFAULT_URL), **options
    )
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", enable_foreign_keys)
    return engine


def enable_foreign_keys(
    connection: sqlite3.Connection, _record: object
) -> None:
    """Включить проверку внешних ключей для нового подключения SQLite."""
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()
