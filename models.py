#!/usr/bin/env python3
"""
models.py - Модели данных и менеджеры для BookBot

Этот модуль содержит классы для управления пользователями и книгами,
а также модели данных для работы приложения.
"""

import logging
from typing import List, Dict, Any, Optional
from database import Database, DatabaseError


class Book:
    """Класс, представляющий книгу."""
    
    def __init__(self, data: Dict[str, Any]):
        """
        Инициализация книги.
        
        Args:
            data (Dict[str, Any]): Данные книги из базы данных
        """
        self.id = data.get('id')
        self.title = data.get('title', '')
        self.author = data.get('author', '')
        self.total_pages = data.get('total_pages', 0)
        self.genre = data.get('genre', '')
        self.description = data.get('description', '')
        self.added_count = data.get('added_count', 0)
        self.current_readers = data.get('current_readers', 0)
        self.statistics = data.get('statistics', {})
    
    def __str__(self) -> str:
        """Строковое представление книги."""
        return f"Книга #{self.id}: {self.title} - {self.author}"
    
    def get_formatted_info(self, include_stats: bool = True) -> str:
        """
        Получить форматированную информацию о книге.
        
        Args:
            include_stats (bool): Включать ли статистику
            
        Returns:
            str: Форматированная строка с информацией
        """
        info = [
            f"📖 {self.title}",
            f"👤 {self.author}",
            f"📂 {self.genre if self.genre else 'Не указан'}",
            f"📄 Страниц: {self.total_pages}"
        ]
        
        if self.description:
            info.append(f"📝 {self.description[:100]}...")
        
        if include_stats and self.statistics:
            stats_info = [
                f"⭐ Рейтинг: {self.statistics.get('avg_rating', 0)}/5 "
                f"({self.statistics.get('rating_count', 0)} оценок)",
                f"👥 Всего добавили: {self.statistics.get('total_added', 0)} чел.",
                f"📖 Читают сейчас: {self.statistics.get('currently_reading', 0)} чел."
            ]
            info.extend(stats_info)
        
        return "\n".join(info)
    
    def get_short_info(self) -> str:
        """Краткая информация о книге."""
        return f"{self.title[:20]}... - {self.author[:15]}..."


class UserBook:
    """Класс, представляющий книгу пользователя."""
    
    def __init__(self, data: Dict[str, Any]):
        """
        Инициализация книги пользователя.
        
        Args:
            data (Dict[str, Any]): Данные из базы данных
        """
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.book_id = data.get('book_id')
        self.status = data.get('status', 'planned')
        self.current_page = data.get('current_page', 0)
        self.rating = data.get('rating')
        self.added_at = data.get('added_at')
        
        # Дополнительные поля из JOIN
        self.title = data.get('title', '')
        self.author = data.get('author', '')
        self.genre = data.get('genre', '')
        self.total_pages = data.get('total_pages', 0)
    
    def __str__(self) -> str:
        """Строковое представление."""
        return f"Книга пользователя #{self.id}: {self.title}"
    
    def get_progress_percentage(self) -> float:
        """Получить процент прочтения."""
        if self.total_pages > 0 and self.current_page > 0:
            return (self.current_page / self.total_pages) * 100
        return 0.0
    
    def get_formatted_info(self) -> str:
        """Форматированная информация о книге пользователя."""
        status_map = {
            'planned': '📅 Запланировано',
            'reading': '📖 Читаю сейчас',
            'completed': '✅ Прочитано',
            'dropped': '❌ Брошено'
        }
        
        info = [
            f"📖 {self.title}",
            f"👤 {self.author}",
            f"📂 Статус: {status_map.get(self.status, self.status)}"
        ]
        
        if self.status == 'reading' and self.current_page > 0:
            progress = self.get_progress_percentage()
            info.append(f"📊 Прогресс: стр. {self.current_page}/{self.total_pages} ({progress:.1f}%)")
        
        if self.rating:
            stars = "⭐" * self.rating
            info.append(f"⭐ Оценка: {stars} ({self.rating}/5)")
        
        return "\n".join(info)


