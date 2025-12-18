class Book:
    """
    Класс для представления книги в библиотеке.

    Attributes:
        id: Уникальный идентификатор книги
        title: Название книги
        author: Автор книги
        total_pages: Общее количество страниц
        genre: Жанр книги
        description: Описание книги
    """
    def __init__(self, data):
        """
        Инициализирует объект книги.
        Args:
            data: Словарь с данными книги, содержащий ключи:
            - id: Уникальный идентификатор (опционально)
            - title: Название книги
            - author: Автор книги
            - total_pages: Количество страниц
            - genre: Жанр книги
            - description: Описание книги

        Raises:
            ValueError: Если произошла ошибка при создании объекта
        """
        try:
            self.id = data.get('id')
            self.title = data.get('title', 'Без названия')
            self.author = data.get('author', 'Неизвестный автор')
            self.total_pages = data.get('total_pages', 0)
            self.genre = data.get('genre', 'Не указан')
            self.description = data.get('description', '')
        except Exception as e:
            raise ValueError(f"Ошибка создания книги: {e}")

    def get_info(self):
        """
        Возвращает форматированную информацию о книге.

        Returns:
            str: Строка с информацией о книге в формате:
                📖 Название
                👤 Автор: Имя автора
                📂 Жанр: Название жанра
                📄 Страниц: количество
                📝 Краткое описание (если есть)
        """
        info = f"📖 {self.title}\n"
        info += f"👤 Автор: {self.author}\n"
        info += f"📂 Жанр: {self.genre}\n"
        info += f"📄 Страниц: {self.total_pages}"
        if self.description:
            info += f"\n📝 {self.description[:60]}..."
        return info

    def get_short(self):
        """
        Возвращает сокращенное название книги.

        Returns:
            str: Сокращенное название (первые 20 символов с ...),
                если название длиннее 20 символов, иначе полное название
        """
        if len(self.title) > 20:
            short_title = self.title[:20]
            return f"{short_title}..."
        return self.title

    def get_full_description(self):
        """
        Возвращает полное описание книги.

        Returns:
            str: Полное описание книги или сообщение об отсутствии описания
        """
        if self.description:
            return self.description
        return "Описание отсутствует"


class UserBook:
    """
    Класс для представления книги пользователя с прогрессом чтения.

    Attributes:
        id: Уникальный идентификатор записи
        user_id: Идентификатор пользователя
        book_id: Идентификатор книги
        status: Статус чтения ('planned', 'reading', 'completed', 'dropped')
        current_page: Текущая страница чтения
        rating: Оценка пользователя (1-5)
        title: Название книги
        author: Автор книги
        total_pages: Общее количество страниц
        genre: Жанр книги
    """
    def __init__(self, data):
        """
        Инициализирует объект книги пользователя.

        Args:
            data: Словарь с данными книги пользователя

        Raises:
            ValueError: Если произошла ошибка при создании объекта
        """
        try:
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
        except Exception as e:
            raise ValueError(f"Ошибка создания UserBook: {e}")

    def get_progress(self):
        """
        Рассчитывает процент прочтения книги.

        Returns:
            float: Процент прочтения от 0 до 100

        Raises:
            ZeroDivisionError: Если total_pages равно 0
        """
        try:
            if self.total_pages > 0 and self.current_page > 0:
                percent = (self.current_page / self.total_pages) * 100
                return min(100, percent)
            return 0
        except Exception:
            return 0

    def get_info(self):
        """
        Возвращает информацию о книге пользователя.

        Returns:
            str: Форматированная строка с информацией о статусе,
                         прогрессе и оценке книги
        """
        try:
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
        except Exception as e:
            return f"Ошибка получения информации: {e}"

    def is_completed(self):
        """
        Проверяет, завершено ли чтение книги.

        Returns:
            bool: True если статус 'completed', иначе False
        """
        return self.status == 'completed'


