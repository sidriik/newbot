#!/usr/bin/env python3
"""
database.py - База данных книг для BookBot
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime


class DatabaseError(Exception):
    """Исключение для ошибок базы данных."""
    pass


class Database:
    """
    Класс для управления базой данных SQLite книжного бота.
    
    Обрабатывает все операции с книгами, пользователями и их коллекциями.
    """
    
    def __init__(self, db_path: str = "data/books.db"):
        """
        Инициализация подключения к базе данных.
        
        Args:
            db_path: Путь к файлу базы данных
            
        Raises:
            DatabaseError: Если не удалось создать/подключиться к БД
        """
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        
        try:
            # Создаем директорию если не существует
            self.db_path.parent.mkdir(exist_ok=True, parents=True)
            self._init_database()
            self.logger.info(f"База данных инициализирована: {self.db_path}")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации БД: {e}")
            raise DatabaseError(f"Не удалось инициализировать БД: {e}")
    
    def _get_connection(self):
        """Создает соединение с базой данных."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Инициализирует таблицы в базе данных."""
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
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
                    UNIQUE(user_id, book_id)
                )
            ''')
            
            # Создаем индексы для ускорения поиска
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_genre ON books(genre)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_books_user ON user_books(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_books_status ON user_books(status)')
            
            # Добавляем тестовые книги если таблица пуста
            cursor.execute("SELECT COUNT(*) FROM books")
            if cursor.fetchone()[0] == 0:
                self._add_sample_books(cursor)
            
            conn.commit()
    
    def _add_sample_books(self, cursor):
        """Добавляет тестовые книги в базу данных."""
        sample_books = [
            ("Мастер и Маргарита", "Михаил Булгаков", 480, "Классика", 
             "Философский роман о добре и зле, любви и творчестве"),
            ("Преступление и наказание", "Федор Достоевский", 671, "Классика",
             "Психологический роман о преступлении и его последствиях"),
            ("1984", "Джордж Оруэлл", 328, "Антиутопия",
             "Роман о тоталитарном обществе будущего"),
            ("Гарри Поттер и философский камень", "Джоан Роулинг", 320, "Фэнтези",
             "Первая книга о юном волшебнике Гарри Поттере"),
            ("Маленький принц", "Антуан де Сент-Экзюпери", 96, "Философская сказка",
             "Сказка-притча о дружбе, любви и ответственности"),
            ("Война и мир", "Лев Толстой", 1225, "Классика",
             "Эпопея о русском обществе во время войн с Наполеоном"),
            ("Три товарища", "Эрих Мария Ремарк", 480, "Роман",
             "Роман о дружбе, любви и потерях в послевоенной Германии"),
            ("Алхимик", "Пауло Коэльо", 208, "Роман",
             "Притча о поиске своего предназначения"),
            ("Шерлок Холмс. Сборник рассказов", "Артур Конан Дойл", 307, "Детектив",
             "Рассказы о знаменитом сыщике Шерлоке Холмсе"),
            ("Гордость и предубеждение", "Джейн Остин", 432, "Роман",
             "Классика английской литературы о любви и социальных предрассудках"),
            ("Метро 2033", "Дмитрий Глуховский", 384, "Постапокалипсис",
             "Роман о жизни в московском метро после ядерной войны"),
            ("Код да Винчи", "Дэн Браун", 489, "Детектив",
             "Детективный роман с историческими загадками"),
            ("451° по Фаренгейту", "Рэй Брэдбери", 256, "Антиутопия",
             "Роман о мире, где книги находятся под запретом"),
            ("Убить пересмешника", "Харпер Ли", 376, "Роман",
             "Роман о расовых предрассудках в американском Юге"),
            ("Портрет Дориана Грея", "Оскар Уайльд", 254, "Классика",
             "Философский роман о красоте, морали и вечной молодости")
        ]
        
        cursor.executemany('''
            INSERT INTO books (title, author, total_pages, genre, description)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_books)
    
    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает книгу по ID.
        
        Args:
            book_id: ID книги
            
        Returns:
            Словарь с данными книги или None если не найдена
            
        Raises:
            DatabaseError: При ошибке запроса
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка получения книги {book_id}: {e}")
            raise DatabaseError(f"Ошибка получения книги: {e}")
    
    def search_books(self, query: str = "", genre: str = "", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Ищет книги по различным критериям.
        
        Args:
            query: Строка для поиска в названии и авторе
            genre: Жанр для фильтрации
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных книг
            
        Raises:
            DatabaseError: При ошибке поиска
        """
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
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка поиска книг: {e}")
            raise DatabaseError(f"Ошибка поиска книг: {e}")
    
    def get_book_statistics(self, book_id: int) -> Dict[str, Any]:
        """
        Получает статистику по книге.
        
        Args:
            book_id: ID книги
            
        Returns:
            Словарь со статистикой
            
        Raises:
            DatabaseError: При ошибке запроса
        """
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
                return {
                    'total_added': 0,
                    'currently_reading': 0,
                    'avg_rating': 0.0,
                    'rating_count': 0
                }
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка получения статистики книги {book_id}: {e}")
            raise DatabaseError(f"Ошибка получения статистики: {e}")
    
    def get_top_books(self, criteria: str = "rating", genre: str = "", 
                     author: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Получает топ книг по указанному критерию.
        
        Args:
            criteria: 'rating' или 'popularity'
            genre: Фильтр по жанру
            author: Фильтр по автору
            limit: Количество результатов
            
        Returns:
            Список книг
            
        Raises:
            ValueError: При неверном критерии
            DatabaseError: При ошибке запроса
        """
        if criteria not in ['rating', 'popularity']:
            raise ValueError("Критерий должен быть 'rating' или 'popularity'")
        
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
                        HAVING COUNT(ub.rating) > 0
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
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка получения топ книг: {e}")
            raise DatabaseError(f"Ошибка получения топ книг: {e}")
    
    def get_or_create_user(self, telegram_id: int, username: str = "", 
                          first_name: str = "", last_name: str = "") -> int:
        """
        Получает или создает пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            username: Имя пользователя в Telegram
            first_name: Имя
            last_name: Фамилия
            
        Returns:
            ID пользователя в базе
            
        Raises:
            DatabaseError: При ошибке запроса
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем существование пользователя
                cursor.execute(
                    "SELECT id FROM users WHERE telegram_id = ?",
                    (telegram_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return result['id']
                
                # Создаем нового пользователя
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, username, first_name, last_name))
                
                conn.commit()
                return cursor.lastrowid
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка создания пользователя: {e}")
            raise DatabaseError(f"Ошибка создания пользователя: {e}")
    
    def add_user_book(self, user_id: int, book_id: int, status: str = "planned") -> bool:
        """
        Добавляет книгу пользователю.
        
        Args:
            user_id: ID пользователя
            book_id: ID книги
            status: Статус книги
            
        Returns:
            True если успешно, False если книга уже добавлена
            
        Raises:
            DatabaseError: При ошибке запроса
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли уже такая книга у пользователя
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
                
                # Обновляем статистику книги
                cursor.execute('''
                    UPDATE books 
                    SET added_count = added_count + 1,
                        current_readers = current_readers + ?
                    WHERE id = ?
                ''', (1 if status == 'reading' else 0, book_id))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка добавления книги пользователю: {e}")
            raise DatabaseError(f"Ошибка добавления книги пользователю: {e}")
    
    def remove_user_book(self, user_id: int, book_id: int) -> bool:
        """
        Удаляет книгу у пользователя.
        
        Args:
            user_id: ID пользователя
            book_id: ID книги
            
        Returns:
            True если успешно, False если книга не найдена
            
        Raises:
            DatabaseError: При ошибке запроса
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем статус книги перед удалением
                cursor.execute('''
                    SELECT status FROM user_books 
                    WHERE user_id = ? AND book_id = ?
                ''', (user_id, book_id))
                
                result = cursor.fetchone()
                if not result:
                    return False
                
                status = result['status']
                
                # Удаляем запись
                cursor.execute('''
                    DELETE FROM user_books 
                    WHERE user_id = ? AND book_id = ?
                ''', (user_id, book_id))
                
                # Обновляем статистику книги
                cursor.execute('''
                    UPDATE books 
                    SET added_count = added_count - 1,
                        current_readers = current_readers - ?
                    WHERE id = ?
                ''', (1 if status == 'reading' else 0, book_id))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка удаления книги у пользователя: {e}")
            raise DatabaseError(f"Ошибка удаления книги у пользователя: {e}")
    
    def update_book_status(self, user_id: int, book_id: int, 
                          status: str, current_page: int = 0) -> bool:
        """
        Обновляет статус книги у пользователя.
        
        Args:
            user_id: ID пользователя
            book_id: ID книги
            status: Новый статус
            current_page: Текущая страница
            
        Returns:
            True если успешно, False если книга не найдена
            
        Raises:
            DatabaseError: При ошибке запроса
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем старый статус
                cursor.execute('''
                    SELECT status FROM user_books 
                    WHERE user_id = ? AND book_id = ?
                ''', (user_id, book_id))
                
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
                
                # Обновляем статистику книги при изменении статуса чтения
                if old_status != status:
                    if old_status == 'reading':
                        cursor.execute('''
                            UPDATE books 
                            SET current_readers = current_readers - 1
                            WHERE id = ?
                        ''', (book_id,))
                    
                    if status == 'reading':
                        cursor.execute('''
                            UPDATE books 
                            SET current_readers = current_readers + 1
                            WHERE id = ?
                        ''', (book_id,))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка обновления статуса книги: {e}")
            raise DatabaseError(f"Ошибка обновления статуса книги: {e}")
    
    def rate_book(self, user_id: int, book_id: int, rating: int) -> bool:
        """
        Оценивает книгу.
        
        Args:
            user_id: ID пользователя
            book_id: ID книги
            rating: Оценка от 1 до 5
            
        Returns:
            True если успешно, False если книга не найдена
            
        Raises:
            ValueError: Если оценка вне диапазона 1-5
            DatabaseError: При ошибке запроса
        """
        if rating < 1 or rating > 5:
            raise ValueError("Оценка должна быть от 1 до 5")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли книга у пользователя
                cursor.execute('''
                    SELECT id FROM user_books 
                    WHERE user_id = ? AND book_id = ?
                ''', (user_id, book_id))
                
                if not cursor.fetchone():
                    return False
                
                # Обновляем оценку
                cursor.execute('''
                    UPDATE user_books 
                    SET rating = ?
                    WHERE user_id = ? AND book_id = ?
                ''', (rating, user_id, book_id))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка оценки книги: {e}")
            raise DatabaseError(f"Ошибка оценки книги: {e}")
    
    def get_user_books(self, user_id: int, status: str = None) -> List[Dict[str, Any]]:
        """
        Получает книги пользователя.
        
        Args:
            user_id: ID пользователя
            status: Статус для фильтрации
            
        Returns:
            Список книг пользователя
            
        Raises:
            DatabaseError: При ошибке запроса
        """
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
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка получения книг пользователя: {e}")
            raise DatabaseError(f"Ошибка получения книг пользователя: {e}")
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получает статистику пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь со статистикой
            
        Raises:
            DatabaseError: При ошибке запроса
        """
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
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка получения статистики пользователя: {e}")
            raise DatabaseError(f"Ошибка получения статистики пользователя: {e}")
    
    def get_all_genres(self) -> List[str]:
        """
        Получает список всех уникальных жанров.
        
        Returns:
            Список жанров
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT genre FROM books WHERE genre IS NOT NULL ORDER BY genre")
                return [row['genre'] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка получения жанров: {e}")
            return ["Классика", "Фэнтези", "Роман", "Детектив", "Антиутопия"]
    
    def close(self):
        """Закрывает соединение с базой данных."""
        pass  # SQLite автоматически закрывает соединение