class UserManager:
    """Менеджер для работы с пользователями и их книгами."""
    
    def __init__(self, database: Database):
        """
        Инициализация менеджера пользователей.
        
        Args:
            database (Database): Экземпляр базы данных
        """
        self.db = database
        self.logger = logging.getLogger(__name__)
    
    def get_or_create_user(self, telegram_id: int, **kwargs) -> int:
        """
        Получить или создать пользователя.
        
        Args:
            telegram_id (int): Telegram ID пользователя
            **kwargs: Дополнительные данные пользователя
            
        Returns:
            int: ID пользователя в базе данных
            
        Raises:
            UserManagerError: Если произошла ошибка
        """
        try:
            return self.db.get_or_create_user(telegram_id, **kwargs)
        except DatabaseError as e:
            self.logger.error(f"Ошибка при получении/создании пользователя: {e}")
            raise UserManagerError(f"Ошибка работы с пользователем: {e}")
    
    def add_book(self, user_id: int, book_id: int, status: str = "planned") -> bool:
        """
        Добавить книгу пользователю.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            status (str): Статус книги
            
        Returns:
            bool: True если успешно
            
        Raises:
            UserManagerError: Если произошла ошибка
        """
        try:
            return self.db.add_user_book(user_id, book_id, status)
        except DatabaseError as e:
            self.logger.error(f"Ошибка при добавлении книги: {e}")
            raise UserManagerError(f"Ошибка при добавлении книги: {e}")
    
    def remove_book(self, user_id: int, book_id: int) -> bool:
        """
        Удалить книгу у пользователя.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            
        Returns:
            bool: True если успешно
            
        Raises:
            UserManagerError: Если произошла ошибка
        """
        try:
            return self.db.remove_user_book(user_id, book_id)
        except DatabaseError as e:
            self.logger.error(f"Ошибка при удалении книги: {e}")
            raise UserManagerError(f"Ошибка при удалении книги: {e}")
    
    def update_book_status(self, user_id: int, book_id: int, 
                          status: str, current_page: int = 0) -> bool:
        """
        Обновить статус книги.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            status (str): Новый статус
            current_page (int): Текущая страница
            
        Returns:
            bool: True если успешно
            
        Raises:
            UserManagerError: Если произошла ошибка
        """
        try:
            return self.db.update_book_status(user_id, book_id, status, current_page)
        except DatabaseError as e:
            self.logger.error(f"Ошибка при обновлении статуса: {e}")
            raise UserManagerError(f"Ошибка при обновлении статуса: {e}")
    
    def rate_book(self, user_id: int, book_id: int, rating: int) -> bool:
        """
        Оценить книгу.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            rating (int): Оценка от 1 до 5
            
        Returns:
            bool: True если успешно
            
        Raises:
            UserManagerError: Если произошла ошибка
            ValueError: Если оценка неверная
        """
        try:
            return self.db.rate_book(user_id, book_id, rating)
        except DatabaseError as e:
            self.logger.error(f"Ошибка при оценке книги: {e}")
            raise UserManagerError(f"Ошибка при оценке книги: {e}")
        except ValueError as e:
            self.logger.error(f"Неверная оценка: {e}")
            raise
    
    def get_user_books(self, user_id: int, status: str = None) -> List[UserBook]:
        """
        Получить книги пользователя.
        
        Args:
            user_id (int): ID пользователя
            status (str, optional): Статус для фильтрации
            
        Returns:
            List[UserBook]: Список книг пользователя
            
        Raises:
            UserManagerError: Если произошла ошибка
        """
        try:
            books_data = self.db.get_user_books(user_id, status)
            return [UserBook(book) for book in books_data]
        except DatabaseError as e:
            self.logger.error(f"Ошибка при получении книг пользователя: {e}")
            raise UserManagerError(f"Ошибка при получении книг пользователя: {e}")
    
    def get_book_info(self, user_id: int, book_id: int) -> Optional[UserBook]:
        """
        Получить информацию о конкретной книге пользователя.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            
        Returns:
            Optional[UserBook]: Книга пользователя или None
            
        Raises:
            UserManagerError: Если произошла ошибка
        """
        try:
            books = self.db.get_user_books(user_id)
            for book_data in books:
                if book_data['book_id'] == book_id:
                    return UserBook(book_data)
            return None
        except DatabaseError as e:
            self.logger.error(f"Ошибка при получении информации о книге: {e}")
            raise UserManagerError(f"Ошибка при получении информации о книге: {e}")
    
    def has_book(self, user_id: int, book_id: int) -> bool:
        """
        Проверить, есть ли книга у пользователя.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            
        Returns:
            bool: True если есть
            
        Raises:
            UserManagerError: Если произошла ошибка
        """
        return self.get_book_info(user_id, book_id) is not None
    
    def update_progress(self, user_id: int, book_id: int, current_page: int) -> bool:
        """
        Обновить прогресс чтения.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            current_page (int): Номер текущей страницы
            
        Returns:
            bool: True если успешно
            
        Raises:
            UserManagerError: Если произошла ошибка
        """
        return self.update_book_status(user_id, book_id, 'reading', current_page)
    
    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получить статистику пользователя.
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            Dict[str, Any]: Статистика пользователя
            
        Raises:
            UserManagerError: Если произошла ошибка
        """
        try:
            return self.db.get_user_stats(user_id)
        except DatabaseError as e:
            self.logger.error(f"Ошибка при получении статистики: {e}")
            raise UserManagerError(f"Ошибка при получении статистики: {e}")


class BookManager:
    """Менеджер для работы с книгами."""
    
    def __init__(self, database: Database):
        """
        Инициализация менеджера книг.
        
        Args:
            database (Database): Экземпляр базы данных
        """
        self.db = database
        self.logger = logging.getLogger(__name__)
    
    def get_book(self, book_id: int) -> Optional[Book]:
        """
        Получить книгу по ID.
        
        Args:
            book_id (int): ID книги
            
        Returns:
            Optional[Book]: Книга или None
            
        Raises:
            BookManagerError: Если произошла ошибка
        """
        try:
            book_data = self.db.get_book(book_id)
            return Book(book_data) if book_data else None
        except DatabaseError as e:
            self.logger.error(f"Ошибка при получении книги: {e}")
            raise BookManagerError(f"Ошибка при получении книги: {e}")
    
    def search_books(self, query: str = "", genre: str = "", limit: int = 10) -> List[Book]:
        """
        Поиск книг.
        
        Args:
            query (str): Поисковый запрос
            genre (str): Жанр для фильтрации
            limit (int): Максимальное количество результатов
            
        Returns:
            List[Book]: Список найденных книг
            
        Raises:
            BookManagerError: Если произошла ошибка
        """
        try:
            books_data = self.db.search_books(query, genre, limit)
            return [Book(book) for book in books_data]
        except DatabaseError as e:
            self.logger.error(f"Ошибка при поиске книг: {e}")
            raise BookManagerError(f"Ошибка при поиске книг: {e}")
    
    def get_top_books(self, criteria: str = "rating", genre: str = "", 
                     author: str = "", limit: int = 5) -> List[Book]:
        """
        Получить топ книг.
        
        Args:
            criteria (str): Критерий сортировки
            genre (str): Жанр для фильтрации
            author (str): Автор для фильтрации
            limit (int): Максимальное количество результатов
            
        Returns:
            List[Book]: Список книг
            
        Raises:
            BookManagerError: Если произошла ошибка
        """
        try:
            books_data = self.db.get_top_books(criteria, genre, author, limit)
            return [Book(book) for book in books_data]
        except DatabaseError as e:
            self.logger.error(f"Ошибка при получении топ книг: {e}")
            raise BookManagerError(f"Ошибка при получении топ книг: {e}")
    
    def get_all_genres(self) -> List[str]:
        """
        Получить все уникальные жанры.
        
        Returns:
            List[str]: Список жанров
        """
        return ["Классика", "Фэнтези", "Роман", "Детектив", "Научная фантастика",
                "Приключения", "Ужасы", "Исторический", "Биография", "Психология",
                "Поэзия", "Драма", "Комедия", "Триллер", "Мистика", "Антиутопия",
                "Притча"]


class UserManagerError(Exception):
    """Исключение для ошибок менеджера пользователей."""
    pass


class BookManagerError(Exception):
    """Исключение для ошибок менеджера книг."""
    pass
