# Лабораторная работа №7 — работа с базами данных

**Фадеев Иван Александрович, группа 221141, вариант 7, лабораторная №7**

Дисциплина: «Методы и технологии программирования» (часть 1).

## Задания варианта 7

| № | Сложность | Задание из общего списка | Где в коде |
|---|-----------|--------------------------|------------|
| 1 | средняя | 7. Создать несколько таблиц | `library/db.py` — `SCHEMA`, `create_schema` |
| 2 | средняя | 9. Экспорт данных в CSV | `library/export.py` — `export_query`, `export_books` |
| 3 | средняя | 3. Выбрать данные из таблицы | `library/data.py` — `books_with_authors`, `find_books` и др. |
| 4 | повышенная | 7. FastAPI + SQLAlchemy (REST) | `api/` — модели, схемы и маршруты |
| 5 | повышенная | 5. Транзакции | `library/db.py` — `transaction`, `library/loans.py`; `session.begin()` в `api/main.py` |

Предметная область — библиотека: авторы, книги с числом экземпляров,
читатели и выдачи книг. Задания средней сложности и транзакции
выполнены на встроенном модуле `sqlite3`, REST API — на FastAPI и
SQLAlchemy ORM поверх той же схемы базы.

## Темы из методички

| Тема | Как применена |
|------|---------------|
| `sqlite3` — встроенный модуль | `connect`, `execute`, `executemany`, `fetchone`/`fetchall`, `row_factory = sqlite3.Row` (столбцы по имени), своя SQL-функция через `create_function` |
| Создание БД и таблиц | четыре связанные таблицы с первичными и внешними ключами, `CHECK`, `UNIQUE`, `DEFAULT` и индексами |
| `INSERT` / `SELECT` / `UPDATE` | заполнение через `executemany`, выборки с `JOIN`, `LEFT JOIN`, `GROUP BY`, `WHERE`, `ORDER BY`; `UPDATE` остатков при выдаче и возврате |
| Параметры запросов | все значения передаются через `?`, поэтому ввод не может изменить SQL (тест `test_find_treats_input_as_data`) |
| SQLAlchemy ORM: модели, сессии | декларативные модели с `Mapped`/`mapped_column` и связями `relationship`, `sessionmaker`, сессия на запрос через зависимость FastAPI |

Адрес базы для API задаётся переменной окружения `DATABASE_URL`
(по умолчанию `sqlite:///library.db`).

## Схема базы

```
authors (id, name UNIQUE, country)
   │ 1
   │ N
books (id, title, author_id → authors.id, year CHECK 1400–2100,
       copies_total ≥ 0, copies_available от 0 до copies_total)
   │ 1
   │ N
loans (id, book_id → books.id, reader_id → readers.id,
       issued_at DEFAULT now, returned_at NULL — пока не вернули)
   │ N
   │ 1
readers (id, name, email UNIQUE)
```

Внешние ключи в SQLite по умолчанию не проверяются, поэтому при каждом
подключении выполняется `PRAGMA foreign_keys = ON` — и в модуле
`library`, и в движке SQLAlchemy.

## Структура проекта

```
main.py               демонстрация работы через sqlite3 (--db, --csv, --version)
library/db.py         подключение, схема, список таблиц, transaction()
library/data.py       демонстрационные данные и выборки
library/export.py     экспорт результата запроса в CSV
library/loans.py      выдача и возврат книг, пакетная вставка — в транзакциях
api/database.py       движок SQLAlchemy, базовый класс моделей
api/models.py         ORM-модели Author, Book, Reader, Loan
api/schemas.py        схемы Pydantic для запросов и ответов
api/main.py           FastAPI: маршруты /authors, /books, /readers, /loans
tests/                тесты pytest
```

## Запуск

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python main.py                     # демонстрация на базе в памяти
python main.py --db library.db     # то же на файле (создаётся и заполняется один раз)
uvicorn api.main:create_app --factory --reload   # REST API, Swagger на /docs
```

API создаётся фабрикой `create_app`, поэтому импорт модуля не создаёт
файл базы. Если сначала выполнить `python main.py --db library.db`, API
будет работать с уже заполненной базой.

## Отчёт о выполнении

### Задание 7 (средней сложности): несколько таблиц

`create_schema` создаёт таблицы `authors`, `books`, `readers`, `loans`
и индексы по внешним ключам одной транзакцией. Ограничения схемы
проверяет сама база: книга не может ссылаться на несуществующего
автора, свободных экземпляров не может быть больше общего числа или
меньше нуля, почта читателя уникальна. Повторный вызов безопасен
(`IF NOT EXISTS`).

```console
== Таблицы базы ==
  authors          строк: 5
  books            строк: 7
  loans            строк: 0
  readers          строк: 3
