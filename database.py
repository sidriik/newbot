"""
database.py - работа с каталогом книг в SQLite
"""

import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    """Контекстный менеджер для подключения к БД."""
    conn = sqlite3.connect('telegram_books.db', timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

class BookDatabase:
    """Управление каталогом книг в SQLite."""
    
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных."""
        try:
            with get_db_connection() as conn:
                # Таблица книг
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        genre TEXT,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Добавляем тестовые книги, если таблица пуста
                cursor = conn.execute('SELECT COUNT(*) as count FROM books')
                if cursor.fetchone()['count'] == 0:
                    self._add_sample_books(conn)
                
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def _add_sample_books(self, conn):
        """Добавляет тестовые книги."""
        sample_books = [
            ("Преступление и наказание", "Фёдор Достоевский", "Классика", 
             "Роман о студенте Раскольникове, совершившем убийство"),
            ("Мастер и Маргарита", "Михаил Булгаков", "Классика",
             "Мистический роман о визите дьявола в Москву"),
            ("1984", "Джордж Оруэлл", "Антиутопия",
             "Роман о тоталитарном обществе под постоянным наблюдением"),
            ("Гарри Поттер и философский камень", "Джоан Роулинг", "Фэнтези",
             "Первая книга о юном волшебнике Гарри Поттере"),
            ("Война и мир", "Лев Толстой", "Классика",
             "Эпопея о войне 1812 года и судьбах русских дворян"),
            ("Маленький принц", "Антуан де Сент-Экзюпери", "Сказка",
             "Философская сказка для взрослых"),
            ("Три товарища", "Эрих Мария Ремарк", "Роман",
             "История о дружбе и любви в послевоенной Германии"),
            ("Шерлок Холмс. Сборник", "Артур Конан Дойл", "Детектив",
             "Рассказы о знаменитом сыщике Шерлоке Холмсе"),
            ("Алхимик", "Пауло Коэльо", "Роман",
             "Притча о поиске своего предназначения"),
            ("Гордость и предубеждение", "Джейн Остин", "Роман",
             "История любви Элизабет Беннет и мистера Дарси"),
        ]
        
        for title, author, genre, description in sample_books:
            conn.execute('''
                INSERT INTO books (title, author, genre, description)
                VALUES (?, ?, ?, ?)
            ''', (title, author, genre, description))
    
    def search_books(self, query, limit=15):
        """Ищет книги по названию или автору."""
        try:
            search_term = f"%{query}%"
            with get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT id, title, author, genre, description
                    FROM books
                    WHERE title LIKE ? OR author LIKE ?
                    ORDER BY title
                    LIMIT ?
                ''', (search_term, search_term, limit))
                
                results = []
                for row in cursor:
                    results.append({
                        'id': row['id'],
                        'title': row['title'],
                        'author': row['author'],
                        'genre': row['genre'],
                        'description': row['description']
                    })
                return results
        except Exception as e:
            logger.error(f"Error searching books: {e}")
            return []
    
    def get_book(self, book_id):
        """Получает книгу по ID."""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT id, title, author, genre, description
                    FROM books WHERE id = ?
                ''', (book_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row['id'],
                        'title': row['title'],
                        'author': row['author'],
                        'genre': row['genre'],
                        'description': row['description']
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting book {book_id}: {e}")
            return None
    
    def get_all_books(self, limit=50):
        """Получает все книги."""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT id, title, author, genre
                    FROM books
                    ORDER BY title
                    LIMIT ?
                ''', (limit,))
                return [dict(row) for row in cursor]
        except Exception as e:
            logger.error(f"Error getting all books: {e}")
            return []
    
    def add_book(self, title, author, genre=None, description=None):
        """Добавляет новую книгу в каталог."""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO books (title, author, genre, description)
                    VALUES (?, ?, ?, ?)
                ''', (title, author, genre, description))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding book: {e}")
            return None

# Глобальный экземпляр базы данных
db = BookDatabase()
