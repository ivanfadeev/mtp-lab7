"""Заполнение базы и выборка данных."""

import sqlite3

from library.db import transaction

AUTHORS = [
    ("Лев Толстой", "Россия"),
    ("Фёдор Достоевский", "Россия"),
    ("Михаил Булгаков", "Россия"),
    ("Джордж Оруэлл", "Великобритания"),
    ("Рэй Брэдбери", "США"),
]
BOOKS = [
    ("Война и мир", "Лев Толстой", 1869, 3),
    ("Анна Каренина", "Лев Толстой", 1878, 2),
    ("Преступление и наказание", "Фёдор Достоевский", 1866, 4),
    ("Идиот", "Фёдор Достоевский", 1869, 1),
    ("Мастер и Маргарита", "Михаил Булгаков", 1967, 2),
    ("1984", "Джордж Оруэлл", 1949, 2),
    ("451 градус по Фаренгейту", "Рэй Брэдбери", 1953, 1),
]
READERS = [
    ("Иван Петров", "ivan.petrov@example.ru"),
    ("Мария Соколова", "m.sokolova@example.ru"),
    ("Алексей Морозов", "morozov@example.ru"),
]


def seed(connection: sqlite3.Connection) -> None:
    """Заполнить пустую базу демонстрационными данными одной транзакцией."""
    with transaction(connection):
        connection.executemany(
            "INSERT INTO authors (name, country) VALUES (?, ?)", AUTHORS
        )
        connection.executemany(
            "INSERT INTO books (title, author_id, year, copies_total, "
            "copies_available) "
            "SELECT ?, id, ?, ?, ? FROM authors WHERE name = ?",
            [(title, year, copies, copies, author)
             for title, author, year, copies in BOOKS],
        )
        connection.executemany(
            "INSERT INTO readers (name, email) VALUES (?, ?)", READERS
        )


def books_with_authors(
    connection: sqlite3.Connection, available_only: bool = False
) -> list[sqlite3.Row]:
    """Книги с именами авторов (JOIN), по автору и году издания."""
    query = (
        "SELECT b.id, b.title, a.name AS author, b.year, "
        "b.copies_available, b.copies_total "
        "FROM books AS b JOIN authors AS a ON a.id = b.author_id "
    )
    if available_only:
        query += "WHERE b.copies_available > 0 "
    query += "ORDER BY a.name, b.year"
    return connection.execute(query).fetchall()


def find_books(connection: sqlite3.Connection, text: str) -> list[sqlite3.Row]:
    """Книги, в названии или имени автора которых есть text.

    Поиск не зависит от регистра, в том числе для кириллицы. Значение
    передаётся параметром, а не подставляется в строку запроса,
    поэтому SQL-инъекция невозможна.
    """
    pattern = f"%{text.casefold()}%"
    return connection.execute(
        "SELECT b.id, b.title, a.name AS author, b.year "
        "FROM books AS b JOIN authors AS a ON a.id = b.author_id "
        "WHERE casefold(b.title) LIKE ? OR casefold(a.name) LIKE ? "
        "ORDER BY b.title",
        (pattern, pattern),
    ).fetchall()


def books_per_author(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    """Число книг и экземпляров у каждого автора (GROUP BY)."""
    return connection.execute(
        "SELECT a.name AS author, COUNT(b.id) AS books, "
        "COALESCE(SUM(b.copies_total), 0) AS copies "
        "FROM authors AS a LEFT JOIN books AS b ON b.author_id = a.id "
        "GROUP BY a.id ORDER BY books DESC, a.name"
    ).fetchall()


def active_loans(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    """Невозвращённые книги: кто и что взял (JOIN трёх таблиц)."""
    return connection.execute(
        "SELECT l.id, r.name AS reader, b.title, l.issued_at "
        "FROM loans AS l "
        "JOIN readers AS r ON r.id = l.reader_id "
        "JOIN books AS b ON b.id = l.book_id "
        "WHERE l.returned_at IS NULL ORDER BY l.id"
    ).fetchall()