```

### Задание 3 (средней сложности): выбрать данные из таблицы

`library/data.py` содержит выборки разной сложности: каталог с
авторами (`JOIN`), поиск по названию и автору, число книг у каждого
автора (`LEFT JOIN` + `GROUP BY`, чтобы авторы без книг тоже попали в
отчёт) и невозвращённые книги (`JOIN` трёх таблиц). Встроенные `LOWER`
и `LIKE` в SQLite меняют регистр только у латиницы, поэтому для
поиска зарегистрирована функция `casefold()` на Python — поиск «ТОЛСТ»
находит «Лев Толстой».

```console
== Каталог (JOIN books + authors) ==
  6. 1984 — Джордж Оруэлл, 1949 (2 из 2)
  1. Война и мир — Лев Толстой, 1869 (3 из 3)
  2. Анна Каренина — Лев Толстой, 1878 (2 из 2)
  5. Мастер и Маргарита — Михаил Булгаков, 1967 (2 из 2)
  7. 451 градус по Фаренгейту — Рэй Брэдбери, 1953 (1 из 1)
  3. Преступление и наказание — Фёдор Достоевский, 1866 (4 из 4)
  4. Идиот — Фёдор Достоевский, 1869 (1 из 1)

== Поиск «ТОЛСТ» (без учёта регистра) ==
  Анна Каренина — Лев Толстой
  Война и мир — Лев Толстой

== Книг у автора (GROUP BY) ==
  Лев Толстой          книг: 2, экземпляров: 5
  Фёдор Достоевский    книг: 2, экземпляров: 5
  Джордж Оруэлл        книг: 1, экземпляров: 2
  Михаил Булгаков      книг: 1, экземпляров: 2
  Рэй Брэдбери         книг: 1, экземпляров: 1
```

### Задание 5 (повышенной сложности): транзакции

Соединение открывается в режиме автофиксации, а связанные изменения
объединяются контекстным менеджером `transaction()`: `BEGIN IMMEDIATE`
в начале, `COMMIT` при успехе и `ROLLBACK` при любом исключении.

- `issue_book` уменьшает число свободных экземпляров и добавляет
  запись о выдаче. Если вставка не удалась (нет такого читателя —
  сработал внешний ключ), откатывается и уменьшение остатка.
- `return_book` отмечает возврат и возвращает экземпляр.
- `add_books` добавляет партию книг целиком или не добавляет ничего.

В REST API те же операции выполняются внутри `session.begin()`
SQLAlchemy.

```console
== Транзакции ==
выдача №1: книга 7 → читатель 1, свободно: 0
повторная выдача книги 7 → откат: книга 7 недоступна, свободно: 0
выдача несуществующему читателю → откат (FOREIGN KEY constraint failed), свободно было 3, стало 3
партия из 2 книг с ошибкой во второй → откат (CHECK constraint failed: copies_total >= 0), книг в базе: 7
невозвращённые книги:
  выдача №1: Иван Петров — 451 градус по Фаренгейту
