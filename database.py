"""
Модуль для работы с базой данных книг.
Хранит информацию о книгах, пользователях и их коллекциях.
"""

import sqlite3


class DatabaseError(Exception):
    """Исключение для ошибок базы данных."""
    pass


class Database:
    """
    Основной класс для работы с базой данных книг.
    
    :ivar db_path: Путь к файлу базы данных
    :type db_path: str
    """
    
    def __init__(self, db_path="books.db"):
        """
        Конструктор класса.
        
        :param db_path: Путь к файлу базы данных
        :type db_path: str
        """
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """
        Создает и возвращает соединение с базой данных.
        
        :returns: Соединение с базой данных
        :rtype: sqlite3.Connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """
        Инициализирует базу данных и создает таблицы при необходимости.
        
        Создает три таблицы:
        1. books - информация о книгах
        2. users - информация о пользователях
        3. user_books - связь пользователей с книгами
        
        Если таблица books пуста, добавляет тестовые данные.
        
        :raises sqlite3.Error: При ошибках создания таблиц
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                total_pages INTEGER,
                genre TEXT,
                description TEXT
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                status TEXT DEFAULT 'planned',
                current_page INTEGER DEFAULT 0,
                rating INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (book_id) REFERENCES books(id),
                UNIQUE(user_id, book_id)
            )
        ''')
        
        cur.execute("SELECT COUNT(*) FROM books")
        if cur.fetchone()[0] == 0:
            self._add_test_books(cur)
        
        conn.commit()
        conn.close()
    
    def _add_test_books(self, cursor):
        """
        Добавляет тестовые книги в базу данных.
        
        :param cursor: Курсор для выполнения SQL-запросов
        :type cursor: sqlite3.Cursor
        """
        books = [
            ("Мастер и Маргарита", "Михаил Булгаков", 480, "Классика", "Философский роман"),
            ("Преступление и наказание", "Федор Достоевский", 671, "Классика", "Психологический роман"),
            ("1984", "Джордж Оруэлл", 328, "Антиутопия", "Роман о тоталитарном обществе"),
            ("Гарри Поттер и философский камень", "Джоан Роулинг", 320, "Фэнтези", "О юном волшебнике"),
            ("Маленький принц", "Антуан де Сент-Экзюпери", 96, "Сказка", "Философская сказка"),
        ]
        
        for book in books:
            cursor.execute('''
                INSERT INTO books (title, author, total_pages, genre, description)
                VALUES (?, ?, ?, ?, ?)
            ''', book)
    
    def get_book(self, book_id):
        """
        Получает информацию о книге по её ID.
        
        :param book_id: ID книги
        :type book_id: int
        :returns: Словарь с информацией о книге или None
        :rtype: dict or None
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cur.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def search_books(self, query="", genre="", limit=10):
        """
        Ищет книги по заданным критериям.
        
        :param query: Текст для поиска в названии и авторе
        :type query: str
        :param genre: Жанр для фильтрации
        :type genre: str
        :param limit: Максимальное количество результатов
        :type limit: int
        :returns: Список словарей с книгами
        :rtype: list
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        sql = "SELECT * FROM books WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (title LIKE ? OR author LIKE ?)"
            search = f"%{query}%"
            params.extend([search, search])
        
        if genre:
            sql += " AND genre = ?"
            params.append(genre)
        
        sql += " ORDER BY title LIMIT ?"
        params.append(limit)
        
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_book_stats(self, book_id):
        """
        Получает статистику по книге.
        
        :param book_id: ID книги
        :type book_id: int
        :returns: Статистика по книге
        :rtype: dict
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT 
                COUNT(ub.id) as total_added,
                COUNT(CASE WHEN ub.status = 'reading' THEN 1 END) as reading_now,
                AVG(ub.rating) as avg_rating,
                COUNT(ub.rating) as rating_count
            FROM books b
            LEFT JOIN user_books ub ON b.id = ub.book_id
            WHERE b.id = ?
            GROUP BY b.id
        ''', (book_id,))
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            return {
                'total_added': row['total_added'] or 0,
                'currently_reading': row['reading_now'] or 0,
                'avg_rating': round(float(row['avg_rating'] or 0), 2),
                'rating_count': row['rating_count'] or 0
            }
        
        return {
            'total_added': 0,
            'currently_reading': 0,
            'avg_rating': 0,
            'rating_count': 0
        }
    
    def get_top_books(self, criteria="rating", genre="", author="", limit=5):
        """
        Получает топ книг по заданным критериям.
        
        :param criteria: Критерий сортировки ('rating' или другое)
        :type criteria: str
        :param genre: Фильтр по жанру
        :type genre: str
        :param author: Фильтр по автору
        :type author: str
        :param limit: Максимальное количество
        :type limit: int
        :returns: Список топ книг
        :rtype: list
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        if criteria == 'rating':
            sql = '''
                SELECT b.*, 
                       COALESCE(AVG(ub.rating), 0) as calc_rating,
                       COUNT(ub.id) as total_added
                FROM books b
                LEFT JOIN user_books ub ON b.id = ub.book_id
                WHERE 1=1
            '''
        else:
            sql = '''
                SELECT b.*, 
                       COUNT(ub.id) as total_added,
                       COUNT(CASE WHEN ub.status = 'reading' THEN 1 END) as reading_now
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
            sql += " GROUP BY b.id ORDER BY calc_rating DESC, total_added DESC"
        else:
            sql += " GROUP BY b.id ORDER BY total_added DESC, reading_now DESC"
        
        sql += " LIMIT ?"
        params.append(limit)
        
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_or_create_user(self, telegram_id, username="", first_name="", last_name=""):
        """
        Получает или создает пользователя по Telegram ID.
        
        :param telegram_id: ID пользователя в Telegram
        :type telegram_id: int
        :param username: Имя пользователя
        :type username: str
        :param first_name: Имя
        :type first_name: str
        :param last_name: Фамилия
        :type last_name: str
        :returns: ID пользователя в базе данных
        :rtype: int
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        
        if row:
            user_id = row['id']
            conn.close()
            return user_id
        
        cur.execute('''
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, username, first_name, last_name))
        
        user_id = cur.lastrowid
        conn.commit()
        conn.close()
        
        return user_id
    
    def add_user_book(self, user_id, book_id, status="planned"):
        """
        Добавляет книгу в коллекцию пользователя.
        
        :param user_id: ID пользователя
        :type user_id: int
        :param book_id: ID книги
        :type book_id: int
        :param status: Статус книги
        :type status: str
        :returns: True если книга добавлена, False если уже существует
        :rtype: bool
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM user_books WHERE user_id = ? AND book_id = ?", 
                   (user_id, book_id))
        
        if cur.fetchone():
            conn.close()
            return False
        
        cur.execute('''
            INSERT INTO user_books (user_id, book_id, status)
            VALUES (?, ?, ?)
        ''', (user_id, book_id, status))
        
        conn.commit()
        conn.close()
        return True
    
    def remove_user_book(self, user_id, book_id):
        """
        Удаляет книгу из коллекции пользователя.
        
        :param user_id: ID пользователя
        :type user_id: int
        :param book_id: ID книги
        :type book_id: int
        :returns: True если книга удалена, False если не найдена
        :rtype: bool
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM user_books WHERE user_id = ? AND book_id = ?", 
                   (user_id, book_id))
        
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        
        return deleted
    
    def update_book_status(self, user_id, book_id, status, current_page=0):
        """
        Обновляет статус книги у пользователя.
        
        :param user_id: ID пользователя
        :type user_id: int
        :param book_id: ID книги
        :type book_id: int
        :param status: Новый статус
        :type status: str
        :param current_page: Текущая страница
        :type current_page: int
        :returns: True если обновлено, False если не найдено
        :rtype: bool
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute('''
            UPDATE user_books 
            SET status = ?, current_page = ?
            WHERE user_id = ? AND book_id = ?
        ''', (status, current_page, user_id, book_id))
        
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        
        return updated
    
    def rate_book(self, user_id, book_id, rating):
        """
        Оценивает книгу пользователем.
        
        :param user_id: ID пользователя
        :type user_id: int
        :param book_id: ID книги
        :type book_id: int
        :param rating: Оценка от 1 до 5
        :type rating: int
        :returns: True если оценка сохранена, False если неверная оценка или запись не найдена
        :rtype: bool
        """
        if rating < 1 or rating > 5:
            return False
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute('''
            UPDATE user_books 
            SET rating = ?
            WHERE user_id = ? AND book_id = ?
        ''', (rating, user_id, book_id))
        
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        
        return updated
    
    def get_user_books(self, user_id, status=None):
        """
        Получает книги пользователя.
        
        :param user_id: ID пользователя
        :type user_id: int
        :param status: Фильтр по статусу
        :type status: str
        :returns: Список книг пользователя
        :rtype: list
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
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
        
        sql += " ORDER BY ub.id DESC"
        
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_user_stats(self, user_id):
        """
        Получает статистику пользователя.
        
        :param user_id: ID пользователя
        :type user_id: int
        :returns: Статистика пользователя
        :rtype: dict
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'planned' THEN 1 END) as planned,
                COUNT(CASE WHEN status = 'reading' THEN 1 END) as reading,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'dropped' THEN 1 END) as dropped,
                AVG(rating) as avg_rating,
                SUM(current_page) as pages_read
            FROM user_books 
            WHERE user_id = ?
        ''', (user_id,))
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            return {
                'total': row['total'] or 0,
                'planned': row['planned'] or 0,
                'reading': row['reading'] or 0,
                'completed': row['completed'] or 0,
                'dropped': row['dropped'] or 0,
                'avg_rating': round(float(row['avg_rating'] or 0), 2),
                'total_pages_read': row['pages_read'] or 0
            }
        
        return {
            'total': 0,
            'planned': 0,
            'reading': 0,
            'completed': 0,
            'dropped': 0,
            'avg_rating': 0,
            'total_pages_read': 0
        }
    
    def get_all_genres(self):
        """
        Получает все уникальные жанры из базы данных.
        
        :returns: Список жанров
        :rtype: list
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT DISTINCT genre FROM books WHERE genre IS NOT NULL ORDER BY genre")
        rows = cur.fetchall()
        conn.close()
        
        genres = [row['genre'] for row in rows]
        
        return genres if genres else ["Классика", "Фэнтези", "Роман", "Детектив", "Антиутопия"]
    
    def add_book_to_catalog(self, title, author, pages, genre, description=""):
        """
        Добавляет новую книгу в каталог.
        
        Проверяет, нет ли уже такой книги. Если нет - добавляет.
        
        :param title: Название книги
        :type title: str
        :param author: Автор книги
        :type author: str
        :param pages: Количество страниц
        :type pages: int
        :param genre: Жанр книги
        :type genre: str
        :param description: Описание книги
        :type description: str
        :returns: Кортеж (success, book_id, message)
            - success (bool): True если успешно, False если ошибка
            - book_id (int): ID книги или None
            - message (str): Сообщение для пользователя
        :rtype: tuple
        :raises sqlite3.IntegrityError: При нарушении целостности данных
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            # Проверяем, есть ли уже такая книга
            cur.execute(
                'SELECT id FROM books WHERE LOWER(title) = LOWER(?) AND LOWER(author) = LOWER(?)',
                (title, author)
            )
            existing = cur.fetchone()
            
            if existing:
                # Книга уже есть в каталоге
                conn.close()
                return False, existing['id'], "Книга уже есть в каталоге"
            
            # Добавляем новую книгу
            cur.execute('''
                INSERT INTO books (title, author, total_pages, genre, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, author, pages, genre, description))
            
            book_id = cur.lastrowid
            conn.commit()
            conn.close()
            
            return True, book_id, "Книга успешно добавлена"
            
        except sqlite3.IntegrityError as e:
            conn.rollback()
            conn.close()
            return False, None, f"Ошибка базы данных: {str(e)}"
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, None, f"Неизвестная ошибка: {str(e)}"
