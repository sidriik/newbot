import pytest
from unittest.mock import Mock
from new_bot import Book, UserBook, BookManager, UserManager

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


def test_get_all_genres1():
    db = Mock()
    db.get_all_genres.return_value = ["Фэнтези", "Детектив", "Классика"]
    m = BookManager(db)
    assert m.get_all_genres() == ["Фэнтези", "Детектив", "Классика"]


def test_get_all_genres2():
    db = Mock()
    db.get_all_genres.return_value = []
    m = BookManager(db)
    assert m.get_all_genres() == []


def test_get_book():
    db = Mock()
    db.get_book.return_value = {'title': 'Книга'}
    m = BookManager(db)
    assert m.get_book(1).title == 'Книга'


def test_search_books():
    db = Mock()
    db.search_books.return_value = [{'title': 'Книга 1'}, {'title': 'Книга 2'}]
    m = BookManager(db)
    assert len(m.search_books()) == 2


def test_rate_book1():
    db = Mock()
    db.rate_book.return_value = True
    m = UserManager(db)
    assert m.rate_book(1, 1, 5) == True


def test_rate_book2():
    db = Mock()
    m = UserManager(db)
    assert m.rate_book(1, 1, 0) == False


def test_count_user_books1():
    m = UserManager(None)
    m.get_user_books = lambda user_id: [Mock(), Mock(), Mock()]
    assert m.count_user_books(1) == 3


def test_count_user_books2():
    m = UserManager(None)
    m.get_user_books = lambda user_id: []
    assert m.count_user_books(1) == 0


def test_add_book():
    db = Mock()
    db.add_user_book.return_value = True
    m = UserManager(db)
    assert m.add_book(1, 1, "planned") == True


def test_update_status():
    db = Mock()
    db.update_book_status.return_value = True
    m = UserManager(db)
    assert m.update_book_status(1, 1, "reading", 10) == True
