import pytest
from models import Book, UserBook, BookManager, UserManager
def test_book_simple():
    """Simple test for Book class"""
    book_data = {
        'id': 1,
        'title': 'Harry Potter',
        'author': 'J.K. Rowling'
    }
    
    book = Book(book_data)
    
    assert book.id == 1
    assert book.title == 'Harry Potter'
    assert book.author == 'J.K. Rowling'
    assert book.get_short() == 'Harry Potter'

def test_book_get_info():
    """Test book info method"""
    book_data = {
        'id': 2,
        'title': 'War and Peace',
        'author': 'Leo Tolstoy',
        'genre': 'Classic',
        'total_pages': 1000,
        'description': 'A Russian novel'
    }
    
    book = Book(book_data)
    info = book.get_info()
    
    assert '📖 War and Peace' in info
    assert '👤 Автор: Leo Tolstoy' in info 
    assert '📂 Жанр: Classic' in info
    assert '📄 Страниц: 1000' in info

def test_userbook_progress():
    """Test UserBook progress calculation"""
    data = {
        'id': 1,
        'current_page': 50,
        'total_pages': 200,
        'status': 'reading'
    }
    
    user_book = UserBook(data)
    
    assert user_book.get_progress() == 25.0

def test_bookmanager():
    class MockDB:
        def get_book(self, book_id):
            return {'id': book_id, 'title': f'Book {book_id}', 'author': 'Author'}
        
        def search_books(self, query="", genre="", limit=10):
            return [{'id': 1, 'title': 'Found Book', 'author': 'Author'}]
        
        def get_top_books(self, criteria="rating", genre="", author="", limit=5):
            return [{'id': 1, 'title': 'Top Book', 'author': 'Popular Author'}]
        
        def get_all_genres(self):
            return ['Fantasy', 'Classic', 'Detective']

    db = MockDB()
    manager = BookManager(db)
    book = manager.get_book(1)
    assert book.title == 'Book 1'
    results = manager.search_books("search")
    assert len(results) == 1
    assert results[0].title == 'Found Book'
    genres = manager.get_all_genres()
    assert len(genres) == 3
    assert 'Fantasy' in genres

def test_book_not_found():
    """Negative test: book not found"""
    class MockDB:
        def get_book(self, book_id):
            return None  
    
    db = MockDB()
    manager = BookManager(db)
    book = manager.get_book(999)
    assert book is None

def test_invalid_book_data():
    book = Book({})
    assert book.title == 'Без названия'
    assert book.author == 'Неизвестный автор'
    assert book.genre == 'Не указан'
    assert book.total_pages == 0

def test_usermanager():
    class MockDB:
        def get_or_create_user(self, telegram_id, username="", first_name="", last_name=""):
            return 123
    
    db = MockDB()
    manager = UserManager(db)
    user_id = manager.get_or_create_user(telegram_id=55555, username="test_user")
    assert user_id == 123

def test_userbook_zero_pages():
    data = {
        'id': 1,
        'current_page': 10,
        'total_pages': 0 
    }
    
    user_book = UserBook(data)
    progress = user_book.get_progress()
    assert progress == 0

def test_bookmanager_empty_search():
    class MockDB:
        def search_books(self, query="", genre="", limit=10):
            return [] 
    
    db = MockDB()
    manager = BookManager(db)
    results = manager.search_books("nonexistentquery")
    assert results == []
    assert len(results) == 0
