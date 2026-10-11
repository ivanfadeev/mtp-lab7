"""ORM-модели работают с базой, созданной модулем sqlite3."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import make_engine
from api.models import Book, Loan
from library.data import seed
from library.db import connect, create_schema
from library.loans import issue_book


def test_orm_reads_and_writes_sqlite3_database(tmp_path):
    path = tmp_path / "library.db"
    connection = connect(path)
    create_schema(connection)
    seed(connection)
    issue_book(connection, 1, 1)
    connection.close()

    engine = make_engine(f"sqlite:///{path}")
    with Session(engine) as session:
        book = session.scalars(select(Book).where(Book.id == 1)).one()
        assert (book.title, book.author.name) == ("Война и мир",
                                                  "Лев Толстой")
        assert book.copies_available == 2
        loan = session.get(Loan, 1)
        assert loan.reader.name == "Иван Петров"
        assert loan.issued_at.year >= 2026
    engine.dispose()
