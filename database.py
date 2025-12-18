"""
Модуль для работы с базой данных книг.
Хранит информацию о книгах, пользователях и их коллекциях.
"""

import sqlite3


class DatabaseError(Exception):
    """Ошибка при работе с базой данных"""
    pass


class Database:
    """Класс для работы с базой данных книг"""
    
    def __init__(self, db_name="books.db"):
        """
        Создает новую базу данных или подключается к существующей.
        
        Args:
            db_name (str): Имя файла базы данных. По умолчанию "books.db"
        """
        self.db_name = db_name
        self.setup_database()
    
    def connect(self):
        """Подключается к базе данных и возвращает соединение"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def setup_database(self):
        """Создает таблицы в базе данных, если их еще нет"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                pages INTEGER,
                genre TEXT,
                description TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                status TEXT DEFAULT 'planned',
                current_page INTEGER DEFAULT 0,
                rating INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (book_id) REFERENCES books(id)
            )
        ''')
        
        cursor.execute("SELECT COUNT(*) FROM books")
        if cursor.fetchone()[0] == 0:
            self.add_sample_books(cursor)
        
        conn.commit()
        conn.close()
    
    def add_sample_books(self, cursor):
        """Добавляет примеры книг в базу данных"""
        books = [
            ("Мастер и Маргарита", "Михаил Булгаков", 480, "Классика", "Роман о добре и зле"),
            ("Преступление и наказание", "Федор Достоевский", 671, "Классика", "Психологический роман"),
            ("1984", "Джордж Оруэлл", 328, "Антиутопия", "Роман о будущем"),
            ("Гарри Поттер и философский камень", "Джоан Роулинг", 320, "Фэнтези", "О мальчике-волшебнике"),
            ("Маленький принц", "Антуан де Сент-Экзюпери", 96, "Сказка", "Философская сказка"),
        ]
        
        for book in books:
            cursor.execute(
                "INSERT INTO books (title, author, pages, genre, description) VALUES (?, ?, ?, ?, ?)",
                book
            )
    
    def find_books(self, search_text="", genre="", limit=10):
        """
        Ищет книги по названию, автору или жанру.
        
        Args:
            search_text (str): Текст для поиска в названии или авторе
            genre (str): Жанр для фильтрации
            limit (int): Максимальное количество результатов
            
        Returns:
            list: Список найденных книг
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        query = "SELECT * FROM books WHERE 1=1"
        params = []
        
        if search_text:
            query += " AND (title LIKE ? OR author LIKE ?)"
            search_param = f"%{search_text}%"
            params.append(search_param)
            params.append(search_param)
        
        if genre:
            query += " AND genre = ?"
            params.append(genre)
        
        query += " ORDER BY title LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        books = cursor.fetchall()
        
        conn.close()
        return [dict(book) for book in books]
    
    def get_or_create_user(self, telegram_id, username="", first_name="", last_name=""):
        """
        Находит пользователя по ID Telegram или создает нового.
        
        Args:
            telegram_id (int): ID пользователя в Telegram
            username (str): Имя пользователя в Telegram
            first_name (str): Имя пользователя
            last_name (str): Фамилия пользователя
            
        Returns:
            int: ID пользователя в базе данных
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        
        if user:
            user_id = user['id']
            conn.close()
            return user_id
        cursor.execute(
            "INSERT INTO users (telegram_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
            (telegram_id, username, first_name, last_name)
        )
        user_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return user_id
    
    def add_book_to_user(self, user_id, book_id, status="planned"):
        """
        Добавляет книгу в коллекцию пользователя.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            status (str): Статус чтения ('planned', 'reading', 'completed', 'dropped')
            
        Returns:
            bool: True если книга добавлена, False если уже была
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM user_books WHERE user_id = ? AND book_id = ?",
            (user_id, book_id)
        )
        
        if cursor.fetchone():
            conn.close()
            return False

        cursor.execute(
            "INSERT INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)",
            (user_id, book_id, status)
        )
        
        conn.commit()
        conn.close()
        return True
    
    def remove_book_from_user(self, user_id, book_id):
        """
        Удаляет книгу из коллекции пользователя.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            
        Returns:
            bool: True если книга удалена, False если ее не было
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM user_books WHERE user_id = ? AND book_id = ?",
            (user_id, book_id)
        )
        
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return deleted
    
    def update_reading_status(self, user_id, book_id, status, current_page=0):
        """
        Обновляет статус чтения книги.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            status (str): Новый статус
            current_page (int): Текущая страница
            
        Returns:
            bool: True если обновлено, False если книги не было
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE user_books SET status = ?, current_page = ? WHERE user_id = ? AND book_id = ?",
            (status, current_page, user_id, book_id)
        )
        
        updated = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return updated
    
    def rate_book(self, user_id, book_id, rating):
        """
        Ставит оценку книге от 1 до 5.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            rating (int): Оценка от 1 до 5
            
        Returns:
            bool: True если оценка поставлена, False если ошибка
        """
        if rating < 1 or rating > 5:
            return False
        
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE user_books SET rating = ? WHERE user_id = ? AND book_id = ?",
            (rating, user_id, book_id)
        )
        
        updated = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return updated
    
    def get_user_books(self, user_id, status=None):
        """
        Получает список книг пользователя.
        
        Args:
            user_id (int): ID пользователя
            status (str, optional): Фильтр по статусу
            
        Returns:
            list: Список книг пользователя
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        query = """
            SELECT ub.*, b.title, b.author, b.genre, b.pages as total_pages
            FROM user_books ub
            JOIN books b ON ub.book_id = b.id
            WHERE ub.user_id = ?
        """
        params = [user_id]
        
        if status:
            query += " AND ub.status = ?"
            params.append(status)
        
        query += " ORDER BY ub.id DESC"
        
        cursor.execute(query, params)
        books = cursor.fetchall()
        
        conn.close()
        return [dict(book) for book in books]
    
    def get_user_stats(self, user_id):
        """
        Получает статистику пользователя.
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            dict: Статистика пользователя
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'planned' THEN 1 ELSE 0 END) as planned,
                SUM(CASE WHEN status = 'reading' THEN 1 ELSE 0 END) as reading,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'dropped' THEN 1 ELSE 0 END) as dropped,
                AVG(rating) as avg_rating,
                SUM(current_page) as pages_read
            FROM user_books 
            WHERE user_id = ?
        """, (user_id,))
        
        stats = cursor.fetchone()
        conn.close()
        
        if stats:
            return {
                'total': stats['total'] or 0,
                'planned': stats['planned'] or 0,
                'reading': stats['reading'] or 0,
                'completed': stats['completed'] or 0,
                'dropped': stats['dropped'] or 0,
                'avg_rating': round(stats['avg_rating'] or 0, 2),
                'total_pages_read': stats['pages_read'] or 0
            }
        
        return {
            'total': 0, 'planned': 0, 'reading': 0, 'completed': 0, 'dropped': 0,
            'avg_rating': 0, 'total_pages_read': 0
        }
    
    def get_all_genres(self):
        """
        Получает список всех жанров книг.
        
        Returns:
            list: Список жанров
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT genre FROM books WHERE genre IS NOT NULL ORDER BY genre")
        genres = [row['genre'] for row in cursor.fetchall()]
        
        conn.close()
        
        if not genres:
            return ["Классика", "Фэнтези", "Роман", "Детектив"]
        
        return genres