class BookManager:
    """
    Менеджер для работы с книгами в библиотеке.
    """
    def __init__(self, db):
        """
        Инициализирует менеджер книг.

        Args:
            db: Объект базы данных для работы с книгами

        Raises:
            ValueError: Если произошла ошибка инициализации
        """
        try:
            self.db = db
        except Exception as e:
            raise ValueError(f"Ошибка инициализации BookManager: {e}")

    def get_book(self, book_id):
        """
        Получает книгу по идентификатору.

        Args:
            book_id: Идентификатор книги

        Returns:
            Optional[Book]: Объект книги или None если не найдена
        """
        try:
            data = self.db.get_book(book_id)
            return Book(data) if data else None
        except Exception as e:
            print(f"Ошибка получения книги: {e}")
            return None

    def search_books(self, query="", genre="", limit=10):
        """
        Ищет книги по запросу и жанру.

        Args:
            query: Текст для поиска в названии и авторе
            genre: Жанр для фильтрации
            limit: Максимальное количество результатов

        Returns:
            List[Book]: Список найденных книг
        """
        try:
            data = self.db.search_books(query, genre, limit)
            return [Book(item) for item in data]
        except Exception as e:
            print(f"Ошибка поиска книг: {e}")
            return []

    def get_top_books(self, criteria="rating", genre="", author="", limit=5):

        try:
            data = self.db.get_top_books(criteria, genre, author, limit)
            return [Book(item) for item in data]
        except Exception as e:
            print(f"Ошибка получения топ книг: {e}")
            return []

    def get_all_genres(self):
        try:
            return self.db.get_all_genres()
        except Exception as e:
            print(f"Ошибка получения жанров: {e}")
            return []

    def count_books(self):
        try:
            books = self.search_books("", "", 1000)
            return len(books)
        except Exception as e:
            print(f"Ошибка подсчета книг: {e}")
            return 0


class UserManager:
    """
    Менеджер для работы с пользователями и их книгами.
    """
    def __init__(self, db):
        """
        Инициализирует менеджер пользователей.

        Args:
            db: Объект базы данных для работы с пользователями

        Raises:
            ValueError: Если произошла ошибка инициализации
        """
        try:
            self.db = db
        except Exception as e:
            raise ValueError(f"Ошибка инициализации UserManager: {e}")

    def get_or_create_user(self, telegram_id, username="", first_name="", last_name=""):

        try:
            return self.db.get_or_create_user(telegram_id, username, first_name, last_name)
        except Exception as e:
            print(f"Ошибка создания пользователя: {e}")
            return None

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
                print("Ошибка: рейтинг должен быть от 1 до 5")
                return False
            return self.db.rate_book(user_id, book_id, rating)
        except Exception as e:
            print(f"Ошибка оценки книги: {e}")
            return False

    def get_user_books(self, user_id, status=None):
        try:
            data = self.db.get_user_books(user_id, status)
            return [UserBook(item) for item in data]
        except Exception as e:
            print(f"Ошибка получения книг пользователя: {e}")
            return []

    def get_book_info(self, user_id, book_id):
        try:
            books = self.get_user_books(user_id)
            for book in books:
                if book.book_id == book_id:
                    return book
            return None
        except Exception as e:
            print(f"Ошибка получения информации о книге: {e}")
            return None

    def has_book(self, user_id, book_id):
        try:
            return self.get_book_info(user_id, book_id) is not None
        except Exception as e:
            print(f"Ошибка проверки наличия книги: {e}")
            return False

    def update_progress(self, user_id, book_id, current_page):
        try:
            return self.update_book_status(user_id, book_id, 'reading', current_page)
        except Exception as e:
            print(f"Ошибка обновления прогресса: {e}")
            return False

    def get_stats(self, user_id):
        try:
            return self.db.get_user_stats(user_id)
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return {}

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
            return [book for book in books if book.is_completed()]
        except Exception as e:
            print(f"Ошибка получения завершенных книг: {e}")
            return []
