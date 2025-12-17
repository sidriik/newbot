class Book:
    def init(self, data):
        self.id = data.get('id')
        self.title = data.get('title', 'Без названия')
        self.author = data.get('author', 'Неизвестный автор')
        self.total_pages = data.get('total_pages', 0)
        self.genre = data.get('genre', 'Не указан')
        self.description = data.get('description', '')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'total_pages': self.total_pages,
            'genre': self.genre,
            'description': self.description
        }
    
    def is_long(self):
        return self.total_pages > 300
    
    def get_short_info(self):
        return f"{self.title} - {self.author}"


class UserBook:
    def init(self, data):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.book_id = data.get('book_id')
        self.status = data.get('status', 'planned')
        self.current_page = data.get('current_page', 0)
        self.rating = data.get('rating')
        
        self.title = data.get('title', '')
        self.author = data.get('author', '')
        self.total_pages = data.get('total_pages', 0)
        self.genre = data.get('genre', '')
    
    def get_progress(self):
        if self.total_pages > 0 and self.current_page > 0:
            return (self.current_page / self.total_pages) * 100
        return 0.0
    
    def is_finished(self):
        return self.status == 'completed'
    
    def get_status_text(self):
        status_texts = {
            'planned': 'Запланировано к прочтению',
            'reading': 'Читается сейчас',
            'completed': 'Прочитано',
            'dropped': 'Брошено'
        }
        return status_texts.get(self.status, self.status)
    
    def get_rating_stars(self):
        if self.rating:
            return '★' * self.rating + '☆' * (5 - self.rating)
        return 'Нет оценки'


class BookManagerError(Exception):
    pass


class UserManagerError(Exception):
    pass
class BookManager:
    def init(self, database):
        self.db = database
    
    def get_book(self, book_id):
        try:
            book_data = self.db.get_book(book_id)
            return Book(book_data) if book_data else None
        except Exception as e:
            print(f"Ошибка получения книги: {e}")
            return None
    
    def search_books(self, query="", limit=10):
        try:
            books_data = self.db.search_books(query, limit)
            return [Book(book) for book in books_data]
        except Exception as e:
            print(f"Ошибка поиска книг: {e}")
            return []
    
    def get_books_by_genre(self, genre):
        try:
            all_books = self.search_books("", 100)
            return [book for book in all_books if book.genre.lower() == genre.lower()]
        except Exception as e:
            print(f"Ошибка фильтрации по жанру: {e}")
            return []
    
    def count_books(self):
        try:
            books = self.search_books("", 1000)
            return len(books)
        except Exception as e:
            print(f"Ошибка подсчета книг: {e}")
            return 0
    
    def get_long_books(self):
        try:
            all_books = self.search_books("", 100)
            return [book for book in all_books if book.is_long()]
        except Exception as e:
            print(f"Ошибка получения длинных книг: {e}")
            return []
    
    def get_book_with_stats(self, book_id):
        try:
            book = self.get_book(book_id)
            if not book:
                return None, {}
            stats = self.db.get_book_statistics(book_id)
            return book, stats
        except Exception as e:
            print(f"Ошибка получения книги со статистикой: {e}")
            return None, {}
    
    def get_top_books(self, criteria="rating", genre="", author="", limit=5):
        try:
            books_data = self.db.get_top_books(criteria, genre, author, limit)
            return [Book(book) for book in books_data]
        except Exception as e:
            print(f"Ошибка получения топ книг: {e}")
            return []
    
    def get_all_genres(self):
        try:
            return self.db.get_all_genres()
        except:
            return ["Классика", "Фэнтези", "Роман", "Детектив", "Антиутопия"]
    
