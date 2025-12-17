#!/usr/bin/env python3
"""
database.py - Модуль для работы с базой данных SQLite BookBot

Этот модуль содержит классы и функции для взаимодействия с базой данных,
включая создание таблиц, добавление, удаление и поиск книг и записей о чтении.
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
from contextlib import closing
from pathlib import Path


class DatabaseError(Exception):
    """Исключение для ошибок базы данных."""
    pass


class Database:
    """Класс для работы с базой данных книг и пользователей."""
    
    def __init__(self, db_path: str):
        """
        Инициализация подключения к базе данных.
        
        Args:
            db_path (str): Путь к файлу базы данных SQLite
            
        Raises:
            DatabaseError: Если не удалось подключиться к базе данных
        """
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        
        try:
            # Создаем директорию для базы данных, если её нет
            self.db_path.parent.mkdir(exist_ok=True, parents=True)
            
            # Инициализируем базу данных
            self._init_database()
            self.logger.info(f"База данных инициализирована: {self.db_path}")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации базы данных: {e}")
            raise DatabaseError(f"Не удалось инициализировать базу данных: {e}")
    
    def _init_database(self) -> None:
        """
        Инициализирует таблицы базы данных.
        
        Создает таблицы books, users и user_books, если они не существуют.
        Также заполняет таблицу books тестовыми данными.
        """
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Таблица книг
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        total_pages INTEGER NOT NULL DEFAULT 0,
                        genre TEXT,
                        description TEXT,
                        added_count INTEGER DEFAULT 0,  -- сколько раз добавили
                        current_readers INTEGER DEFAULT 0  -- сколько читают сейчас
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
                
                # Таблица пользовательских книг
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        book_id INTEGER NOT NULL,
                        status TEXT CHECK(status IN ('planned', 'reading', 'completed', 'dropped')),
                        current_page INTEGER DEFAULT 0,
                        rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (book_id) REFERENCES books (id),
                        UNIQUE(user_id, book_id)
                    )
                ''')
                
                # Создаем индексы для ускорения поиска
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_genre ON books(genre)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_books_user_id ON user_books(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_books_book_id ON user_books(book_id)')
                
                # Проверяем, есть ли книги в базе
                cursor.execute("SELECT COUNT(*) FROM books")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    self._populate_initial_books(cursor)
                
                conn.commit()
                self.logger.info(f"База данных инициализирована. Книг в базе: {count}")
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка SQLite при инициализации: {e}")
            raise DatabaseError(f"Ошибка SQLite: {e}")
    
    def _populate_initial_books(self, cursor: sqlite3.Cursor) -> None:
        """
        Заполняет базу данных начальным набором книг.
        
        Args:
            cursor (sqlite3.Cursor): Курсор базы данных
        """
        initial_books = [
            ("Преступление и наказание", "Федор Достоевский", 671, "Классика", 
             "Роман о преступлении и его последствиях"),
            ("Мастер и Маргарита", "Михаил Булгаков", 480, "Классика", 
             "Мистический роман о визите дьявола в Москву"),
            ("1984", "Джордж Оруэлл", 328, "Антиутопия", 
             "Роман о тоталитарном обществе"),
            ("Гарри Поттер и философский камень", "Джоан Роулинг", 320, "Фэнтези", 
             "Первая книга о юном волшебнике"),
            ("Война и мир", "Лев Толстой", 1225, "Классика", 
             "Эпопея о войне 1812 года"),
            ("Маленький принц", "Антуан де Сент-Экзюпери", 96, "Притча", 
             "Философская сказка для детей и взрослых"),
            ("Три товарища", "Эрих Мария Ремарк", 480, "Роман", 
             "Роман о дружбе и любви"),
            ("Анна Каренина", "Лев Толстой", 864, "Классика", 
             "Роман о любви и трагедии"),
            ("Шерлок Холмс", "Артур Конан Дойл", 307, "Детектив", 
             "Сборник рассказов о знаменитом сыщике"),
            ("Гордость и предубеждение", "Джейн Остин", 432, "Роман", 
             "Классика английской литературы"),
            ("Зов Ктулху", "Говард Лавкрафт", 320, "Ужасы", 
             "Сборник рассказов в жанре хоррор"),
            ("Властелин Колец", "Джон Р. Р. Толкин", 1178, "Фэнтези", 
             "Эпическая фэнтези-сага"),
            ("Алхимик", "Пауло Коэльо", 208, "Роман", 
             "Философская притча о поиске своего предназначения"),
            ("Код да Винчи", "Дэн Браун", 489, "Детектив", 
             "Детективный роман с историческими загадками"),
            ("451° по Фаренгейту", "Рэй Брэдбери", 256, "Антиутопия", 
             "Роман о мире, где книги запрещены"),
        ]
        
        cursor.executemany('''
            INSERT INTO books (title, author, total_pages, genre, description)
            VALUES (?, ?, ?, ?, ?)
        ''', initial_books)
        
        self.logger.info(f"Добавлено {len(initial_books)} начальных книг")
    
    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить книгу по ID.
        
        Args:
            book_id (int): ID книги
            
        Returns:
            Optional[Dict[str, Any]]: Словарь с данными книги или None, если книга не найдена
            
        Raises:
            DatabaseError: Если произошла ошибка при запросе
        """
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
                result = cursor.fetchone()
                
                if result:
                    book = dict(result)
                    # Получаем статистику по книге
                    book['statistics'] = self.get_book_statistics(book_id)
                    return book
                return None
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка при получении книги {book_id}: {e}")
            raise DatabaseError(f"Ошибка при получении книги: {e}")
    
    def search_books(self, query: str = "", genre: str = "", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Поиск книг по запросу и/или жанру.
        
        Args:
            query (str): Поисковый запрос (ищется в названии и авторе)
            genre (str): Жанр для фильтрации
            limit (int): Максимальное количество результатов
            
        Returns:
            List[Dict[str, Any]]: Список найденных книг
            
        Raises:
            DatabaseError: Если произошла ошибка при поиске
        """
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                sql = "SELECT * FROM books WHERE 1=1"
                params = []
                
                if query:
                    sql += " AND (title LIKE ? OR author LIKE ?)"
                    search_pattern = f"%{query}%"
                    params.extend([search_pattern, search_pattern])
                
                if genre:
                    sql += " AND genre = ?"
                    params.append(genre)
                
                sql += " ORDER BY title LIMIT ?"
                params.append(limit)
                
                cursor.execute(sql, params)
                results = cursor.fetchall()
                
                books = []
                for row in results:
                    book = dict(row)
                    book['statistics'] = self.get_book_statistics(book['id'])
                    books.append(book)
                
                return books
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка при поиске книг: {e}")
            raise DatabaseError(f"Ошибка при поиске книг: {e}")
    
    def get_book_statistics(self, book_id: int) -> Dict[str, Any]:
        """
        Получить статистику по книге.
        
        Args:
            book_id (int): ID книги
            
        Returns:
            Dict[str, Any]: Статистика книги
            
        Raises:
            DatabaseError: Если произошла ошибка при запросе
        """
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Общее количество добавлений
                cursor.execute('''
                    SELECT COUNT(*) as total_added,
                           COUNT(CASE WHEN status = 'reading' THEN 1 END) as currently_reading,
                           AVG(rating) as avg_rating,
                           COUNT(rating) as rating_count
                    FROM user_books 
                    WHERE book_id = ?
                ''', (book_id,))
                
                stats = cursor.fetchone()
                if stats:
                    return {
                        'total_added': stats[0] or 0,
                        'currently_reading': stats[1] or 0,
                        'avg_rating': round(stats[2] or 0, 2),
                        'rating_count': stats[3] or 0
                    }
                return {'total_added': 0, 'currently_reading': 0, 'avg_rating': 0, 'rating_count': 0}
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка при получении статистики книги {book_id}: {e}")
            raise DatabaseError(f"Ошибка при получении статистики: {e}")
    
    def get_top_books(self, criteria: str = "rating", genre: str = "", 
                     author: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Получить топ книг по рейтингу или популярности.
        
        Args:
            criteria (str): Критерий сортировки ('rating' или 'popularity')
            genre (str): Жанр для фильтрации
            author (str): Автор для фильтрации
            limit (int): Максимальное количество результатов
            
        Returns:
            List[Dict[str, Any]]: Список книг
            
        Raises:
            DatabaseError: Если произошла ошибка при запросе
            ValueError: Если передан неверный критерий
        """
        if criteria not in ['rating', 'popularity']:
            raise ValueError("Критерий должен быть 'rating' или 'popularity'")
        
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # В зависимости от критерия выбираем разные SQL-запросы
                if criteria == 'rating':
                    sql = '''
                        SELECT b.*, 
                               COALESCE(AVG(ub.rating), 0) as calculated_rating,
                               COUNT(ub.id) as total_added
                        FROM books b
                        LEFT JOIN user_books ub ON b.id = ub.book_id AND ub.rating IS NOT NULL
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
                        HAVING COUNT(ub.rating) >= 1
                        ORDER BY calculated_rating DESC, total_added DESC
                        LIMIT ?
                    '''
                else:
                    sql += '''
                        GROUP BY b.id
                        ORDER BY total_added DESC, currently_reading DESC
                        LIMIT ?
                    '''
                
                params.append(limit)
                
                cursor.execute(sql, params)
                results = cursor.fetchall()
                
                books = []
                for row in results:
                    book = dict(row)
                    book['statistics'] = self.get_book_statistics(book['id'])
                    books.append(book)
                
                return books
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка при получении топ книг: {e}")
            raise DatabaseError(f"Ошибка при получении топ книг: {e}")
    
    def get_or_create_user(self, telegram_id: int, username: str = "", 
                          first_name: str = "", last_name: str = "") -> int:
        """
        Получить или создать пользователя.
        
        Args:
            telegram_id (int): Telegram ID пользователя
            username (str): Имя пользователя в Telegram
            first_name (str): Имя пользователя
            last_name (str): Фамилия пользователя
            
        Returns:
            int: ID пользователя в базе данных
            
        Raises:
            DatabaseError: Если произошла ошибка при запросе
        """
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Проверяем существование пользователя
                cursor.execute(
                    "SELECT id FROM users WHERE telegram_id = ?",
                    (telegram_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                
                # Создаем нового пользователя
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, username, first_name, last_name))
                
                conn.commit()
                return cursor.lastrowid
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка при создании пользователя: {e}")
            raise DatabaseError(f"Ошибка при создании пользователя: {e}")
    
    def add_user_book(self, user_id: int, book_id: int, status: str = "planned") -> bool:
        """
        Добавить книгу пользователю.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            status (str): Статус книги
            
        Returns:
            bool: True если успешно, False если книга уже добавлена
            
        Raises:
            DatabaseError: Если произошла ошибка при запросе
        """
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли уже такая книга у пользователя
                cursor.execute('''
                    SELECT id FROM user_books 
                    WHERE user_id = ? AND book_id = ?
                ''', (user_id, book_id))
                
                if cursor.fetchone():
                    return False
                
                # Добавляем книгу пользователю
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
            self.logger.error(f"Ошибка при добавлении книги пользователю: {e}")
            raise DatabaseError(f"Ошибка при добавлении книги пользователю: {e}")
    
    def remove_user_book(self, user_id: int, book_id: int) -> bool:
        """
        Удалить книгу у пользователя.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            
        Returns:
            bool: True если успешно, False если книга не найдена
            
        Raises:
            DatabaseError: Если произошла ошибка при запросе
        """
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Получаем статус книги перед удалением
                cursor.execute('''
                    SELECT status FROM user_books 
                    WHERE user_id = ? AND book_id = ?
                ''', (user_id, book_id))
                
                result = cursor.fetchone()
                if not result:
                    return False
                
                status = result[0]
                
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
            self.logger.error(f"Ошибка при удалении книги у пользователя: {e}")
            raise DatabaseError(f"Ошибка при удалении книги у пользователя: {e}")
    
    def update_book_status(self, user_id: int, book_id: int, 
                          status: str, current_page: int = 0) -> bool:
        """
        Обновить статус книги у пользователя.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            status (str): Новый статус
            current_page (int): Текущая страница
            
        Returns:
            bool: True если успешно, False если книга не найдена
            
        Raises:
            DatabaseError: Если произошла ошибка при запросе
        """
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Получаем старый статус
                cursor.execute('''
                    SELECT status FROM user_books 
                    WHERE user_id = ? AND book_id = ?
                ''', (user_id, book_id))
                
                result = cursor.fetchone()
                if not result:
                    return False
                
                old_status = result[0]
                
                # Обновляем статус
                cursor.execute('''
                    UPDATE user_books 
                    SET status = ?, current_page = ?
                    WHERE user_id = ? AND book_id = ?
                ''', (status, current_page, user_id, book_id))
                
                # Обновляем статистику книги
                if old_status != status:
                    # Уменьшаем счетчик для старого статуса
                    if old_status == 'reading':
                        cursor.execute('''
                            UPDATE books 
                            SET current_readers = current_readers - 1
                            WHERE id = ?
                        ''', (book_id,))
                    
                    # Увеличиваем счетчик для нового статуса
                    if status == 'reading':
                        cursor.execute('''
                            UPDATE books 
                            SET current_readers = current_readers + 1
                            WHERE id = ?
                        ''', (book_id,))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка при обновлении статуса книги: {e}")
            raise DatabaseError(f"Ошибка при обновлении статуса книги: {e}")
    
    def rate_book(self, user_id: int, book_id: int, rating: int) -> bool:
        """
        Оценить книгу.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            rating (int): Оценка от 1 до 5
            
        Returns:
            bool: True если успешно, False если книга не найдена
            
        Raises:
            DatabaseError: Если произошла ошибка при запросе
            ValueError: Если оценка не в диапазоне 1-5
        """
        if rating < 1 or rating > 5:
            raise ValueError("Оценка должна быть от 1 до 5")
        
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
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
            self.logger.error(f"Ошибка при оценке книги: {e}")
            raise DatabaseError(f"Ошибка при оценке книги: {e}")
    
    def get_user_books(self, user_id: int, status: str = None) -> List[Dict[str, Any]]:
        """
        Получить книги пользователя.
        
        Args:
            user_id (int): ID пользователя
            status (str, optional): Статус для фильтрации
            
        Returns:
            List[Dict[str, Any]]: Список книг пользователя
            
        Raises:
            DatabaseError: Если произошла ошибка при запросе
        """
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
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
                results = cursor.fetchall()
                
                return [dict(row) for row in results]
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка при получении книг пользователя: {e}")
            raise DatabaseError(f"Ошибка при получении книг пользователя: {e}")
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получить статистику пользователя.
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            Dict[str, Any]: Статистика пользователя
            
        Raises:
            DatabaseError: Если произошла ошибка при запросе
        """
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
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
                        'total': result[0] or 0,
                        'planned': result[1] or 0,
                        'reading': result[2] or 0,
                        'completed': result[3] or 0,
                        'dropped': result[4] or 0,
                        'avg_rating': round(result[5] or 0, 2),
                        'total_pages_read': result[6] or 0
                    }
                return {
                    'total': 0, 'planned': 0, 'reading': 0, 
                    'completed': 0, 'dropped': 0, 'avg_rating': 0,
                    'total_pages_read': 0
                }
                
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка при получении статистики пользователя: {e}")
            raise DatabaseError(f"Ошибка при получении статистики пользователя: {e}")
