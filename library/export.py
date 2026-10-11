"""Экспорт результатов запросов в CSV."""

import csv
import sqlite3
from pathlib import Path


def export_query(
    connection: sqlite3.Connection,
    query: str,
    path: str | Path,
    params: tuple = (),
    delimiter: str = ",",
) -> int:
    """Записать результат запроса в CSV и вернуть число строк данных.

    Первая строка файла — имена столбцов из cursor.description, так
    что заголовок есть даже у пустого результата. Файл пишется в
    кодировке UTF-8 с BOM (utf-8-sig): так Excel правильно открывает
    кириллицу. Значения с разделителем, кавычками или переводом строки
    экранируются модулем csv.
    """
    cursor = connection.execute(query, params)
    header = [column[0] for column in cursor.description]
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with target.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, delimiter=delimiter)
        writer.writerow(header)
        for row in cursor:
            writer.writerow(tuple(row))
            count += 1
    return count


def export_books(connection: sqlite3.Connection, path: str | Path,
                 delimiter: str = ",") -> int:
    """Выгрузить каталог книг с авторами и остатками в CSV."""
    return export_query(
        connection,
        "SELECT b.id, b.title AS название, a.name AS автор, "
        "b.year AS год, b.copies_available AS в_наличии, "
        "b.copies_total AS всего "
        "FROM books AS b JOIN authors AS a ON a.id = b.author_id "
        "ORDER BY b.id",
        path,
        delimiter=delimiter,
    )
