"""Тесты экспорта в CSV."""

import csv

from library.export import export_books, export_query


def read_csv(path, delimiter=","):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.reader(stream, delimiter=delimiter))


def test_export_books(library, tmp_path):
    path = tmp_path / "out" / "books.csv"
    assert export_books(library, path) == 7
    rows = read_csv(path)
    assert rows[0] == ["id", "название", "автор", "год", "в_наличии",
                       "всего"]
    assert rows[1] == ["1", "Война и мир", "Лев Толстой", "1869", "3", "3"]
    assert len(rows) == 8


def test_file_starts_with_bom_for_excel(library, tmp_path):
    path = tmp_path / "books.csv"
    export_books(library, path)
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")


def test_special_characters_are_quoted(connection, tmp_path):
    connection.execute(
        "INSERT INTO authors (name, country) VALUES (?, ?)",
        ('Автор, "в кавычках"', "строка\nвторая"),
    )
    path = tmp_path / "authors.csv"
    export_query(connection, "SELECT name, country FROM authors", path)
    assert read_csv(path)[1] == ['Автор, "в кавычках"', "строка\nвторая"]


def test_empty_result_has_header(connection, tmp_path):
    path = tmp_path / "empty.csv"
    assert export_query(connection, "SELECT id, name FROM authors",
                        path) == 0
    assert read_csv(path) == [["id", "name"]]


def test_semicolon_delimiter_and_params(library, tmp_path):
    path = tmp_path / "ru.csv"
    count = export_query(
        library,
        "SELECT title, year FROM books WHERE year < ? ORDER BY year",
        path,
        params=(1868,),
        delimiter=";",
    )
    assert count == 1
    assert read_csv(path, ";")[1] == ["Преступление и наказание", "1866"]
