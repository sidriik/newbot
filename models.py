from database import Database

class Book:
    """
    Класс для представления книги в библиотеке.

    Attributes:
        id (int): Уникальный идентификатор книги
        title (str): Название книги
        author (str): Автор книги
        total_pages (int): Общее количество страниц
        genre (str): Жанр книги
        description (str): Описание книги
    """

    def __init__(self, data):
        """
        Инициализирует объект книги.
        """
        self.id = data.get('id')
        self.title = data.get('title', 'Без названия')
        self.author = data.get('author', 'Неизвестный автор')
        self.total_pages = data.get('total_pages', 0)
        self.genre = data.get('genre', 'Не указан')
        self.description = data.get('description', '')

    def get_info(self):
        """
        Возвращает форматированную информацию о книге.

        Returns:
            str: Строка с информацией о книге в формате:
                📖 Название: Название книги
                👤 Автор: Имя автора
                📂 Жанр: Название жанра
                📄 Страниц: количество
                📝 Краткое описание (если есть)
        """
        info = f"📖 Название: {self.title}\n"
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
            str: Сокращенное название (первые 15 символов)
            или пустую строку в случае ошибки
        """
        try:
            return self.title[:15] + "..." if len(self.title) > 15 else self.title
        except Exception as e:
            return ""


class UserBook:
    """
    Класс для представления книги пользователя с прогрессом чтения.

     Attributes:
        id (int): Уникальный идентификатор записи
        user_id (int): Идентификатор пользователя
        book_id (int): Идентификатор книги
        status (str): Статус чтения ('planned', 'reading', 'completed', 'dropped')
        current_page (int): Текущая страница чтения
        rating (Optional[int]): Оценка пользователя (1-5) или None
        title (str): Название книги
        author (str): Автор книги
        total_pages (int): Общее количество страниц
        genre (str): Жанр книги
    """

    def __init__(self, data):
        """
        Инициализирует объект книги пользователя.
        """
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
        """
        Рассчитывает процент прочтения книги.

        Returns:
            float: Процент прочтения от 0.0 до 100.0.
            Всегда возвращает 0.0 при некорректных входных данных или ошибках.
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
            str: Форматированная строка с информацией о статусе, прогрессе и оценке книги
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

    def get_short(self):
        """
        Возвращает сокращенное название книги.

        Returns:
            str: Сокращенное название (первые 15 символов)
            или пустую строку в случае ошибки
        """
        try:
            return self.title[:15] + "..." if len(self.title) > 15 else self.title
        except Exception:
            return ""

    def is_completed(self) -> bool:
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
        """
        self.db = db

    def get_books(self, book_id):
        """
        Получает книгу по идентификатору.

        Args:
            book_id: Идентификатор книги

        Returns:
            Optional[Book]: Объект книги или None если книга не найдена
        """
        try:
            data = self.db.get_book(book_id)
            return Book(data) if data else None
        except Exception as e:
            print(f"Ошибка получения книги: {e}")
            return None

    def search_book(self, query="", genre="", limit=10):
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

    def get_top_book(self, criteria="rating", genre="", author="", limit=5):
        """
        Получает список лучших книг по заданным критериям.

        Args:
            criteria: Критерий сортировки
            genre: Фильтр по жанру книги (если пустая строка - все жанры)
            author: Фильтр по автору (если пустая строка - все авторы)
            limit: Максимальное количество возвращаемых книг

        Returns:
            List[Book]: Список объектов Book, отсортированных по указанному критерию
        """
        try:
            data = self.db.get_top_books(criteria, genre, author, limit)
            return [Book(item) for item in data]
        except Exception as e:
            print(f"Ошибка получения топ книг: {e}")
            return []

    def get_all_genre(self):
        """
        Получает список всех доступных жанров книг в библиотеке.

        Returns:
            List[str]: Список уникальных жанров книг
        """
        return self.db.get_all_genres()


class UserManager:
    """
    Менеджер для работы с пользователями и их книгами.
    """

    def __init__(self, db):
        """
        Инициализирует менеджер пользователей.
        """
        self.db = db

    def get_or_create_users(self, telegram_id, username="", first_name="", last_name=""):
        """
        Получает существующего пользователя или создает нового.

        Args:
            telegram_id: Уникальный идентификатор пользователя в Telegram
            username: Имя пользователя в Telegram (опционально)
            first_name: Имя пользователя (опционально)
            last_name: Фамилия пользователя (опционально)

        Returns:
            int: Идентификатор пользователя в системе (существующего или нового)
        """
        return self.db.get_or_create_user(telegram_id, username, first_name, last_name)

    def add_book(self, user_id, book_id, status="planned"):
        """
        Добавляет книгу в коллекцию пользователя.

        Args:
            user_id: Уникальный идентификатор пользователя
            book_id: Уникальный идентификатор книги
            status: Статус чтения книги: "planned", "reading", "completed", "dropped"

        Returns:
            bool: True если книга успешно добавлена, False если произошла ошибка

        Raises:
            ValueError: Если указан недопустимый статус
        """
        try:
            allowed_status = ["planned", "reading", "completed", "dropped"]
            if status not in allowed_status:
                raise ValueError
            return self.db.add_user_book(user_id, book_id, status)
        except Exception as e:
            print(f"Ошибка добавления книги: {e}")
            return False

    def remove_book(self, user_id, book_id):
        """
        Удаляет книгу из коллекции пользователя.

        Args:
            user_id: Уникальный идентификатор пользователя
            book_id: Уникальный идентификатор книги для удаления

        Returns:
            bool: True если книга успешно удалена, False если произошла ошибка
        """
        try:
            return self.db.remove_user_book(user_id, book_id)
        except Exception as e:
            print(f"Ошибка удаления книги: {e}")
            return False

    def update_books_status(self, user_id, book_id, status, current_page=0):
        """
        Обновляет статус чтения книги пользователем.

        Args:
            user_id: Уникальный идентификатор пользователя
            book_id: Уникальный идентификатор книги
            status: Новый статус чтения: "planned", "reading", "completed", "dropped"
            current_page: Текущая страница (по умолчанию 0)

        Returns:
            bool: True если статус успешно обновлен, False если произошла ошибка

        Raises:
            ValueError: Если указан недопустимый статус
        """
        try:
            allowed_status = ["planned", "reading", "completed", "dropped"]
            if status not in allowed_status:
                raise ValueError
            if current_page < 0:
                raise ValueError
            return self.db.update_book_status(user_id, book_id, status, current_page)
        except ValueError as ve:
            print(f"Ошибка валидации: {ve}")
            return False
        except Exception as e:
            print(f"Ошибка обновления статуса: {e}")
            return False

    def update_progress(self, user_id, book_id, current_page):
        """
        Обновляет прогресс чтения книги.

        Args:
            user_id: ID пользователя
            book_id: ID книги
            current_page: Текущая страница

        Returns:
            bool: True если успешно, False при ошибке

        Raises:
            ValueError: Если current_page отрицательное
        """
        try:
            if current_page < 0:
                raise ValueError
            book = self.get_book_info(user_id, book_id)
            if not book or not book.total_pages:
                return False
            if current_page >= book.total_pages:
                status, current_page = 'completed', book.total_pages
            else:
                status = 'reading' if current_page > 0 else 'planned'
            return self.db.update_book_status(user_id, book_id, status, current_page)
        except ValueError:
            raise
        except Exception:
            return False

    def get_user_book(self, user_id, status=None):
        """
        Получает книги пользователя.

        Args:
            user_id: Идентификатор пользователя
            status: Фильтр по статусу чтения

        Returns:
            List[UserBook]: Список книг пользователя
        """
        try:
            data = self.db.get_user_books(user_id, status)
            return [UserBook(item) for item in data]
        except Exception as e:
            print(f"Ошибка получения книг пользователя: {e}")
            return []

    def get_stats(self, user_id):
        """
        Получает статистику чтения для указанного пользователя.

        Args:
            user_id: Уникальный идентификатор пользователя

        Returns:
            Dict[str, Any]: Словарь со статистическими данными пользователя или пустой словарь в случае ошибки
        """
        try:
            return self.db.get_user_stats(user_id)
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return {}

    def get_completed_books(self, user_id):
        """
        Получает список завершенных (прочитанных) книг пользователя.

        Args:
            user_id: Уникальный идентификатор пользователя

        Returns:
            List[UserBook]: Список объектов UserBook со статусом 'completed'
        """
        try:
            books = self.get_user_book(user_id)
            return [book for book in books if book.is_completed()]
        except Exception as e:
            print(f"Ошибка получения завершенных книг: {e}")
            return []

    def count_user_books(self, user_id):
        """
        Подсчитывает общее количество книг в коллекции пользователя.

        Args:
            user_id: Уникальный идентификатор пользователя

        Returns:
            int: Количество книг в коллекции пользователя или 0 при ошибке
        """
        try:
            books = self.get_user_book(user_id)
            return len(books)
        except Exception as e:
            print(f"Ошибка подсчета книг пользователя: {e}")
            return 0

    def get_book_info(self, user_id, book_id):
        """
        Получает информацию о конкретной книге пользователя.

        Args:
            user_id: Идентификатор пользователя в системе
            book_id: Идентификатор книги в каталоге

        Returns:
            Optional[UserBook]: Объект книги пользователя если найдена,
            None если книга отсутствует в коллекции пользователя
        """
        try:
            user_books = self.get_user_book(user_id)
            for book in user_books:
                if book.book_id == book_id:
                    return book
            return None
        except Exception:
            return None

    def has_book(self, user_id, book_id):
        """
        Проверяет наличие книги в коллекции пользователя.

        Args:
            user_id: Идентификатор пользователя в системе
            book_id: Идентификатор книги в каталоге

        Returns:
            bool: True если книга есть в коллекции пользователя,
                False если книги нет или произошла ошибка
        """
        try:
            return self.get_book_info(user_id, book_id) is not None
        except Exception:
            return False

    def rate_books(self, user_id, book_id, rating):
        """
        Устанавливает оценку книги пользователем.

        Args:
            user_id: Уникальный идентификатор пользователя
            book_id: Уникальный идентификатор книги
            rating: Оценка книги (целое число от 1 до 5 включительно)

        Returns:
            bool: True если оценка успешно сохранена, False в случае ошибки

        Raises:
            ValueError: Если оценка выходит за допустимый диапазон (1-5)
        """
        try:
            if rating < 1 or rating > 5:
                raise ValueError
            return self.db.rate_book(user_id, book_id, rating)
        except Exception as e:
            print(f"Ошибка оценки: {e}")
            return False


if __name__ == "__main__":
    print("✅ Библиотечный бот инициализирован")
