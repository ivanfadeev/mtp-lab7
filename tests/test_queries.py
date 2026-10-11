"""Тесты выборки данных из таблиц."""

from library.data import (
    BOOKS,
    active_loans,
    books_per_author,
    books_with_authors,
    find_books,
)


def test_books_with_authors(library):
    rows = books_with_authors(library)
    assert len(rows) == len(BOOKS)
    first = rows[0]
    assert (first["title"], first["author"]) == ("1984", "Джордж Оруэлл")
    assert first.keys() == ["id", "title", "author", "year",
                            "copies_available", "copies_total"]


def test_available_only(library):
    library.execute("UPDATE books SET copies_available = 0 WHERE id = 1")
    titles = {row["title"] for row in books_with_authors(library, True)}
    assert "Война и мир" not in titles
    assert len(titles) == len(BOOKS) - 1


def test_find_is_case_insensitive_for_cyrillic(library):
    assert [r["title"] for r in find_books(library, "ТОЛСТ")] == [
        "Анна Каренина", "Война и мир",
    ]
    assert [r["title"] for r in find_books(library, "мастер")] == [
        "Мастер и Маргарита",
    ]


def test_find_treats_input_as_data(library):
    assert find_books(library, "' OR 1=1 --") == []


def test_books_per_author(library):
    rows = {row["author"]: (row["books"], row["copies"])
            for row in books_per_author(library)}
    assert rows["Лев Толстой"] == (2, 5)
    assert rows["Рэй Брэдбери"] == (1, 1)


def test_author_without_books_is_listed(library):
    library.execute("INSERT INTO authors (name) VALUES ('Новый автор')")
    rows = {row["author"]: row["books"] for row in books_per_author(library)}
    assert rows["Новый автор"] == 0


def test_active_loans_join(library):
    library.execute("INSERT INTO loans (book_id, reader_id) VALUES (6, 2)")
    rows = active_loans(library)
    assert [(r["reader"], r["title"]) for r in rows] == [
        ("Мария Соколова", "1984"),
    ]
