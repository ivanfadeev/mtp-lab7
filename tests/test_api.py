"""Тесты REST API на FastAPI + SQLAlchemy."""

import pytest


@pytest.fixture
def filled(client):
    """API с автором, книгой в двух экземплярах и читателем."""
    author = client.post("/authors", json={"name": "Лев Толстой",
                                           "country": "Россия"}).json()
    book = client.post("/books", json={"title": "Война и мир",
                                       "author_id": author["id"],
                                       "year": 1869,
                                       "copies_total": 2}).json()
    reader = client.post("/readers", json={"name": "Иван",
                                           "email": "ivan@example.ru"}).json()
    return client, author, book, reader


def test_authors_crud(client):
    response = client.post("/authors", json={"name": "  Гоголь "})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "Гоголь", "country": ""}
    assert client.post("/authors", json={"name": "Гоголь"}).status_code == 409
    assert [a["name"] for a in client.get("/authors").json()] == ["Гоголь"]


def test_book_created_with_author(filled):
    _, author, book, _ = filled
    assert book["author"] == author
    assert (book["copies_total"], book["copies_available"]) == (2, 2)


def test_book_requires_existing_author(client):
    response = client.post("/books", json={"title": "X", "author_id": 5})
    assert response.status_code == 404


def test_book_list_search_and_filter(filled):
    client, author, _, reader = filled
    client.post("/books", json={"title": "Анна Каренина",
                                "author_id": author["id"],
                                "copies_total": 1})
    titles = [b["title"] for b in client.get("/books").json()]
    assert titles == ["Анна Каренина", "Война и мир"]
    found = client.get("/books", params={"q": "ВОЙНА"}).json()
    assert [b["title"] for b in found] == ["Война и мир"]
    client.post("/loans", json={"book_id": 2, "reader_id": reader["id"]})
    free = client.get("/books", params={"available": True}).json()
    assert [b["title"] for b in free] == ["Война и мир"]


def test_patch_book_adjusts_available(filled):
    client, _, book, reader = filled
    client.post("/loans", json={"book_id": book["id"],
                                "reader_id": reader["id"]})
    changed = client.patch(f"/books/{book['id']}",
                           json={"copies_total": 5, "year": 1867}).json()
    assert (changed["copies_total"], changed["copies_available"],
            changed["year"]) == (5, 4, 1867)
    response = client.patch(f"/books/{book['id']}",
                            json={"copies_total": 0})
    assert response.status_code == 409


def test_delete_book(filled):
    client, author, book, reader = filled
    extra = client.post("/books", json={"title": "Черновик",
                                        "author_id": author["id"]}).json()
    assert client.delete(f"/books/{extra['id']}").status_code == 204
    assert client.get(f"/books/{extra['id']}").status_code == 404
    client.post("/loans", json={"book_id": book["id"],
                                "reader_id": reader["id"]})
    assert client.delete(f"/books/{book['id']}").status_code == 409


def test_reader_validation_and_uniqueness(client):
    bad = client.post("/readers", json={"name": "А", "email": "не-почта"})
    assert bad.status_code == 422
    good = {"name": "А", "email": "a@example.ru"}
    assert client.post("/readers", json=good).status_code == 201
    assert client.post("/readers", json=good).status_code == 409


def test_issue_and_return_in_transactions(filled):
    client, _, book, reader = filled
    request = {"book_id": book["id"], "reader_id": reader["id"]}
    first = client.post("/loans", json=request)
    assert first.status_code == 201
    assert first.json()["returned_at"] is None
    assert client.post("/loans", json=request).status_code == 201
    assert client.post("/loans", json=request).status_code == 409
    assert client.get(f"/books/{book['id']}").json()["copies_available"] == 0

    loan_id = first.json()["id"]
    returned = client.post(f"/loans/{loan_id}/return")
    assert returned.status_code == 200
    assert returned.json()["returned_at"] is not None
    assert client.post(f"/loans/{loan_id}/return").status_code == 409
    assert client.get(f"/books/{book['id']}").json()["copies_available"] == 1
    active = client.get("/loans", params={"active": True}).json()
    assert [loan["id"] for loan in active] == [2]


def test_failed_issue_changes_nothing(filled):
    client, _, book, _ = filled
    response = client.post("/loans", json={"book_id": book["id"],
                                           "reader_id": 999})
    assert response.status_code == 404
    assert client.get(f"/books/{book['id']}").json()["copies_available"] == 2
    assert client.get("/loans").json() == []


@pytest.mark.parametrize(
    "path", ["/books/99", "/loans/99/return"],
)
def test_not_found(client, path):
    method = client.post if path.endswith("return") else client.get
    assert method(path).status_code == 404


def test_validation_errors(filled):
    client, author, _, _ = filled
    for payload in ({"title": "", "author_id": author["id"]},
                    {"title": "X", "author_id": author["id"], "year": 99},
                    {"title": "X", "author_id": author["id"],
                     "copies_total": -1}):
        assert client.post("/books", json=payload).status_code == 422


def test_swagger(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/authors", "/books", "/books/{book_id}", "/readers", "/loans",
            "/loans/{loan_id}/return"} <= set(paths)
