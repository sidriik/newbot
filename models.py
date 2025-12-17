class Book:
    def __init__(self, data):
        self.id = data.get('id')
        self.title = data.get('title', 'Без названия')
        self.author = data.get('author', 'Неизвестный автор')
        self.total_pages = data.get('total_pages', 0)
        self.genre = data.get('genre', 'Не указан')
        self.description = data.get('description', '')
    
    def get_info(self):
        info = f"📖 {self.title}\n"
        info += f"👤 Автор: {self.author}\n"
        info += f"📂 Жанр: {self.genre}\n"
        info += f"📄 Страниц: {self.total_pages}"
        if self.description:
            info += f"\n📝 {self.description[:60]}..."
        return info
    
    def get_short(self):
        return f"{self.title[:20]}..." if len(self.title) > 20 else self.title


class UserBook:
    def __init__(self, data):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.book_id = data.get('book_id')
        self.status = data.get('status', 'planned')
        self.current_page = data.get('current_page', 0)
        self.rating = data.get('rating')
        
        # Из JOIN
        self.title = data.get('title', '')
        self.author = data.get('author', '')
        self.total_pages = data.get('total_pages', 0)
        self.genre = data.get('genre', '')
    
    def get_progress(self):
        if self.total_pages > 0 and self.current_page > 0:
            percent = (self.current_page / self.total_pages) * 100
            return min(100, percent)
        return 0
    
    def get_info(self):
        status_names = {
            'planned': '📅 Запланировано',
            'reading': '📖 Читаю сейчас',
            'completed': '✅ Прочитано',
            'dropped': '❌ Брошено'
        }
        
        info = f"📖 {self.title}\n"
        info += f"👤 {self.author}\n"
        info += f"📂 Статус: {status_names.get(self.status, self.status)}\n"
        
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
        data = self.db.get_book(book_id)
        return Book(data) if data else None
    
    def search_books(self, query="", genre="", limit=10):
        data = self.db.search_books(query, genre, limit)
        return [Book(item) for item in data]
    
    def get_top_books(self, criteria="rating", genre="", author="", limit=5):
        data = self.db.get_top_books(criteria, genre, author, limit)
        return [Book(item) for item in data]
    
    def get_all_genres(self):
        return self.db.get_all_genres()


class UserManager:
    def __init__(self, db):
        self.db = db
    
    def get_or_create_user(self, telegram_id, username="", first_name="", last_name=""):
        return self.db.get_or_create_user(telegram_id, username, first_name, last_name)
    
    def add_book(self, user_id, book_id, status="planned"):
        return self.db.add_user_book(user_id, book_id, status)
    
    def remove_book(self, user_id, book_id):
        return self.db.remove_user_book(user_id, book_id)
    
    def update_book_status(self, user_id, book_id, status, current_page=0):
        return self.db.update_book_status(user_id, book_id, status, current_page)
    
    def rate_book(self, user_id, book_id, rating):
        return self.db.rate_book(user_id, book_id, rating)
    
    def get_user_books(self, user_id, status=None):
        data = self.db.get_user_books(user_id, status)
        return [UserBook(item) for item in data]
    
    def get_book_info(self, user_id, book_id):
        books = self.get_user_books(user_id)
        for book in books:
            if book.book_id == book_id:
                return book
        return None
    
    def has_book(self, user_id, book_id):
        return self.get_book_info(user_id, book_id) is not None
    
    def update_progress(self, user_id, book_id, current_page):
        return self.update_book_status(user_id, book_id, 'reading', current_page)
    
    def get_stats(self, user_id):
        return self.db.get_user_stats(user_id)
