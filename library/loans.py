"""Выдача и возврат книг — операции в транзакциях."""

import sqlite3
from collections.abc import Iterable

from library.db import transaction


class NotAvailableError(Exception):
    """Свободных экземпляров книги нет или книга не найдена."""


class AlreadyReturnedError(Exception):
    """Выдача не найдена или книга по ней уже возвращена."""


def issue_book(connection: sqlite3.Connection, book_id: int,
               reader_id: int) -> int:
    """Выдать книгу читателю и вернуть id записи о выдаче.

    Два изменения — уменьшение числа свободных экземпляров и запись
    в loans — выполняются в одной транзакции. Если второе не удастся
    (например, такого читателя нет и срабатывает внешний ключ), первое
    тоже откатится, и число экземпляров останется прежним.
    """
    with transaction(connection):
        updated = connection.execute(
            "UPDATE books SET copies_available = copies_available - 1 "
            "WHERE id = ? AND copies_available > 0",
            (book_id,),
        ).rowcount
        if updated == 0:
            raise NotAvailableError(f"книга {book_id} недоступна")
        cursor = connection.execute(
            "INSERT INTO loans (book_id, reader_id) VALUES (?, ?)",
            (book_id, reader_id),
        )
    return cursor.lastrowid


def return_book(connection: sqlite3.Connection, loan_id: int) -> None:
    """Принять книгу обратно: отметить выдачу и вернуть экземпляр.

    Обе записи меняются в одной транзакции.
    """
    with transaction(connection):
        row = connection.execute(
            "SELECT book_id FROM loans WHERE id = ? AND returned_at IS NULL",
            (loan_id,),
        ).fetchone()
        if row is None:
            raise AlreadyReturnedError(f"выдача {loan_id} не активна")
        connection.execute(
            "UPDATE loans SET returned_at = datetime('now') WHERE id = ?",
            (loan_id,),
        )
        connection.execute(
            "UPDATE books SET copies_available = copies_available + 1 "
            "WHERE id = ?",
            (row["book_id"],),
        )


def add_books(connection: sqlite3.Connection,
              books: Iterable[tuple[str, int, int, int]]) -> int:
    """Добавить партию книг (название, id автора, год, экземпляров).

    Партия добавляется целиком или не добавляется совсем: если
    хотя бы одна строка нарушает ограничения базы, откатывается вся
    вставка. Возвращает число добавленных книг.
    """
    rows = [(title, author, year, copies, copies)
            for title, author, year, copies in books]
    with transaction(connection):
        connection.executemany(
            "INSERT INTO books (title, author_id, year, copies_total, "
            "copies_available) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
    return len(rows)
