"""Тесты создания нескольких связанных таблиц."""

import sqlite3

import pytest

from library.db import TABLES, connect, create_schema, table_names


def test_all_tables_created(connection):
    assert set(TABLES) <= set(table_names(connection))


def test_schema_can_be_created_twice(connection):
    create_schema(connection)
    assert set(TABLES) <= set(table_names(connection))


def test_foreign_keys_link_tables(connection):
    links = {
        (table, row["table"], row["from"])
        for table in TABLES
        for row in connection.execute(f"PRAGMA foreign_key_list({table})")
    }
    assert links == {
        ("books", "authors", "author_id"),
        ("loans", "books", "book_id"),
        ("loans", "readers", "reader_id"),
    }


def test_foreign_keys_are_enforced(connection):
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO books (title, author_id, copies_total, "
            "copies_available) VALUES ('X', 42, 1, 1)"
        )


@pytest.mark.parametrize(
    "year, total, available",
    [(1200, 1, 1), (2000, -1, 0), (2000, 1, 2), (2000, 2, -1)],
)
def test_check_constraints(connection, year, total, available):
    connection.execute("INSERT INTO authors (name) VALUES ('А')")
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO books (title, author_id, year, copies_total, "
            "copies_available) VALUES ('X', 1, ?, ?, ?)",
            (year, total, available),
        )


def test_unique_email(connection):
    connection.execute(
        "INSERT INTO readers (name, email) VALUES ('А', 'a@b.c')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO readers (name, email) VALUES ('Б', 'a@b.c')"
        )


def test_file_database_persists(tmp_path):
    path = tmp_path / "lib.db"
    first = connect(path)
    create_schema(first)
    first.execute("INSERT INTO authors (name) VALUES ('Гоголь')")
    first.close()
    second = connect(path)
    assert second.execute("SELECT name FROM authors").fetchone()[0] == (
        "Гоголь"
    )
    second.close()
