#!/usr/bin/env python3
"""
database.py - База данных для BookBot
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Исключение для ошибок базы данных."""
    pass


class Database:
    """Класс для работы с базой данных SQLite."""
    
    def __init__(self, db_path: str = "books.db"):
        """Инициализация базы данных."""
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self):
        """Создает соединение с базой данных."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Инициализирует таблицы в базе данных."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Таблица книг
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        total_pages INTEGER DEFAULT 0,
                        genre TEXT,
                        description TEXT,
                        added_count INTEGER DEFAULT 0,
                        current_readers INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица книг пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        book_id INTEGER NOT NULL,
                        status TEXT DEFAULT 'planned',
                        current_page INTEGER DEFAULT 0,
                        rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, book_id)
                    )
                ''')
                
                # Проверяем, есть ли книги
                cursor.execute("SELECT COUNT(*) FROM books")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    self._add_sample_books(cursor)
                    logger.info("Добавлены тестовые книги")
                
                conn.commit()
                logger.info(f"База данных инициализирована. Книг: {count}")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise DatabaseError(f"Ошибка инициализации БД: {e}")
    
    def _add_sample_books(self, cursor):
        """Добавляет тестовые книги."""
        sample_books = [
            ("Мастер и Маргарита", "Михаил Булгаков", 480, "Классика", "Философский роман о добре и зле"),
            ("Преступление и наказание", "Федор Достоевский", 671, "Классика", "Роман о преступлении и его последствиях"),
            ("1984", "Джордж Оруэлл", 328, "Антиутопия", "Роман о тоталитарном обществе"),
            ("Гарри Поттер и философский камень", "Джоан Роулинг", 320, "Фэнтези", "Первая книга о юном волшебнике"),
            ("Маленький принц", "Антуан де Сент-Экзюпери", 96, "Философская сказка", "Сказка-притча о дружбе"),
            ("Война и мир", "Лев Толстой", 1225, "Классика", "Эпопея о русском обществе"),
            ("Три товарища", "Эрих Мария Ремарк", 480, "Роман", "Роман о дружбе и любви"),
            ("Алхимик", "Пауло Коэльо", 208, "Роман", "Притча о поиске предназначения"),
            ("Шерлок Холмс", "Артур Конан Дойл", 307, "Детектив", "Рассказы о знаменитом сыщике"),
            ("Гордость и предубеждение", "Джейн Остин", 432, "Роман", "Классика английской литературы"),
            ("Метро 2033", "Дмитрий Глуховский", 384, "Постапокалипсис", "Роман о жизни в метро после войны"),
            ("Код да Винчи", "Дэн Браун", 489, "Детектив", "Детектив с историческими загадками"),
            ("451° по Фаренгейту", "Рэй Брэдбери", 256, "Антиутопия", "Роман о мире, где книги запрещены"),
            ("Убить пересмешника", "Харпер Ли", 376, "Роман", "Роман о расовых предрассудках"),
            ("Портрет Дориана Грея", "Оскар Уайльд", 254, "Классика", "Философский роман о красоте"),
        ]
        
        cursor.executemany('''
            INSERT INTO books (title, author, total_pages, genre, description)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_books)
    
    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Получает книгу по ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка получения книги {book_id}: {e}")
            return None
    
    def search_books(self, query: str = "", genre: str = "", limit: int = 10) -> List[Dict[str, Any]]:
        """Ищет книги."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                sql = "SELECT * FROM books WHERE 1=1"
                params = []
                
                if query:
                    sql += " AND (title LIKE ? OR author LIKE ?)"
                    search_term = f"%{query}%"
                    params.extend([search_term, search_term])
                
                if genre:
                    sql += " AND genre = ?"
                    params.append(genre)
                
                sql += " ORDER BY title LIMIT ?"
                params.append(limit)
                
                cursor.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Ошибка поиска книг: {e}")
            return []
    
    def get_book_statistics(self, book_id: int) -> Dict[str, Any]:
        """Получает статистику по книге."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COUNT(ub.id) as total_added,
                        COUNT(CASE WHEN ub.status = 'reading' THEN 1 END) as currently_reading,
                        AVG(ub.rating) as avg_rating,
                        COUNT(ub.rating) as rating_count
                    FROM books b
                    LEFT JOIN user_books ub ON b.id = ub.book_id
                    WHERE b.id = ?
                    GROUP BY b.id
                ''', (book_id,))
                
                result = cursor.fetchone()
                if result:
                    avg_rating = result['avg_rating'] or 0
                    return {
                        'total_added': result['total_added'] or 0,
                        'currently_reading': result['currently_reading'] or 0,
                        'avg_rating': round(float(avg_rating), 2),
                        'rating_count': result['rating_count'] or 0
                    }
                return {'total_added': 0, 'currently_reading': 0, 'avg_rating': 0, 'rating_count': 0}
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {'total_added': 0, 'currently_reading': 0, 'avg_rating': 0, 'rating_count': 0}
    
    def get_top_books(self, criteria: str = "rating", genre: str = "", 
                     author: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        """Получает топ книг."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if criteria == 'rating':
                    sql = '''
                        SELECT b.*, 
                               COALESCE(AVG(ub.rating), 0) as calculated_rating,
                               COUNT(ub.id) as total_added
                        FROM books b
                        LEFT JOIN user_books ub ON b.id = ub.book_id
                        WHERE 1=1
                    '''
                else:  # popularity
                    sql = '''
                        SELECT b.*, 
                               COUNT(ub.id) as total_added,
                               COUNT(CASE WHEN ub.status = 'reading' THEN 1 END) as currently_reading
                        FROM books b
                        LEFT JOIN user_books ub ON b.id = ub.book_id
                        WHERE 1=1
                    '''
                
                params = []
                
                if genre:
                    sql += " AND b.genre = ?"
                    params.append(genre)
                
                if author:
                    sql += " AND b.author LIKE ?"
                    params.append(f"%{author}%")
                
                if criteria == 'rating':
                    sql += '''
                        GROUP BY b.id
                        ORDER BY calculated_rating DESC, total_added DESC
                    '''
                else:
                    sql += '''
                        GROUP BY b.id
                        ORDER BY total_added DESC, currently_reading DESC
                    '''
                
                sql += " LIMIT ?"
                params.append(limit)
                
                cursor.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Ошибка получения топ книг: {e}")
            return []
    
    def get_or_create_user(self, telegram_id: int, username: str = "", 
                          first_name: str = "", last_name: str = "") -> int:
        """Получает или создает пользователя."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT id FROM users WHERE telegram_id = ?",
                    (telegram_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return result['id']
                
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, username, first_name, last_name))
                
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Ошибка создания пользователя: {e}")
            # Возвращаем фиктивный ID для продолжения работы
            return telegram_id
    
    def add_user_book(self, user_id: int, book_id: int, status: str = "planned") -> bool:
        """Добавляет книгу пользователю."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли уже книга
                cursor.execute(
                    "SELECT id FROM user_books WHERE user_id = ? AND book_id = ?",
                    (user_id, book_id)
                )
                
                if cursor.fetchone():
                    return False
                
                # Добавляем книгу
                cursor.execute('''
                    INSERT INTO user_books (user_id, book_id, status)
                    VALUES (?, ?, ?)
                ''', (user_id, book_id, status))
                
                # Обновляем статистику
                cursor.execute('''
                    UPDATE books 
                    SET added_count = added_count + 1,
                        current_readers = current_readers + ?
                    WHERE id = ?
                ''', (1 if status == 'reading' else 0, book_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка добавления книги: {e}")
            return False
    
    def remove_user_book(self, user_id: int, book_id: int) -> bool:
        """Удаляет книгу у пользователя."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT status FROM user_books WHERE user_id = ? AND book_id = ?",
                    (user_id, book_id)
                )
                
                result = cursor.fetchone()
                if not result:
                    return False
                
                status = result['status']
                
                cursor.execute(
                    "DELETE FROM user_books WHERE user_id = ? AND book_id = ?",
                    (user_id, book_id)
                )
                
                # Обновляем статистику
                cursor.execute('''
                    UPDATE books 
                    SET added_count = added_count - 1,
                        current_readers = current_readers - ?
                    WHERE id = ?
                ''', (1 if status == 'reading' else 0, book_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка удаления книги: {e}")
            return False
    
    def update_book_status(self, user_id: int, book_id: int, 
                          status: str, current_page: int = 0) -> bool:
        """Обновляет статус книги."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем старый статус
                cursor.execute(
                    "SELECT status FROM user_books WHERE user_id = ? AND book_id = ?",
                    (user_id, book_id)
                )
                
                result = cursor.fetchone()
                if not result:
                    return False
                
                old_status = result['status']
                
                # Обновляем статус
                cursor.execute('''
                    UPDATE user_books 
                    SET status = ?, current_page = ?
                    WHERE user_id = ? AND book_id = ?
                ''', (status, current_page, user_id, book_id))
                
                # Обновляем статистику
                if old_status != status:
                    if old_status == 'reading':
                        cursor.execute(
                            "UPDATE books SET current_readers = current_readers - 1 WHERE id = ?",
                            (book_id,)
                        )
                    
                    if status == 'reading':
                        cursor.execute(
                            "UPDATE books SET current_readers = current_readers + 1 WHERE id = ?",
                            (book_id,)
                        )
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка обновления статуса: {e}")
            return False
    
    def rate_book(self, user_id: int, book_id: int, rating: int) -> bool:
        """Оценивает книгу."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT id FROM user_books WHERE user_id = ? AND book_id = ?",
                    (user_id, book_id)
                )
                
                if not cursor.fetchone():
                    return False
                
                cursor.execute('''
                    UPDATE user_books 
                    SET rating = ?
                    WHERE user_id = ? AND book_id = ?
                ''', (rating, user_id, book_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка оценки книги: {e}")
            return False
    
    def get_user_books(self, user_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Получает книги пользователя."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                sql = '''
                    SELECT ub.*, b.title, b.author, b.genre, b.total_pages
                    FROM user_books ub
                    JOIN books b ON ub.book_id = b.id
                    WHERE ub.user_id = ?
                '''
                params = [user_id]
                
                if status:
                    sql += " AND ub.status = ?"
                    params.append(status)
                
                sql += " ORDER BY ub.added_at DESC"
                
                cursor.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Ошибка получения книг пользователя: {e}")
            return []
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получает статистику пользователя."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'planned' THEN 1 END) as planned,
                        COUNT(CASE WHEN status = 'reading' THEN 1 END) as reading,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                        COUNT(CASE WHEN status = 'dropped' THEN 1 END) as dropped,
                        AVG(rating) as avg_rating,
                        SUM(current_page) as total_pages_read
                    FROM user_books 
                    WHERE user_id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'total': result['total'] or 0,
                        'planned': result['planned'] or 0,
                        'reading': result['reading'] or 0,
                        'completed': result['completed'] or 0,
                        'dropped': result['dropped'] or 0,
                        'avg_rating': round(float(result['avg_rating'] or 0), 2),
                        'total_pages_read': result['total_pages_read'] or 0
                    }
                return {
                    'total': 0, 'planned': 0, 'reading': 0, 
                    'completed': 0, 'dropped': 0, 'avg_rating': 0,
                    'total_pages_read': 0
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                'total': 0, 'planned': 0, 'reading': 0, 
                'completed': 0, 'dropped': 0, 'avg_rating': 0,
                'total_pages_read': 0
            }
    
    def get_all_genres(self) -> List[str]:
        """Получает все жанры."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT genre FROM books WHERE genre IS NOT NULL ORDER BY genre")
                return [row['genre'] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения жанров: {e}")
            return ["Классика", "Фэнтези", "Роман", "Детектив", "Антиутопия"]
