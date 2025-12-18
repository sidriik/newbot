"""
Модуль для работы с базой данных книг.
Хранит информацию о книгах, пользователях и их коллекциях.
"""

import sqlite3


# Ошибка базы данных
class DatabaseError(Exception):
    pass


# Главный класс для работы с базой
class Database:
    
    def __init__(self, db_path="books.db"):
        # Путь к файлу базы
        self.db_path = db_path
        # Создаем базу
        self.init_db()
    
    # Подключиться к базе
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Чтобы результаты были как словари
        return conn
    
    # Создать базу и таблицы
    def init_db(self):
        conn = self.get_connection()
        cur = conn.cursor()
        
        # Таблица с книгами
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
        
        # Таблица с пользователями
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT
            )
        ''')
        
        # Таблица связей (какие книги у каких пользователей)
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
        
        # Проверим, есть ли уже книги
        cur.execute("SELECT COUNT(*) FROM books")
        count = cur.fetchone()[0]
        
        # Если книг нет, добавим тестовые
        if count == 0:
            self.add_test_books(cur)
        
        conn.commit()
        conn.close()
    
    # Добавить тестовые книги
    def add_test_books(self, cur):
        # Список книг для добавления
        books = [
            ("Мастер и Маргарита", "Михаил Булгаков", 480, "Классика", "Философский роман"),
            ("Преступление и наказание", "Федор Достоевский", 671, "Классика", "Психологический роман"),
            ("1984", "Джордж Оруэлл", 328, "Антиутопия", "Роман о тоталитарном обществе"),
            ("Гарри Поттер и философский камень", "Джоан Роулинг", 320, "Фэнтези", "О юном волшебнике"),
            ("Маленький принц", "Антуан де Сент-Экзюпери", 96, "Сказка", "Философская сказка"),
            ("Война и мир", "Лев Толстой", 1225, "Классика", "Эпопея"),
            ("Три товарища", "Эрих Мария Ремарк", 480, "Роман", "О дружбе и любви"),
            ("Алхимик", "Пауло Коэльо", 208, "Роман", "Притча"),
            ("Шерлок Холмс", "Артур Конан Дойл", 307, "Детектив", "Рассказы о сыщике"),
            ("Гордость и предубеждение", "Джейн Остин", 432, "Роман", "Классика"),
        ]
        
        # Добавляем каждую книгу
        for book in books:
            cur.execute('''
                INSERT INTO books (title, author, total_pages, genre, description)
                VALUES (?, ?, ?, ?, ?)
            ''', book)
    
    # Получить книгу по ID
    def get_book(self, book_id):
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cur.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)  # Превращаем в словарь
        return None
    
    # Поиск книг
    def search_books(self, query="", genre="", limit=10):
        conn = self.get_connection()
        cur = conn.cursor()
        
        # Начинаем запрос
        sql = "SELECT * FROM books WHERE 1=1"
        params = []
        
        # Если есть текст для поиска
        if query:
            sql += " AND (title LIKE ? OR author LIKE ?)"
            search = f"%{query}%"
            params.append(search)
            params.append(search)
        
        # Если выбран жанр
        if genre:
            sql += " AND genre = ?"
            params.append(genre)
        
        # Сортировка и лимит
        sql += " ORDER BY title LIMIT ?"
        params.append(limit)
        
        # Выполняем запрос
        cur.execute(sql, params)
        rows = cur.fetchall()
        
        conn.close()
        
        # Превращаем все в словари
        result = []
        for row in rows:
            result.append(dict(row))
        return result
    
    # Статистика по книге
    def get_book_stats(self, book_id):
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
        
        # Если нет статистики
        return {
            'total_added': 0,
            'currently_reading': 0,
            'avg_rating': 0,
            'rating_count': 0
        }
    
    # Топ книг
    def get_top_books(self, criteria="rating", genre="", author="", limit=5):
        conn = self.get_connection()
        cur = conn.cursor()
        
        # Выбираем как сортировать
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
        
        # Фильтр по жанру
        if genre:
            sql += " AND b.genre = ?"
            params.append(genre)
        
        # Фильтр по автору
        if author:
            sql += " AND b.author LIKE ?"
            params.append(f"%{author}%")
        
        # Сортировка
        if criteria == 'rating':
            sql += " GROUP BY b.id ORDER BY calc_rating DESC, total_added DESC"
        else:
            sql += " GROUP BY b.id ORDER BY total_added DESC, reading_now DESC"
        
        # Лимит
        sql += " LIMIT ?"
        params.append(limit)
        
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        
        # Возвращаем список словарей
        result = []
        for row in rows:
            result.append(dict(row))
        return result
    
    # Получить или создать пользователя
    def get_or_create_user(self, telegram_id, username="", first_name="", last_name=""):
        conn = self.get_connection()
        cur = conn.cursor()
        
        # Ищем пользователя
        cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        
        # Если нашли
        if row:
            user_id = row['id']
            conn.close()
            return user_id
        
        # Если не нашли - создаем
        cur.execute('''
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, username, first_name, last_name))
        
        user_id = cur.lastrowid
        conn.commit()
        conn.close()
        
        return user_id
    
    # Добавить книгу пользователю
    def add_user_book(self, user_id, book_id, status="planned"):
        conn = self.get_connection()
        cur = conn.cursor()
        
        # Проверим, есть ли уже такая книга
        cur.execute("SELECT id FROM user_books WHERE user_id = ? AND book_id = ?", (user_id, book_id))
        if cur.fetchone():
            conn.close()
            return False  # Уже есть
        
        # Добавляем
        cur.execute('''
            INSERT INTO user_books (user_id, book_id, status)
            VALUES (?, ?, ?)
        ''', (user_id, book_id, status))
        
        conn.commit()
        conn.close()
        return True
    
    # Удалить книгу у пользователя
    def remove_user_book(self, user_id, book_id):
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM user_books WHERE user_id = ? AND book_id = ?", (user_id, book_id))
        deleted = cur.rowcount > 0
        
        conn.commit()
        conn.close()
        return deleted
    
    # Обновить статус книги
    def update_book_status(self, user_id, book_id, status, current_page=0):
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
    
    # Оценить книгу
    def rate_book(self, user_id, book_id, rating):
        # Проверка оценки
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
    
    # Получить книги пользователя
    def get_user_books(self, user_id, status=None):
        conn = self.get_connection()
        cur = conn.cursor()
        
        sql = '''
            SELECT ub.*, b.title, b.author, b.genre, b.total_pages
            FROM user_books ub
            JOIN books b ON ub.book_id = b.id
            WHERE ub.user_id = ?
        '''
        params = [user_id]
        
        # Фильтр по статусу
        if status:
            sql += " AND ub.status = ?"
            params.append(status)
        
        sql += " ORDER BY ub.added_at DESC"
        
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        
        # В список словарей
        result = []
        for row in rows:
            result.append(dict(row))
        return result
    
    # Статистика пользователя
    def get_user_stats(self, user_id):
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
        
        # Если нет книг
        return {
            'total': 0,
            'planned': 0,
            'reading': 0,
            'completed': 0,
            'dropped': 0,
            'avg_rating': 0,
            'total_pages_read': 0
        }
    
    # Все жанры
    def get_all_genres(self):
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT DISTINCT genre FROM books WHERE genre IS NOT NULL ORDER BY genre")
        rows = cur.fetchall()
        
        conn.close()
        
        # Извлекаем жанры
        genres = []
        for row in rows:
            genres.append(row['genre'])
        
        # Если нет жанров - возвращаем тестовые
        if not genres:
            return ["Классика", "Фэнтези", "Роман", "Детектив", "Антиутопия"]
        
        return genres
