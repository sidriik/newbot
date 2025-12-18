#!/usr/bin/env python3
"""
Тесты для модуля models.py
"""

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


def test_book_get_short():
    # Длинное название
    b = Book({'title': 'Очень длинное название книги которое не помещается'})
    short = b.get_short()
    assert '...' in short
    assert len(short) <= 18  # 15 + "..."

    # Короткое название
    b = Book({'title': 'Книга'})
    assert b.get_short() == 'Книга'


def test_book_get_info():
    b = Book({
        'title': 'Гарри Поттер',
        'author': 'Дж.К. Роулинг',
        'total_pages': 400,
        'genre': 'Фэнтези',
        'description': 'О волшебнике'
    })
    info = b.get_info()
    assert 'Гарри Поттер' in info
    assert 'Дж.К. Роулинг' in info
    assert '400' in info
    assert 'Фэнтези' in info
    assert 'О волшебнике' in info


def test_progress1():
    ub = UserBook({'current_page': 50, 'total_pages': 100})
    assert ub.get_progress() == 50.0


def test_progress2():
    ub = UserBook({'current_page': 10, 'total_pages': 0})
    assert ub.get_progress() == 0.0


def test_progress3():
    # Прогресс 100% при current_page >= total_pages
    ub = UserBook({'current_page': 100, 'total_pages': 100})
    assert ub.get_progress() == 100.0
    
    ub = UserBook({'current_page': 150, 'total_pages': 100})
    assert ub.get_progress() == 100.0


def test_is_completed1():
    ub = UserBook({'status': 'completed'})
    assert ub.is_completed() == True


def test_is_completed2():
    ub = UserBook({'status': 'reading'})
    assert ub.is_completed() == False


def test_is_completed3():
    ub = UserBook({'status': 'planned'})
    assert ub.is_completed() == False
    
    ub = UserBook({'status': 'dropped'})
    assert ub.is_completed() == False


def test_user_book_get_info():
    ub = UserBook({
        'title': 'Гарри Поттер',
        'author': 'Дж.К. Роулинг',
        'status': 'reading',
        'current_page': 150,
        'total_pages': 400,
        'rating': 5
    })
    info = ub.get_info()
    assert 'Гарри Поттер' in info
    assert 'Дж.К. Роулинг' in info
    assert '150/400' in info
    assert '⭐' in info


def test_user_book_get_info_no_rating():
    ub = UserBook({
        'title': 'Гарри Поттер',
        'author': 'Дж.К. Роулинг',
        'status': 'planned'
    })
    info = ub.get_info()
    assert 'Гарри Поттер' in info
    assert '⭐' not in info  # Не должно быть звезд, если нет оценки


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
    db.get_book.return_value = {'title': 'Книга', 'author': 'Автор'}
    m = BookManager(db)
    book = m.get_book(1)
    assert book.title == 'Книга'
    assert book.author == 'Автор'


def test_get_book_not_found():
    db = Mock()
    db.get_book.return_value = None
    m = BookManager(db)
    assert m.get_book(999) is None


def test_search_books():
    db = Mock()
    db.search_books.return_value = [{'title': 'Книга 1'}, {'title': 'Книга 2'}]
    m = BookManager(db)
    books = m.search_books()
    assert len(books) == 2
    assert books[0].title == 'Книга 1'
    assert books[1].title == 'Книга 2'


def test_search_books_empty():
    db = Mock()
    db.search_books.return_value = []
    m = BookManager(db)
    books = m.search_books()
    assert len(books) == 0


def test_get_top_books():
    db = Mock()
    db.get_top_books.return_value = [
        {'title': 'Лучшая книга', 'author': 'Лучший автор'},
        {'title': 'Вторая книга', 'author': 'Второй автор'}
    ]
    m = BookManager(db)
    books = m.get_top_books()
    assert len(books) == 2
    assert books[0].title == 'Лучшая книга'


def test_rate_book1():
    db = Mock()
    db.rate_book.return_value = True
    m = UserManager(db)
    assert m.rate_book(1, 1, 5) == True


def test_rate_book2():
    db = Mock()
    m = UserManager(db)
    # Некорректная оценка (слишком маленькая)
    assert m.rate_book(1, 1, 0) == False
    # Некорректная оценка (слишком большая)
    assert m.rate_book(1, 1, 6) == False


def test_rate_book3():
    db = Mock()
    db.rate_book.return_value = False  # Например, если книга не найдена
    m = UserManager(db)
    assert m.rate_book(1, 999, 5) == False


