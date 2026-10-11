"""Схемы запросов и ответов API (Pydantic)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class AuthorIn(BaseModel):
    """Новый автор."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    country: str = Field(default="", max_length=100)


class AuthorOut(BaseModel):
    """Автор в ответе API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: str


class BookIn(BaseModel):
    """Новая книга."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=300)
    author_id: int
    year: int | None = Field(default=None, ge=1400, le=2100)
    copies_total: int = Field(default=1, ge=0)


class BookUpdate(BaseModel):
    """Изменение книги: передаются только меняемые поля."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=300)
    year: int | None = Field(default=None, ge=1400, le=2100)
    copies_total: int | None = Field(default=None, ge=0)


class BookOut(BaseModel):
    """Книга в ответе API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    year: int | None
    copies_total: int
    copies_available: int
    author: AuthorOut


class ReaderIn(BaseModel):
    """Новый читатель."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    email: str = Field(pattern=EMAIL, max_length=200)


class ReaderOut(BaseModel):
    """Читатель в ответе API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class LoanIn(BaseModel):
    """Запрос на выдачу книги."""

    book_id: int
    reader_id: int


class LoanOut(BaseModel):
    """Выдача в ответе API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    reader_id: int
    issued_at: datetime
    returned_at: datetime | None
