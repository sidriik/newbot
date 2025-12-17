import sqlite3
import logging

logger = logging.getLogger(__name__)

class BookDatabase:
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
            row = cursor.fetchone()
            book_count = row['count'] if row else 0
            
            if book_count == 0:
                self._add_sample_books(conn)
                print("[INFO] Добавлены тестовые книги в базу данных")
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[ERROR] Ошибка инициализации БД: {e}")
    
    def _add_sample_books(self, conn):
        """Добавляет тестовые книги"""
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
        ]
        
        cursor = conn.cursor()
        for book in sample_books:
            cursor.execute('''
                INSERT OR IGNORE INTO books (id, title, author, genre, description, total_pages)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', book)
    
    def search_books(self, query, limit=15):
        """Ищет книги"""
        try:
            search_term = f"%{query}%"
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
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
                
                return results
        except Exception as e:
            print(f"[ERROR] Ошибка поиска: {e}")
            return []
    
    def get_book(self, book_id):
        """Получает книгу по ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
                row = cursor.fetchone()
                
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
            print(f"[ERROR] Ошибка получения книги: {e}")
            return None

# Создаем глобальный экземпляр базы данных
db = BookDatabase()
