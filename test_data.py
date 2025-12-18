import unittest
import os
import sqlite3
from database import Database


class TestDatabaseSimple(unittest.TestCase):
    
    def setUp(self):
        self.test_db_path = "test_books.db"
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = Database(db_path=self.test_db_path)
    
    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    def test_01_database_initialization(self):
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        self.assertIn('books', tables)
        self.assertIn('users', tables)
        self.assertIn('user_books', tables)
        cursor.execute("SELECT COUNT(*) FROM books")
        count = cursor.fetchone()[0]
        self.assertGreater(count, 0, "Тестовые книги должны быть добавлены")
        
        conn.close()
    
    def test_02_user_creation_and_retrieval(self):
        user_id = self.db.get_or_create_user(
            telegram_id=12345,
            username="testuser"
        )
        
        self.assertIsInstance(user_id, int)
        self.assertGreater(user_id, 0)
        same_user_id = self.db.get_or_create_user(telegram_id=12345)
        self.assertEqual(user_id, same_user_id)
        another_user_id = self.db.get_or_create_user(telegram_id=67890)
        self.assertNotEqual(user_id, another_user_id)
    
    def test_03_book_addition_and_duplicate_check(self):
        success, book_id, message = self.db.add_book_to_catalog_simple(
            title="Тестовая книга",
            author="Тестовый автор",
            pages=100,
            genre="Тест"
        )
        
        self.assertTrue(success)
        self.assertIsInstance(book_id, int)
        self.assertIn("добавлена", message.lower())
        success2, book_id2, message2 = self.db.add_book_to_catalog_simple(
            title="Тестовая книга",
            author="Тестовый автор",
            pages=200,
            genre="Другой жанр"
        )
        
        self.assertFalse(success2)
        self.assertEqual(book_id, book_id2)
        self.assertIn("уже есть", message2.lower())
    
    def test_04_user_book_operations(self):
        user_id = self.db.get_or_create_user(telegram_id=11111)
        success, book_id, _ = self.db.add_book_to_catalog_simple(
            title="Книга пользователя",
            author="Автор",
            pages=150,
            genre="Жанр"
        )

        added = self.db.add_user_book(user_id, book_id, "planned")
        self.assertTrue(added)
        user_books = self.db.get_user_books(user_id)
        self.assertEqual(len(user_books), 1)
        added_again = self.db.add_user_book(user_id, book_id)
        self.assertFalse(added_again)
        updated = self.db.update_book_status(user_id, book_id, "reading", 50)
        self.assertTrue(updated)
        removed = self.db.remove_user_book(user_id, book_id)
        self.assertTrue(removed)
        user_books = self.db.get_user_books(user_id)
        self.assertEqual(len(user_books), 0)
    
    def test_05_book_rating_and_validation(self):
        user_id = self.db.get_or_create_user(telegram_id=22222)
        success, book_id, _ = self.db.add_book_to_catalog_simple(
            title="Оцениваемая книга",
            author="Автор",
            pages=100,
            genre="Жанр"
        )
        
        self.db.add_user_book(user_id, book_id)
        rated = self.db.rate_book(user_id, book_id, 5)
        self.assertTrue(rated)
        rated_low = self.db.rate_book(user_id, book_id, 0)
        self.assertFalse(rated_low)
        rated_high = self.db.rate_book(user_id, book_id, 6)
        self.assertFalse(rated_high)
        rated_change = self.db.rate_book(user_id, book_id, 3)
        self.assertTrue(rated_change)


if __name__ == '__main__':
    unittest.main()
