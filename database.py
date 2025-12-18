import sqlite3

class DatabaseError(Exception):
    """Специальное исключение для ошибок базы данных нашего приложения."""
    pass

class Database:
    """
    Основной класс для работы с базой данных SQLite книжного бота.
    
    Отвечает за создание таблиц и выполнение всех операций с данными.
    Создает три таблицы:
    - books: информация о книгах (название, автор, жанр, описание)
    - users: зарегистрированные пользователи Telegram
    - user_books: связь пользователей с книгами (статус, прогресс, оценка)
    
    :ivar db_path: Путь к файлу базы данных SQLite
    :type db_path: str
    """
    
    def __init__(self, db_path="books.db"):
        """
        Инициализирует объект базы данных.
        
        :param db_path: путь к файлу базы данных SQLite
        :type db_path: str
        """
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """
        Создает новое соединение с базой данных.
        
        :returns: активное соединение с базой данных
        :type: sqlite3.Connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """
        Инициализирует базу данных: создает все необходимые таблицы,
        если они еще не существуют, и добавляет тестовые данные.
        
        :raises DatabaseError: Если произошла ошибка при создании таблиц
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            # Таблица книг
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
            
            # Таблица пользователей
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT
                )
            ''')
            
            # Таблица связи пользователей и книг
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
            
            # Проверяем, есть ли уже книги в базе
            cur.execute("SELECT COUNT(*) FROM books")
            if cur.fetchone()[0] == 0:
                self._add_test_books(cur)
            
            conn.commit()
            
        except sqlite3.Error as e:
            conn.rollback()
            raise DatabaseError(f"Ошибка инициализации базы данных: {e}")
        finally:
            conn.close()
    
    def _add_test_books(self, cursor):
        """
        Вспомогательный метод для добавления тестовых книг в пустую базу.
        
        :param cursor: активный курсор базы данных
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
        Получает информацию о книге по её уникальному идентификатору.
        
        :param book_id: числовой идентификатор книги
        :type book_id: int
        :returns: словарь с данными книги или None, если книга не найдена
        :type: dict or None
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def search_books(self, query="", genre="", limit=10):
        """
        Ищет книги в базе данных по различным критериям.
        
        :param query: строка для поиска в названии или авторе книги
        :type query: str
        :param genre: фильтр по жанру (точное совпадение)
        :type genre: str
        :param limit: максимальное количество возвращаемых результатов
        :type limit: int
        :returns: список словарей с найденными книгами
        :type: list
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
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
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def get_book_stats(self, book_id):
        """
        Собирает статистику по конкретной книге.
        
        :param book_id: идентификатор книги
        :type book_id: int
        :returns: словарь со статистикой книги
        :type: dict
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
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
            if row:
                return {
                    'total_added': row['total_added'] or 0,
                    'currently_reading': row['reading_now'] or 0,
                    'avg_rating': round(float(row['avg_rating'] or 0), 2),
                    'rating_count': row['rating_count'] or 0
                }
            
            # Если книга не найдена или у нее нет статистики
            return {
                'total_added': 0,
                'currently_reading': 0,
                'avg_rating': 0,
                'rating_count': 0
            }
        finally:
            conn.close()
    
    def get_top_books(self, criteria="rating", genre="", author="", title="", limit=5):
        """
        Получает топ книг по рейтингу или популярности с возможностью фильтрации.

        Args:
            criteria (str): Критерий сортировки ('rating' или другое)
            genre (str): Фильтр по жанру
            author (str): Фильтр по автору
            title (str): Фильтр по названию - НОВЫЙ ПАРАМЕТР
            limit (int): Максимальное количество

        Returns:
            list: Список топ книг
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
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
            
            # НОВЫЙ ФИЛЬТР: по названию книги
            if title:
                sql += " AND b.title LIKE ?"
                params.append(f"%{title}%")
            
            if criteria == 'rating':
                sql += " GROUP BY b.id ORDER BY calc_rating DESC, total_added DESC"
            else:
                sql += " GROUP BY b.id ORDER BY total_added DESC, reading_now DESC"
            
            sql += " LIMIT ?"
            params.append(limit)
            
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def get_or_create_user(self, telegram_id, username="", first_name="", last_name=""):
        """
        Находит пользователя по Telegram ID или создает нового.
        
        :param telegram_id: уникальный ID пользователя в Telegram
        :type telegram_id: int
        :param username: @username пользователя
        :type username: str
        :param first_name: имя пользователя
        :type first_name: str
        :param last_name: фамилия пользователя
        :type last_name: str
        :returns: ID пользователя в нашей базе данных
        :type: int
        :raises DatabaseError: Если произошла ошибка при создании пользователя
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            # Пытаемся найти существующего пользователя
            cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cur.fetchone()
            
            if row:
                # Пользователь уже существует
                user_id = row['id']
                return user_id
            
            # Создаем нового пользователя
            cur.execute('''
                INSERT INTO users (telegram_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (telegram_id, username, first_name, last_name))
            
            user_id = cur.lastrowid
            conn.commit()
            return user_id
            
        except sqlite3.IntegrityError:
            # В очень редком случае одновременного создания
            conn.rollback()
            # Повторно ищем пользователя
            cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cur.fetchone()
            return row['id'] if row else None
        finally:
            conn.close()
    
    def add_user_book(self, user_id, book_id, status="planned"):
        """
        Добавляет книгу в коллекцию пользователя.
        
        :param user_id: ID пользователя в нашей базе
        :type user_id: int
        :param book_id: ID книги
        :type book_id: int
        :param status: начальный статус
        :type status: str
        :returns: True если книга успешно добавлена, False если уже есть
        :type: bool
        :raises DatabaseError: Если произошла ошибка при добавлении
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            # Проверяем, есть ли уже такая книга у пользователя
            cur.execute(
                "SELECT id FROM user_books WHERE user_id = ? AND book_id = ?", 
                (user_id, book_id)
            )
            
            if cur.fetchone():
                return False  # Книга уже есть
            
            # Добавляем книгу
            cur.execute('''
                INSERT INTO user_books (user_id, book_id, status)
                VALUES (?, ?, ?)
            ''', (user_id, book_id, status))
            
            conn.commit()
            return True
            
        except sqlite3.IntegrityError as e:
            conn.rollback()
            if "UNIQUE" in str(e):
                return False
            raise DatabaseError(f"Ошибка добавления книги: {e}")
        finally:
            conn.close()
    
    def remove_user_book(self, user_id, book_id):
        """
        Удаляет книгу из коллекции пользователя.
        
        :param user_id: ID пользователя
        :type user_id: int
        :param book_id: ID книги
        :type book_id: int
        :returns: True если книга успешно удалена, False если книги не было
        :type: bool
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute(
                "DELETE FROM user_books WHERE user_id = ? AND book_id = ?", 
                (user_id, book_id)
            )
            
            deleted = cur.rowcount > 0
            conn.commit()
            return deleted
        finally:
            conn.close()
    
    def update_book_status(self, user_id, book_id, status, current_page=0):
        """
        Обновляет статус чтения книги у пользователя.
        
        :param user_id: ID пользователя
        :type user_id: int
        :param book_id: ID книги
        :type book_id: int
        :param status: новый статус
        :type status: str
        :param current_page: текущая страница
        :type current_page: int
        :returns: True если статус обновлен, False если запись не найдена
        :type: bool
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                UPDATE user_books 
                SET status = ?, current_page = ?
                WHERE user_id = ? AND book_id = ?
            ''', (status, current_page, user_id, book_id))
            
            updated = cur.rowcount > 0
            conn.commit()
            return updated
        finally:
            conn.close()
    
    def rate_book(self, user_id, book_id, rating):
        """
        Оценивает книгу пользователем.
        
        :param user_id: ID пользователя
        :type user_id: int
        :param book_id: ID книги
        :type book_id: int
        :param rating: оценка от 1 до 5
        :type rating: int
        :returns: True если оценка сохранена, False если неверная оценка или запись не найдена
        :type: bool
        """
        if rating < 1 or rating > 5:
            return False
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                UPDATE user_books 
                SET rating = ?
                WHERE user_id = ? AND book_id = ?
            ''', (rating, user_id, book_id))
            
            updated = cur.rowcount > 0
            conn.commit()
            return updated
        finally:
            conn.close()
    
    def get_user_books(self, user_id, status=None):
        """
        Получает все книги пользователя с возможностью фильтрации по статусу.
        
        :param user_id: ID пользователя
        :type user_id: int
        :param status: фильтр по статусу
        :type status: str
        :returns: список словарей с книгами пользователя
        :type: list
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
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
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def get_user_stats(self, user_id):
        """
        Собирает статистику по пользователю.
        
        :param user_id: ID пользователя
        :type user_id: int
        :returns: статистика пользователя
        :type: dict
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
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
            
            # Если у пользователя нет книг
            return {
                'total': 0,
                'planned': 0,
                'reading': 0,
                'completed': 0,
                'dropped': 0,
                'avg_rating': 0,
                'total_pages_read': 0
            }
        finally:
            conn.close()
    
    def get_all_genres(self):
        """
        Получает список всех уникальных жанров из базы данных.
        
        :returns: отсортированный список жанров
        :type: list
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute(
                "SELECT DISTINCT genre FROM books WHERE genre IS NOT NULL ORDER BY genre"
            )
            rows = cur.fetchall()
            genres = [row['genre'] for row in rows]
            
            # Если жанров нет в базе, возвращаем стандартный список
            return genres if genres else [
                "Классика", "Фэнтези", "Роман", "Детектив", "Антиутопия",
                "Научная фантастика", "Биография", "Поэзия", "Драма", "Юмор"
            ]
        finally:
            conn.close()