книга 7 возвращена, свободно: 1
```

### Задание 9 (средней сложности): экспорт данных в CSV

`export_query` записывает результат любого запроса в CSV модулем `csv`:
заголовок берётся из `cursor.description` (он есть даже у пустого
результата), значения с запятыми, кавычками и переводами строк
экранируются. Файл сохраняется в UTF-8 с BOM — так Excel сразу
показывает кириллицу. Разделитель настраивается (например, `;` для
русской версии Excel).

```console
== Экспорт в CSV ==
записано строк: 7, файл export/books.csv
$ head -5 export/books.csv
id,название,автор,год,в_наличии,всего
1,Война и мир,Лев Толстой,1869,3,3
2,Анна Каренина,Лев Толстой,1878,2,2
3,Преступление и наказание,Фёдор Достоевский,1866,4,4
4,Идиот,Фёдор Достоевский,1869,1,1
```

### Задание 7 (повышенной сложности): FastAPI + SQLAlchemy (REST)

ORM-модели описывают те же таблицы, что и `library/db.py`: тест
`test_orm_compat.py` создаёт базу модулем `sqlite3`, а затем читает её
через SQLAlchemy, включая связи `book.author` и `loan.reader`.

| Метод и адрес | Что делает |
|---------------|------------|
| `GET /authors`, `POST /authors` | список и добавление авторов (409 при повторе имени) |
| `GET /books?q=&available=` | книги с авторами, поиск и фильтр «в наличии» |
| `POST /books` | добавить книгу (404, если нет автора) |
| `GET /books/{id}` | одна книга |
| `PATCH /books/{id}` | изменить книгу; при смене числа экземпляров остаток пересчитывается |
| `DELETE /books/{id}` | удалить книгу без истории выдач (иначе 409) |
| `GET /readers`, `POST /readers` | читатели (409 при повторе почты) |
| `GET /loans?active=` | выдачи, можно только невозвращённые |
| `POST /loans` | выдать книгу (транзакция; 409, если экземпляров нет) |
| `POST /loans/{id}/return` | вернуть книгу (транзакция; 409 при повторе) |

Сеанс с API на базе, заполненной `python main.py --db library.db`:

```console
$ curl -s 'http://127.0.0.1:5078/books?q=фаренгейт'
[
  {
    "id": 7,
    "title": "451 градус по Фаренгейту",
    "year": 1953,
    "copies_total": 1,
    "copies_available": 1,
    "author": {
      "id": 5,
      "name": "Рэй Брэдбери",
      "country": "США"
    }
  }
]

$ curl -s -X POST http://127.0.0.1:5078/readers -H 'Content-Type: application/json' -d '{"name": "Ольга Ким", "email": "kim@example.ru"}'
HTTP 201: {"id": 4, "name": "Ольга Ким", "email": "kim@example.ru"}

$ curl -s -X POST http://127.0.0.1:5078/loans -H 'Content-Type: application/json' -d '{"book_id": 7, "reader_id": 4}'   # единственный экземпляр
HTTP 201: {"id": 2, "book_id": 7, "reader_id": 4, "issued_at": "2026-10-11T09:56:40", "returned_at": null}
$ curl -s -X POST http://127.0.0.1:5078/loans -H 'Content-Type: application/json' -d '{"book_id": 7, "reader_id": 1}'   # экземпляров больше нет
HTTP 409: {"detail": "свободных экземпляров нет"}
$ curl -s -X POST http://127.0.0.1:5078/loans -H 'Content-Type: application/json' -d '{"book_id": 1, "reader_id": 999}'  # нет читателя — остаток не меняется
HTTP 404: {"detail": "читатель не найден"}
$ curl -s http://127.0.0.1:5078/books/1   # остаток книги 1 не изменился
copies_available: 3

$ curl -s -X POST http://127.0.0.1:5078/loans/2/return
HTTP 200: {"id": 2, "book_id": 7, "reader_id": 4, "issued_at": "2026-10-11T09:56:40", "returned_at": "2026-10-11T09:56:40"}
$ curl -s -X POST http://127.0.0.1:5078/loans/2/return   # повторный возврат
HTTP 409: {"detail": "книга уже возвращена"}
$ curl -s -X PATCH http://127.0.0.1:5078/books/7 -H 'Content-Type: application/json' -d '{"copies_total": 3}'
{'id': 7, 'title': '451 градус по Фаренгейту', 'copies_total': 3, 'copies_available': 3}
```

## Тесты

Тесты используют базы в памяти: модуль `sqlite3` — `:memory:`, API —
отдельный движок SQLAlchemy со `StaticPool` на каждый тест.

```console
$ pip install -r requirements-dev.txt
$ python -m pytest -q
...............................................                          [100%]
47 passed in 0.18s
```

| Файл | Тестов |
|------|--------|
| `test_api.py` | 13 |
| `test_export.py` | 5 |
| `test_main.py` | 3 |
| `test_orm_compat.py` | 1 |
| `test_queries.py` | 7 |
| `test_schema.py` | 10 |
| `test_transactions.py` | 8 |

```console
$ python main.py --version
lab7 1.0.0
```
