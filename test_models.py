import pytest
from unittest.mock import Mock
from models import Book, UserBook, BookManager, UserManager

def test_book1():
    b = Book({'title': 'Гарри Поттер', 'author': 'Роулинг', 'genre': 'Фэнтези'})
    assert b.title == 'Гарри Поттер'
    assert b.author == 'Роулинг'
    assert b.genre == 'Фэнтези'


def test_book2():
    b = Book({})
    assert b.title == 'Без названия'
    assert b.author == 'Неизвестный автор'
    assert b.genre == 'Не указан'


def test_progress1():
    ub = UserBook({'current_page': 50, 'total_pages': 100})
    assert ub.get_progress() == 50.0


def test_progress2():
    ub = UserBook({'current_page': 10, 'total_pages': 0})
    assert ub.get_progress() == 0.0


def test_is_completed1():
    ub = UserBook({'status': 'completed'})
    assert ub.is_completed() == True


def test_is_completed2():
    ub = UserBook({'status': 'reading'})
    assert ub.is_completed() == False


def test_get_all_genre1():
    db = Mock()
    db.get_all_genres.return_value = ["Фэнтези", "Детектив", "Классика"]
    m = BookManager(db)
    assert m.get_all_genre() == ["Фэнтези", "Детектив", "Классика"]


def test_get_all_genre2():
    db = Mock()
    db.get_all_genres.return_value = []
    m = BookManager(db)
    assert m.get_all_genre() == []



def test_rate_books1():
    db = Mock()
    db.rate_book.return_value = True
    m = UserManager(db)
    assert m.rate_books(1, 1, 5) == True


def test_rate_books2():
    db = Mock()
    m = UserManager(db)
    assert m.rate_books(1, 1, 0) == False


def test_update_status1():
    db = Mock()
    db.update_book_status.return_value = True
    m = UserManager(db)
    assert m.update_books_status(1, 1, "reading", 10) == True


def test_update_status2():
    db = Mock()
    m = UserManager(db)
    result = m.update_books_status(1, 1, "invalid_status", 10)
    assert result == False
