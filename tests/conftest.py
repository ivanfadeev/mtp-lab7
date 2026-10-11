"""Общие фикстуры: база sqlite3 в памяти и клиент REST API."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

from api.database import make_engine
from api.main import create_app
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


@pytest.fixture
def client():
    """Клиент API с отдельной базой в памяти на каждый тест.

    StaticPool отдаёт всем сессиям одно и то же подключение — иначе
    у каждого подключения была бы своя пустая база в памяти.
    """
    engine = make_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield TestClient(create_app(engine))
    engine.dispose()
