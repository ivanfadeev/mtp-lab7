"""Проверка демонстрации из main.py."""

import pytest

import main


def test_demo(tmp_path, capsys):
    target = tmp_path / "books.csv"
    main.main(["--csv", str(target)])
    output = capsys.readouterr().out
    assert target.exists()
    assert "authors          строк: 5" in output
    assert "Поиск «ТОЛСТ»" in output
    assert "свободно было 3, стало 3" in output
    assert "книг в базе: 7" in output


def test_demo_on_file_database_twice(tmp_path, capsys):
    db = tmp_path / "library.db"
    for _ in range(2):
        main.main(["--db", str(db), "--csv", str(tmp_path / "b.csv")])
    assert "books            строк: 7" in capsys.readouterr().out


def test_version(capsys):
    with pytest.raises(SystemExit):
        main.main(["--version"])
    assert capsys.readouterr().out.strip() == "lab7 1.0.0"
