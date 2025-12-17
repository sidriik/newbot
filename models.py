from database import Database

class Book:
    def __init__(self, data):
        self.id = data.get('id')
        self.title = data.get('title', 'Без названия')
        self.author = data.get('author', 'Неизвестный автор')
        self.total_pages = data.get('total_pages', 0)
        self.genre = data.get('genre', 'Не указан')

    def get_info(self):
        info = f"📖 {self.title}\n"
        info += f"👤 Автор: {self.author}\n"
        info += f"📂 Жанр: {self.genre}\n"
        info += f"📄 Страниц: {self.total_pages}"
        return info

class UserBook:
    def __init__(self, data):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.book_id = data.get('book_id')
        self.status = data.get('status', 'planned')
        self.current_page = data.get('current_page', 0)
        self.rating = data.get('rating')
        self.title = data.get('title', '')
        self.author = data.get('author', '')
        self.total_pages = data.get('total_pages', 0)

    def get_progress(self):
        if self.total_pages > 0 and self.current_page > 0:
            return (self.current_page / self.total_pages) * 100
        return 0

    def get_info(self):
        info = f"📖 {self.title}\n"
        info += f"👤 {self.author}\n"
        
        status_text = {
            'planned': '📅 Запланировано',
            'reading': '📖 Читаю сейчас',
            'completed': '✅ Прочитано',
            'dropped': '❌ Брошено'
        }
        info += f"📂 Статус: {status_text.get(self.status, self.status)}\n"
        
        if self.status == 'reading' and self.current_page > 0:
            progress = self.get_progress()
            info += f"📊 Прогресс: стр. {self.current_page}/{self.total_pages} ({progress:.1f}%)\n"
        
        if self.rating:
            stars = "⭐" * self.rating
            info += f"⭐ Ваша оценка: {stars}"
        
        return info

class BookManager:
    def __init__(self, db):
        self.db = db

    def get_book(self, book_id):
        try:
            book_data = self.db.get_book(book_id)
            return Book(book_data) if book_data else None
        except Exception as e:
            print(f"Ошибка получения книги: {e}")
            return None

    def search_books(self, query=""):
        try:
            books_data = self.db.search_books(query)
            return [Book(book) for book in books_data]
        except Exception as e:
            print(f"Ошибка поиска книг: {e}")
            return []

class UserManager:
    def __init__(self, db):
        self.db = db

    def get_or_create_user(self, telegram_id, username=None):
        try:
            return self.db.get_or_create_user(telegram_id, username)
        except Exception as e:
            print(f"Ошибка создания пользователя: {e}")
            return 0

    def add_book(self, user_id, book_id, status="planned"):
        try:
            return self.db.add_user_book(user_id, book_id, status)
        except Exception as e:
            print(f"Ошибка добавления книги: {e}")
            return False

    def remove_book(self, user_id, book_id):
        try:
            return self.db.remove_user_book(user_id, book_id)
        except Exception as e:
            print(f"Ошибка удаления книги: {e}")
            return False

    def update_status(self, user_id, book_id, status, page=0):
        try:
            return self.db.update_book_status(user_id, book_id, status, page)
        except Exception as e:
            print(f"Ошибка обновления статуса: {e}")
            return False

    def get_books(self, user_id, status=None):
        try:
            books_data = self.db.get_user_books(user_id, status)
            return [UserBook(book) for book in books_data]
        except Exception as e:
            print(f"Ошибка получения книг: {e}")
            return []

    def get_stats(self, user_id):
        try:
            books = self.get_books(user_id)
            stats = {
                'total': len(books),
                'reading': 0,
                'completed': 0,
                'planned': 0
            }
            for book in books:
                if book.status == 'reading':
                    stats['reading'] += 1
                elif book.status == 'completed':
                    stats['completed'] += 1
                elif book.status == 'planned':
                    stats['planned'] += 1
            
            return stats
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return {'total': 0, 'reading': 0, 'completed': 0, 'planned': 0}
