"""Общие фикстуры: база sqlite3 в памяти."""

import pytest

from library.data import seed
from library.db import connect, create_schema


@pytest.fixture
def connection():
    """Пустая база в памяти со схемой."""
    database = connect()
    create_schema(database)
    yield database
    database.close()


@pytest.fixture
def library(connection):
    """База в памяти с демонстрационными данными."""
    seed(connection)
    return connection
