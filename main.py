"""Лабораторная работа №7: работа с базами данных из Python.

Демонстрация модуля sqlite3: несколько таблиц, выборки, транзакции и
экспорт в CSV.
Автор: Фадеев Иван Александрович, группа 221141, вариант 7.
"""

import argparse
import sqlite3
from pathlib import Path

from library.data import (
    active_loans,
    books_per_author,
    books_with_authors,
    find_books,
    seed,
)
from library.db import TABLES, connect, create_schema, table_names
from library.export import export_books
from library.loans import NotAvailableError, add_books, issue_book, return_book

APP_NAME = "lab7"
APP_VERSION = "1.0.0"


def build_parser() -> argparse.ArgumentParser:
    """Собрать разбор аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description="Библиотека на sqlite3 (лабораторная №7, вариант 7)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {APP_VERSION}",
    )
    parser.add_argument(
        "--db",
        default=":memory:",
        help="файл базы; по умолчанию база создаётся в памяти",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("export/books.csv"),
        help="куда выгрузить каталог (по умолчанию export/books.csv)",
    )
    return parser


def copies(connection: sqlite3.Connection, book_id: int) -> int:
    """Число свободных экземпляров книги."""
    row = connection.execute(
        "SELECT copies_available FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    return row["copies_available"]


def show_tables(connection: sqlite3.Connection) -> None:
    """Показать созданные таблицы и число строк в каждой."""
    print("== Таблицы базы ==")
    for name in table_names(connection):
        if name not in TABLES:
            continue
        # имя таблицы нельзя передать параметром «?», поэтому в запрос
        # подставляются только имена из белого списка TABLES
        count = connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()
        print(f"  {name:<16} строк: {count[0]}")


def show_selects(connection: sqlite3.Connection) -> None:
    """Показать выборки данных."""
    print("\n== Каталог (JOIN books + authors) ==")
    for row in books_with_authors(connection):
        print(f"  {row['id']}. {row['title']} — {row['author']}, "
              f"{row['year']} ({row['copies_available']} из "
              f"{row['copies_total']})")
    print("\n== Поиск «ТОЛСТ» (без учёта регистра) ==")
    for row in find_books(connection, "ТОЛСТ"):
        print(f"  {row['title']} — {row['author']}")
    print("\n== Книг у автора (GROUP BY) ==")
    for row in books_per_author(connection):
        print(f"  {row['author']:<20} книг: {row['books']}, "
              f"экземпляров: {row['copies']}")


def show_transactions(connection: sqlite3.Connection) -> None:
    """Показать работу транзакций и их откат."""
    print("\n== Транзакции ==")
    loan = issue_book(connection, book_id=7, reader_id=1)
    print(f"выдача №{loan}: книга 7 → читатель 1, свободно: "
          f"{copies(connection, 7)}")
    try:
        issue_book(connection, book_id=7, reader_id=2)
    except NotAvailableError as error:
        print(f"повторная выдача книги 7 → откат: {error}, свободно: "
              f"{copies(connection, 7)}")
    before = copies(connection, 1)
    try:
        issue_book(connection, book_id=1, reader_id=999)
    except sqlite3.IntegrityError as error:
        print(f"выдача несуществующему читателю → откат ({error}), "
              f"свободно было {before}, стало {copies(connection, 1)}")
    batch = [("Белая гвардия", 3, 1925, 2), ("Бесы", 2, 1872, -1)]
    try:
        add_books(connection, batch)
    except sqlite3.IntegrityError as error:
        total = connection.execute("SELECT COUNT(*) FROM books").fetchone()
        print(f"партия из 2 книг с ошибкой во второй → откат ({error}), "
              f"книг в базе: {total[0]}")
    print("невозвращённые книги:")
    for row in active_loans(connection):
        print(f"  выдача №{row['id']}: {row['reader']} — {row['title']}")
    return_book(connection, loan)
    print(f"книга 7 возвращена, свободно: {copies(connection, 7)}")


def main(argv: list[str] | None = None) -> None:
    """Создать и заполнить базу, показать выборки, транзакции и экспорт."""
    args = build_parser().parse_args(argv)
    connection = connect(args.db)
    try:
        create_schema(connection)
        if not connection.execute("SELECT 1 FROM authors").fetchone():
            seed(connection)
        show_tables(connection)
        show_selects(connection)
        show_transactions(connection)
        rows = export_books(connection, args.csv)
        print(f"\n== Экспорт в CSV ==\nзаписано строк: {rows}, файл "
              f"{args.csv}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
