"""Подключение к SQLite, схема из нескольких таблиц и транзакции."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS authors (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    country    TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS books (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT NOT NULL,
    author_id        INTEGER NOT NULL REFERENCES authors(id),
    year             INTEGER CHECK (year BETWEEN 1400 AND 2100),
    copies_total     INTEGER NOT NULL CHECK (copies_total >= 0),
    copies_available INTEGER NOT NULL
        CHECK (copies_available BETWEEN 0 AND copies_total)
);

CREATE TABLE IF NOT EXISTS readers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS loans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL REFERENCES books(id),
    reader_id   INTEGER NOT NULL REFERENCES readers(id),
    issued_at   TEXT NOT NULL DEFAULT (datetime('now')),
    returned_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_books_author ON books(author_id);
CREATE INDEX IF NOT EXISTS idx_loans_book ON loans(book_id);
CREATE INDEX IF NOT EXISTS idx_loans_reader ON loans(reader_id);
"""

TABLES = ("authors", "books", "readers", "loans")


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    """Открыть базу с включёнными внешними ключами.

    Соединение работает в режиме автофиксации (isolation_level=None):
    одиночные запросы фиксируются сразу, а несколько связанных
    изменений объединяются явно через transaction(). Строки
    результатов доступны и по индексу, и по имени столбца. В запросах
    доступна функция casefold() — приведение регистра, которое, в
    отличие от встроенных LOWER и LIKE в SQLite, работает и для
    кириллицы.
    """
    connection = sqlite3.connect(str(path), isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.create_function("casefold", 1, str.casefold,
                               deterministic=True)
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    """Создать таблицы authors, books, readers, loans и индексы.

    Повторный вызов ничего не ломает: используется IF NOT EXISTS.
    """
    with transaction(connection):
        for statement in SCHEMA.split(";"):
            if statement.strip():
                connection.execute(statement)


def table_names(connection: sqlite3.Connection) -> list[str]:
    """Имена пользовательских таблиц базы по алфавиту."""
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row["name"] for row in rows]


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[None]:
    """Выполнить блок как одну транзакцию: всё или ничего.

    BEGIN IMMEDIATE сразу берёт блокировку записи, поэтому другой
    процесс не изменит данные между проверкой и записью. При любом
    исключении внутри блока выполняется ROLLBACK, и база остаётся в
    состоянии до транзакции; иначе — COMMIT.
    """
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        connection.execute("ROLLBACK")
        raise
    connection.execute("COMMIT")