def test_count_user_books1():
    m = UserManager(None)
    # Мокаем метод get_user_books
    m.get_user_books = lambda user_id: [
        Mock(title='Книга 1'),
        Mock(title='Книга 2'),
        Mock(title='Книга 3')
    ]
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


def test_add_book_already_exists():
    db = Mock()
    db.add_user_book.return_value = False  # Книга уже существует
    m = UserManager(db)
    assert m.add_book(1, 1, "planned") == False


def test_update_status():
    db = Mock()
    db.update_book_status.return_value = True
    m = UserManager(db)
    assert m.update_book_status(1, 1, "reading", 10) == True


def test_update_status_invalid():
    db = Mock()
    m = UserManager(db)
    # Некорректный статус
    assert m.update_book_status(1, 1, "wrong_status") == False
    # Отрицательная страница
    assert m.update_book_status(1, 1, "reading", -1) == False


def test_get_or_create_user():
    db = Mock()
    db.get_or_create_user.return_value = 123
    m = UserManager(db)
    user_id = m.get_or_create_user(telegram_id=456, username="test")
    assert user_id == 123


def test_remove_book():
    db = Mock()
    db.remove_user_book.return_value = True
    m = UserManager(db)
    assert m.remove_book(1, 1) == True


def test_remove_book_not_found():
    db = Mock()
    db.remove_user_book.return_value = False
    m = UserManager(db)
    assert m.remove_book(1, 999) == False


def test_get_user_books():
    db = Mock()
    db.get_user_books.return_value = [
        {'title': 'Книга 1', 'status': 'reading'},
        {'title': 'Книга 2', 'status': 'completed'}
    ]
    m = UserManager(db)
    books = m.get_user_books(1)
    assert len(books) == 2
    assert books[0].title == 'Книга 1'
    assert books[1].status == 'completed'


def test_get_completed_books():
    m = UserManager(None)
    # Мокаем get_user_books для возврата списка с разными статусами
    m.get_user_books = lambda user_id: [
        UserBook({'title': 'Книга 1', 'status': 'completed'}),
        UserBook({'title': 'Книга 2', 'status': 'reading'}),
        UserBook({'title': 'Книга 3', 'status': 'completed'}),
        UserBook({'title': 'Книга 4', 'status': 'planned'})
    ]
    completed = m.get_completed_books(1)
    assert len(completed) == 2
    assert all(book.is_completed() for book in completed)
    assert completed[0].title == 'Книга 1'
    assert completed[1].title == 'Книга 3'


def test_get_stats():
    db = Mock()
    db.get_user_stats.return_value = {
        'total': 5,
        'reading': 2,
        'completed': 3,
        'avg_rating': 4.5
    }
    m = UserManager(db)
    stats = m.get_stats(1)
    assert stats['total'] == 5
    assert stats['reading'] == 2
    assert stats['completed'] == 3
    assert stats['avg_rating'] == 4.5


def test_has_book_true():
    m = UserManager(None)
    m.get_book_info = lambda user_id, book_id: Mock()  # Возвращаем не None
    assert m.has_book(1, 1) == True


def test_has_book_false():
    m = UserManager(None)
    m.get_book_info = lambda user_id, book_id: None  # Возвращаем None
    assert m.has_book(1, 1) == False


def test_update_progress():
    m = UserManager(None)
    # Мокаем get_book_info и update_book_status
    mock_book = Mock(total_pages=100)
    m.get_book_info = lambda user_id, book_id: mock_book
    m.update_book_status = lambda user_id, book_id, status, page: True
    
    # Обновление прогресса
    assert m.update_progress(1, 1, 50) == True


def test_update_progress_complete():
    m = UserManager(None)
    mock_book = Mock(total_pages=100)
    m.get_book_info = lambda user_id, book_id: mock_book
    
    # Сохраняем вызовы update_book_status
    calls = []
    def mock_update(user_id, book_id, status, page):
        calls.append((status, page))
        return True
    m.update_book_status = mock_update
    
    # Обновляем до конца книги
    result = m.update_progress(1, 1, 100)
    assert result == True
    assert len(calls) == 1
    assert calls[0][0] == 'completed'
    assert calls[0][1] == 100


def test_update_progress_invalid():
    m = UserManager(None)
    # Отрицательная страница
    with pytest.raises(ValueError):
        m.update_progress(1, 1, -1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]), 10) == True
