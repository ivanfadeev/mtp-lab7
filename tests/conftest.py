"""Общие фикстуры: база sqlite3 в памяти."""

import pytest

from library.db import connect, create_schema


@pytest.fixture
def connection():
    """Пустая база в памяти со схемой."""
    database = connect()
    create_schema(database)
    yield database
    database.close()
