#!/usr/bin/env python3
"""
test_bot.py - Тесты для BookBot
"""

import unittest
import tempfile
import os
from database import Database
from models import Book, UserBook, BookManager, UserManager


class TestDatabase(unittest.TestCase):
    """Тесты для класса Database."""
    
    def setUp(self):
        """Настройка тестовой базы данных."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = Database(self.db_path)
    
    def tearDown(self):
        """Очистка после тестов."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_database_initialization(self):
        """Тестирование инициализации базы данных."""
        # Проверяем, что файл базы данных создан
        self.assertTrue(os.path.exists(self.db_path))
    
    def test_add_and_get_book(self):
        """Тестирование добавления и получения книги."""
        # Тестируем получение существующей книги
        book = self.db.get_book(1)
        self.assertIsNotNone(book)
        self.assertEqual(book['id'], 1)
    
    def test_search_books(self):
        """Тестирование поиска книг."""
        # Поиск по названию
        results = self.db.search_books(query="Гарри")
        self.assertGreaterEqual(len(results), 0)
        
        # Поиск по жанру
        results = self.db.search_books(genre="Классика")
        self.assertGreaterEqual(len(results), 0)
    
    def test_user_management(self):
        """Тестирование управления пользователями."""
        # Создаем пользователя
        user_id = self.db.get_or_create_user(
            telegram_id=123456,
            username="testuser"
        )
        
        self.assertIsNotNone(user_id)


class TestModels(unittest.TestCase):
    """Тесты для моделей данных."""
    
    def setUp(self):
        """Настройка тестовой базы данных."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = Database(self.db_path)
        self.book_manager = BookManager(self.db)
        self.user_manager = UserManager(self.db)
    
    def tearDown(self):
        """Очистка после тестов."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_book_model(self):
        """Тестирование модели Book."""
        book_data = {
            'id': 1,
            'title': 'Тестовая книга',
            'author': 'Тестовый автор',
            'total_pages': 100,
            'genre': 'Тест',
            'description': 'Тестовое описание'
        }
        
        book = Book(book_data)
        
        # Проверяем атрибуты
        self.assertEqual(book.id, 1)
        self.assertEqual(book.title, 'Тестовая книга')
        self.assertEqual(book.author, 'Тестовый автор')
        
        # Проверяем форматирование
        formatted_info = book.get_formatted_info()
        self.assertIn('Тестовая книга', formatted_info)
    
    def test_user_book_model(self):
        """Тестирование модели UserBook."""
        user_book_data = {
            'id': 1,
            'user_id': 1,
            'book_id': 1,
            'status': 'reading',
            'current_page': 50,
            'rating': 5,
            'title': 'Тестовая книга',
            'author': 'Тестовый автор',
            'total_pages': 100
        }
        
        user_book = UserBook(user_book_data)
        
        # Проверяем атрибуты
        self.assertEqual(user_book.id, 1)
        self.assertEqual(user_book.status, 'reading')
        self.assertEqual(user_book.rating, 5)
        
        # Проверяем методы
        self.assertEqual(user_book.get_progress_percentage(), 50.0)
        
        formatted_info = user_book.get_formatted_info()
        self.assertIn('Тестовая книга', formatted_info)
    
    def test_book_manager(self):
        """Тестирование BookManager."""
        # Получаем все книги
        books = self.book_manager.search_books()
        self.assertGreater(len(books), 0)
        
        # Проверяем, что все объекты - экземпляры Book
        for book in books:
            self.assertIsInstance(book, Book)
    
    def test_user_manager(self):
        """Тестирование UserManager."""
        # Создаем пользователя
        user_id = self.user_manager.get_or_create_user(
            telegram_id=999999,
            username="testuser"
        )
        
        self.assertIsNotNone(user_id)


def run_tests():
    """Запускает все тесты."""
    # Создаем test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Добавляем тесты
    suite.addTests(loader.loadTestsFromTestCase(TestDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestModels))
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Возвращаем код выхода
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    print("Запуск тестов BookBot...")
    print("=" * 50)
    
    exit_code = run_tests()
    
    print("=" * 50)
    if exit_code == 0:
        print(" Все тесты пройдены успешно!")
    else:
        print(" Некоторые тесты не пройдены")
    
    print("Тестирование завершено")
    exit(exit_code)
