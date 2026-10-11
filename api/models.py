"""ORM-модели таблиц библиотеки.

Модели описывают те же таблицы, что и схема в library/db.py, поэтому
API может работать с базой, созданной модулем sqlite3, и наоборот.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base

AUTOINCREMENT = {"sqlite_autoincrement": True}


class Author(Base):
    """Автор."""

    __tablename__ = "authors"
    __table_args__ = AUTOINCREMENT

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    country: Mapped[str] = mapped_column(String, default="",
                                         server_default="")
    books: Mapped[list["Book"]] = relationship(back_populates="author")


class Book(Base):
    """Книга и число её экземпляров."""

    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("year BETWEEN 1400 AND 2100"),
        CheckConstraint("copies_total >= 0"),
        CheckConstraint("copies_available BETWEEN 0 AND copies_total"),
        AUTOINCREMENT,
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"),
                                           index=True)
    year: Mapped[int | None]
    copies_total: Mapped[int]
    copies_available: Mapped[int]
    author: Mapped[Author] = relationship(back_populates="books")
    loans: Mapped[list["Loan"]] = relationship(back_populates="book")


class Reader(Base):
    """Читатель."""

    __tablename__ = "readers"
    __table_args__ = AUTOINCREMENT

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True)
    loans: Mapped[list["Loan"]] = relationship(back_populates="reader")


class Loan(Base):
    """Выдача книги читателю; returned_at пусто, пока книга не возвращена."""

    __tablename__ = "loans"
    __table_args__ = AUTOINCREMENT

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)
    reader_id: Mapped[int] = mapped_column(ForeignKey("readers.id"),
                                           index=True)
    issued_at: Mapped[datetime] = mapped_column(
        server_default=func.datetime("now")
    )
    returned_at: Mapped[datetime | None]
    book: Mapped[Book] = relationship(back_populates="loans")
    reader: Mapped[Reader] = relationship(back_populates="loans")
