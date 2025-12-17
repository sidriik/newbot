from database import Database, DatabaseError

class Book:

    def __init__(self, data):
        self.id = data.get('id')
        self.title = data.get('title', 'Без названия')
        self.author = data.get('author', 'Неизвестный автор')
        self.total_pages = data.get('total_pages', 0)
        self.genre = data.get('genre', 'Не указан')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'total_pages': self.total_pages,
            'genre': self.genre
        }

    def is_long(self):
        return self.total_pages > 300

    def get_short_info(self):
        return self.title + " - " + self.author


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

class BookManager:

    def __init__(self, database):
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


class UserManager:

    def __init__(self, database):
        self.db = database

    def get_or_create_user(self, telegram_id):
        try:
            return self.db.get_or_create_user(telegram_id)
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

    def update_book_status(self, user_id, book_id, status, current_page=0):
        try:
            return self.db.update_book_status(user_id, book_id, status, current_page)
        except Exception as e:
            print(f"Ошибка обновления статуса: {e}")
            return False

    def rate_book(self, user_id, book_id, rating):
        try:
            if rating < 1 or rating > 5:
                raise ValueError("Оценка должна быть от 1 до 5")
            return self.db.rate_book(user_id, book_id, rating)
        except Exception as e:
            print(f"Ошибка оценки книги: {e}")
            return False

    def get_user_books(self, user_id, status=None):
        try:
            books_data = self.db.get_user_books(user_id, status)
            return [UserBook(book) for book in books_data]
        except Exception as e:
            print(f"Ошибка получения книг пользователя: {e}")
            return []

    def has_book(self, user_id, book_id):
        try:
            books = self.get_user_books(user_id)
            for book in books:
                if book.book_id == book_id:
                    return True
            return False
        except Exception as e:
            print(f"Ошибка проверки наличия книги: {e}")
            return False

    def count_user_books(self, user_id):
        try:
            books = self.get_user_books(user_id)
            return len(books)
        except Exception as e:
            print(f"Ошибка подсчета книг пользователя: {e}")
            return 0

    def get_completed_books(self, user_id):
        try:
            books = self.get_user_books(user_id)
            return [book for book in books if book.status == 'completed']
        except Exception as e:
            print(f"Ошибка получения завершенных книг: {e}")
            return []
    def validate_status(self, status):
        valid_statuses = ['planned', 'reading', 'completed', 'dropped']
        return status in valid_statuses

    def get_reading_progress(self, user_id):
        try:
            books = self.get_user_books(user_id, 'reading')
            if not books:
                return 0.0

            total_progress = 0
            for book in books:
                total_progress += book.get_progress()

            return total_progress / len(books)
        except Exception as e:
            print(f"Ошибка расчета прогресса чтения: {e}")
            return 0.0
    def get_reading_progress(self, user_id):
        try:  
            books = self.get_user_books(user_id, 'reading')

