"""REST API библиотеки: FastAPI + SQLAlchemy ORM.

Запуск: uvicorn api.main:create_app --factory --reload
Приложение создаётся фабрикой, поэтому импорт модуля не создаёт файл
базы данных (это важно для тестов).
"""

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from sqlalchemy import Engine, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, sessionmaker

from api.database import Base, make_engine
from api.models import Author, Book, Loan, Reader
from api.schemas import (
    AuthorIn,
    AuthorOut,
    BookIn,
    BookOut,
    BookUpdate,
    LoanIn,
    LoanOut,
    ReaderIn,
    ReaderOut,
)

APP_VERSION = "1.0.0"


def get_session(request: Request) -> Iterator[Session]:
    """Открыть сессию на время запроса и закрыть её после ответа."""
    with request.app.state.sessions() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def not_found(text: str) -> HTTPException:
    """Ошибка 404 — запрошенной записи нет."""
    return HTTPException(status.HTTP_404_NOT_FOUND, text)


def conflict(text: str) -> HTTPException:
    """Ошибка 409 — запрос противоречит текущему состоянию данных."""
    return HTTPException(status.HTTP_409_CONFLICT, text)


def load_book(session: Session, book_id: int) -> Book:
    """Книга с автором или 404."""
    book = session.get(Book, book_id, options=[joinedload(Book.author)])
    if book is None:
        raise not_found("книга не найдена")
    return book


def create_app(engine: Engine | None = None) -> FastAPI:
    """Создать приложение и при необходимости таблицы в базе.

    create_all создаёт только отсутствующие таблицы, поэтому
    приложение можно направить и на базу, заполненную модулем
    library.
    """
    engine = engine if engine is not None else make_engine()
    Base.metadata.create_all(engine)
    app = FastAPI(
        title="Библиотека — API",
        version=APP_VERSION,
        description="Лабораторная работа №7, вариант 7: FastAPI + "
                    "SQLAlchemy.",
    )
    app.state.sessions = sessionmaker(engine, expire_on_commit=False)
    register_author_routes(app)
    register_book_routes(app)
    register_reader_routes(app)
    register_loan_routes(app)
    return app


def register_author_routes(app: FastAPI) -> None:
    """Маршруты /authors."""

    @app.get("/authors", response_model=list[AuthorOut], tags=["Авторы"])
    def list_authors(session: SessionDep) -> list[Author]:
        """Все авторы по алфавиту."""
        return list(session.scalars(select(Author).order_by(Author.name)))

    @app.post("/authors", response_model=AuthorOut,
              status_code=status.HTTP_201_CREATED, tags=["Авторы"])
    def create_author(data: AuthorIn, session: SessionDep) -> Author:
        """Добавить автора; имя должно быть уникальным."""
        author = Author(**data.model_dump())
        try:
            with session.begin():
                session.add(author)
        except IntegrityError:
            raise conflict("такой автор уже есть") from None
        return author


