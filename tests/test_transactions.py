"""Тесты транзакций: выдача, возврат и пакетная вставка."""

import sqlite3

import pytest

from library.db import transaction
from library.loans import (
    AlreadyReturnedError,
    NotAvailableError,
    add_books,
    issue_book,
    return_book,
)


def available(connection, book_id):
    return connection.execute(
        "SELECT copies_available FROM books WHERE id = ?", (book_id,)
    ).fetchone()[0]


def count(connection, table):
    return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def loans_count(connection):
    return count(connection, "loans")


def test_issue_changes_both_tables(library):
    loan_id = issue_book(library, 1, 1)
    assert available(library, 1) == 2
    row = library.execute("SELECT * FROM loans WHERE id = ?",
                          (loan_id,)).fetchone()
    assert (row["book_id"], row["reader_id"], row["returned_at"]) == (
        1, 1, None,
    )


def test_no_copies_left(library):
    issue_book(library, 7, 1)
    with pytest.raises(NotAvailableError):
        issue_book(library, 7, 2)
    assert (available(library, 7), loans_count(library)) == (0, 1)


def test_unknown_book(library):
    with pytest.raises(NotAvailableError):
        issue_book(library, 999, 1)


def test_failed_insert_rolls_back_update(library):
    with pytest.raises(sqlite3.IntegrityError):
        issue_book(library, 1, 999)
    assert available(library, 1) == 3
    assert loans_count(library) == 0


def test_return_book(library):
    loan_id = issue_book(library, 4, 3)
    return_book(library, loan_id)
    assert available(library, 4) == 1
    with pytest.raises(AlreadyReturnedError):
        return_book(library, loan_id)


def test_batch_is_all_or_nothing(library):
    before = count(library, "books")
    with pytest.raises(sqlite3.IntegrityError):
        add_books(library, [("Нос", 1, 1836, 1), ("Шинель", 999, 1842, 1)])
    assert count(library, "books") == before
    assert add_books(library, [("Нос", 1, 1836, 1)]) == 1


def test_transaction_rolls_back_on_any_error(connection):
    with pytest.raises(RuntimeError):
        with transaction(connection):
            connection.execute("INSERT INTO authors (name) VALUES ('А')")
            raise RuntimeError("сбой посреди операции")
    assert count(connection, "authors") == 0
    assert not connection.in_transaction


def test_transaction_commits(connection):
    with transaction(connection):
        connection.execute("INSERT INTO authors (name) VALUES ('А')")
        connection.execute("INSERT INTO authors (name) VALUES ('Б')")
    assert count(connection, "authors") == 2
