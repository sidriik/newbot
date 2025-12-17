"""
database.py - работа с каталогом книг в SQLite
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)

class BookDatabase:
    """Класс для работы с базой данных книг"""
    
    def __init__(self, db_path='telegram_books.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Создает подключение к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Создает таблицы и добавляет тестовые книги"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Таблица книг с количеством страниц
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    genre TEXT,
                    description TEXT,
                    total_pages INTEGER DEFAULT 300
                )
            ''')
            
            # Проверяем, есть ли уже книги
            cursor.execute("SELECT COUNT(*) as count FROM books")
            if cursor.fetchone()['count'] == 0:
                self._add_sample_books(conn)
            
            conn.commit()
            conn.close()
            logger.info("База данных инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
    
    def _add_sample_books(self, conn):
        """Добавляет тестовые книги в базу"""
        sample_books = [
            (1, 'Преступление и наказание', 'Фёдор Достоевский', 'Классика', 'Роман о студенте Раскольникове', 672),
            (2, 'Мастер и Маргарита', 'Михаил Булгаков', 'Классика', 'Мистический роман', 480),
            (3, '1984', 'Джордж Оруэлл', 'Антиутопия', 'Роман о тоталитарном обществе', 328),
            (4, 'Гарри Поттер и философский камень', 'Джоан Роулинг', 'Фэнтези', 'Первая книга о юном волшебнике', 432),
            (5, 'Война и мир', 'Лев Толстой', 'Классика', 'Эпопея о войне 1812 года', 1225),
            (6, 'Маленький принц', 'Антуан де Сент-Экзюпери', 'Сказка', 'Философская сказка', 96),
            (7, 'Три товарища', 'Эрих Мария Ремарк', 'Роман', 'История о дружбе и любви', 480),
            (8, 'Шерлок Холмс', 'Артур Конан Дойл', 'Детектив', 'Рассказы о знаменитом сыщике', 320),
            (9, 'Алхимик', 'Пауло Коэльо', 'Роман', 'Притча о поиске своего предназначения', 208),
            (10, 'Гордость и предубеждение', 'Джейн Остин', 'Роман', 'История любви Элизабет Беннет', 432),
            (11, 'Убить пересмешника', 'Харпер Ли', 'Роман', 'История о расовой несправедливости', 376),
            (12, 'Властелин колец', 'Дж. Р. Р. Толкин', 'Фэнтези', 'Эпопея о Средиземье', 1137),
            (13, 'Над пропастью во ржи', 'Джером Сэлинджер', 'Роман', 'История подростка Холдена Колфилда', 277),
            (14, 'Анна Каренина', 'Лев Толстой', 'Классика', 'Роман о любви и обществе', 864),
            (15, 'Сто лет одиночества', 'Габриэль Гарсиа Маркес', 'Роман', 'История семьи Буэндиа', 448),
        ]
        
        cursor = conn.cursor()
        for book in sample_books:
            cursor.execute('''
                INSERT OR IGNORE INTO books (id, title, author, genre, description, total_pages)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', book)
        
        logger.info(f"Добавлено {len(sample_books)} тестовых книг")
    
    def search_books(self, query, limit=15):
        """Ищет книги по названию или автору"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            search_term = f"%{query}%"
            cursor.execute('''
                SELECT id, title, author, genre, description, total_pages
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
                    'description': row['description'],
                    'total_pages': row['total_pages']
                })
            
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return []
    
    def get_book(self, book_id):
        """Получает книгу по ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return {
                    'id': row['id'],
                    'title': row['title'],
                    'author': row['author'],
                    'genre': row['genre'],
                    'description': row['description'],
                    'total_pages': row['total_pages']
                }
            return None
        except Exception as e:
            logger.error(f"Ошибка получения книги: {e}")
            return None
    
    def get_all_books(self):
        """Получает все книги"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, title, author, total_pages FROM books ORDER BY title')
            results = [dict(row) for row in cursor]
            
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Ошибка получения всех книг: {e}")
            return []

# Создаем глобальный экземпляр базы данных
db = BookDatabase()