def register_book_routes(app: FastAPI) -> None:
    """Маршруты /books."""

    @app.get("/books", response_model=list[BookOut], tags=["Книги"])
    def list_books(
        session: SessionDep,
        q: Annotated[str, Query(max_length=100)] = "",
        available: bool = False,
    ) -> list[Book]:
        """Книги с авторами; поиск по названию и фильтр «в наличии»."""
        query = select(Book).options(joinedload(Book.author)).order_by(
            Book.title
        )
        if available:
            query = query.where(Book.copies_available > 0)
        books = list(session.scalars(query))
        needle = q.strip().casefold()
        return [book for book in books if needle in book.title.casefold()]

    @app.post("/books", response_model=BookOut,
              status_code=status.HTTP_201_CREATED, tags=["Книги"])
    def create_book(data: BookIn, session: SessionDep) -> Book:
        """Добавить книгу; все экземпляры сначала свободны."""
        with session.begin():
            if session.get(Author, data.author_id) is None:
                raise not_found("автор не найден")
            book = Book(**data.model_dump(),
                        copies_available=data.copies_total)
            session.add(book)
        return load_book(session, book.id)

    @app.get("/books/{book_id}", response_model=BookOut, tags=["Книги"])
    def read_book(book_id: int, session: SessionDep) -> Book:
        """Одна книга."""
        return load_book(session, book_id)

    @app.patch("/books/{book_id}", response_model=BookOut, tags=["Книги"])
    def update_book(book_id: int, data: BookUpdate,
                    session: SessionDep) -> Book:
        """Изменить книгу.

        При изменении числа экземпляров свободные меняются на ту же
        величину; уменьшить общее число ниже числа выданных нельзя.
        """
        with session.begin():
            book = load_book(session, book_id)
            fields = data.model_dump(exclude_unset=True)
            new_total = fields.pop("copies_total", None)
            if new_total is not None:
                available = book.copies_available + new_total - (
                    book.copies_total
                )
                if available < 0:
                    raise conflict("часть экземпляров сейчас выдана")
                book.copies_total = new_total
                book.copies_available = available
            for name, value in fields.items():
                setattr(book, name, value)
        return load_book(session, book_id)

    @app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT,
                tags=["Книги"])
    def delete_book(book_id: int, session: SessionDep) -> None:
        """Удалить книгу, если по ней не было выдач."""
        with session.begin():
            book = load_book(session, book_id)
            has_loans = session.scalar(
                select(exists().where(Loan.book_id == book_id))
            )
            if has_loans:
                raise conflict("по книге есть записи о выдаче")
            session.delete(book)


def register_reader_routes(app: FastAPI) -> None:
    """Маршруты /readers."""

    @app.get("/readers", response_model=list[ReaderOut], tags=["Читатели"])
    def list_readers(session: SessionDep) -> list[Reader]:
        """Все читатели по имени."""
        return list(session.scalars(select(Reader).order_by(Reader.name)))

    @app.post("/readers", response_model=ReaderOut,
              status_code=status.HTTP_201_CREATED, tags=["Читатели"])
    def create_reader(data: ReaderIn, session: SessionDep) -> Reader:
        """Зарегистрировать читателя; почта должна быть уникальной."""
        reader = Reader(**data.model_dump())
        try:
            with session.begin():
                session.add(reader)
        except IntegrityError:
            raise conflict("читатель с такой почтой уже есть") from None
        return reader


def register_loan_routes(app: FastAPI) -> None:
    """Маршруты /loans: выдача и возврат книг в транзакциях."""

    @app.get("/loans", response_model=list[LoanOut], tags=["Выдачи"])
    def list_loans(session: SessionDep, active: bool = False) -> list[Loan]:
        """Выдачи; active=true — только невозвращённые."""
        query = select(Loan).order_by(Loan.id)
        if active:
            query = query.where(Loan.returned_at.is_(None))
        return list(session.scalars(query))

    @app.post("/loans", response_model=LoanOut,
              status_code=status.HTTP_201_CREATED, tags=["Выдачи"])
    def issue_book(data: LoanIn, session: SessionDep) -> Loan:
        """Выдать книгу: уменьшить остаток и записать выдачу атомарно."""
        with session.begin():
            book = session.get(Book, data.book_id)
            if book is None:
                raise not_found("книга не найдена")
            if session.get(Reader, data.reader_id) is None:
                raise not_found("читатель не найден")
            if book.copies_available == 0:
                raise conflict("свободных экземпляров нет")
            book.copies_available -= 1
            loan = Loan(book_id=book.id, reader_id=data.reader_id)
            session.add(loan)
        session.refresh(loan)
        return loan

    @app.post("/loans/{loan_id}/return", response_model=LoanOut,
              tags=["Выдачи"])
    def return_book(loan_id: int, session: SessionDep) -> Loan:
        """Принять книгу: отметить возврат и вернуть экземпляр атомарно."""
        with session.begin():
            loan = session.get(Loan, loan_id)
            if loan is None:
                raise not_found("выдача не найдена")
            if loan.returned_at is not None:
                raise conflict("книга уже возвращена")
            loan.returned_at = datetime.now(timezone.utc).replace(
                microsecond=0, tzinfo=None
            )
            loan.book.copies_available += 1
        return loan
