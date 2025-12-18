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

    def get_top_books(self, criteria="rating", genre="", author="", title="", limit=5):
        """
        Получает топ книг по рейтингу или популярности с возможностью фильтрации.

        Args:
            criteria: Критерий сортировки ('rating' или любое другое для популярности)
            genre: Фильтр по жанру
            author: Фильтр по автору (поиск по подстроке)
            title: Фильтр по названию (поиск по подстроке) - НОВЫЙ ПАРАМЕТР
            limit: Максимальное количество результатов

        Returns:
            List[Book]: Список книг из топа
        """
        try:
            data = self.db.get_top_books(criteria, genre, author, title, limit)
            return [Book(item) for item in data]
        except Exception as e:
            print(f"Ошибка получения топ книг: {e}")
            return []

    def get_all_genres(self):
        """
        Получает список всех уникальных жанров из базы данных.

        Returns:
            List[str]: Список жанров
        """
        try:
            return self.db.get_all_genres()
        except Exception as e:
            print(f"Ошибка получения жанров: {e}")
            return []

    def count_books(self):
        """
        Подсчитывает общее количество книг в базе данных.

        Returns:
            int: Количество книг
        """
        try:
            books = self.search_books("", "", 1000)
            return len(books)
        except Exception as e:
            print(f"Ошибка подсчета книг: {e}")
            return 0

    def add_book_to_catalog(self, title, author, pages, genre, description=""):
        """
        Добавляет новую книгу в общий каталог.

        Args:
            title: Название книги
            author: Автор книги
            pages: Количество страниц
            genre: Жанр книги
            description: Описание книги (опционально)

        Returns:
            tuple: (success, book_id, message)
                - success: True/False - успешно ли добавлена книга
                - book_id: int - ID книги если успешно, или ID существующей если дубликат
                - message: str - Сообщение для пользователя
        """
        try:
            # Проверяем, есть ли уже такая книга в базе
            # Используем существующий метод search_books с небольшим хаком
            existing_books = self.search_books(query=title, limit=1)
            
            # Более точная проверка: ищем точное совпадение названия и автора
            for book in existing_books:
                if book.title.lower() == title.lower() and book.author.lower() == author.lower():
                    return False, book.id, "Книга уже есть в каталоге"
            
            # Если книга не найдена, добавляем её через прямое обращение к БД
            conn = self.db.get_connection()
            cur = conn.cursor()
            
            try:
                cur.execute('''
                    INSERT INTO books (title, author, total_pages, genre, description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, author, pages, genre, description))
                
                new_id = cur.lastrowid
                conn.commit()
                
                return True, new_id, "Книга успешно добавлена в каталог"
                
            except Exception as e:
                conn.rollback()
                if "UNIQUE" in str(e) or "unique" in str(e).lower():
                    # Если вдруг книга добавилась параллельно
                    cur.execute('''
                        SELECT id FROM books 
                        WHERE LOWER(title) = LOWER(?) AND LOWER(author) = LOWER(?)
                    ''', (title, author))
                    row = cur.fetchone()
                    if row:
                        return False, row['id'], "Книга уже есть в каталоге"
                return False, None, f"Ошибка при добавлении книги: {str(e)}"
            finally:
                conn.close()
                
        except Exception as e:
            return False, None, f"Ошибка базы данных: {str(e)}"
