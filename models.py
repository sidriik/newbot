#!/usr/bin/env python3
"""
models.py - Модели данных для BookBot
"""

import logging
from typing import List, Dict, Any, Optional
from database import Database, DatabaseError


class Book:
    """Класс, представляющий книгу."""
    
    def __init__(self, data: Dict[str, Any]):
        """
        Инициализация объекта книги.
        
        Args:
            data: Словарь с данными книги из базы данных
        """
        self.id = data.get('id')
        self.title = data.get('title', 'Без названия')
        self.author = data.get('author', 'Неизвестный автор')
        self.total_pages = data.get('total_pages', 0)
        self.genre = data.get('genre', 'Не указан')
        self.description = data.get('description', '')
        self.added_count = data.get('added_count', 0)
        self.current_readers = data.get('current_readers', 0)
    
    def __str__(self) -> str:
        """
        Строковое представление книги.
        
        Returns:
            Строка с основными данными книги
        """
        return f"Книга #{self.id}: {self.title} - {self.author}"
    
    def get_formatted_info(self, include_stats: bool = False, 
                          stats_data: Dict[str, Any] = None) -> str:
        """
        Форматирует информацию о книге для отображения.
        
        Args:
            include_stats: Включать ли статистику
            stats_data: Данные статистики
            
        Returns:
            Форматированная строка с информацией
        """
        lines = [
            f"📖 {self.title}",
            f"👤 Автор: {self.author}",
            f"📂 Жанр: {self.genre}",
            f"📄 Страниц: {self.total_pages}"
        ]
        
        if self.description:
            desc = self.description[:100] + "..." if len(self.description) > 100 else self.description
            lines.append(f"📝 {desc}")
        
        if include_stats and stats_data:
            avg_rating = stats_data.get('avg_rating', 0)
            rating_count = stats_data.get('rating_count', 0)
            total_added = stats_data.get('total_added', 0)
            currently_reading = stats_data.get('currently_reading', 0)
            
            if avg_rating > 0:
                stars = "⭐" * int(round(avg_rating))
                lines.append(f"⭐ Рейтинг: {stars} ({avg_rating}/5 из {rating_count} оценок)")
            
            lines.append(f"👥 Всего добавили: {total_added} чел.")
            lines.append(f"📖 Читают сейчас: {currently_reading} чел.")
        
        return "\n".join(lines)


class UserBook:
    """Класс, представляющий книгу пользователя."""
    
    def __init__(self, data: Dict[str, Any]):
        """
        Инициализация книги пользователя.
        
        Args:
            data: Словарь с данными из базы данных
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
        """
        Строковое представление.
        
        Returns:
            Строка с информацией о книге пользователя
        """
        return f"Книга пользователя #{self.id}: {self.title}"
    
    def get_progress_percentage(self) -> float:
        """
        Рассчитывает процент прочтения книги.
        
        Returns:
            Процент прочтения (0-100)
        """
        if self.total_pages > 0 and self.current_page > 0:
            return min(100, (self.current_page / self.total_pages) * 100)
        return 0.0
    
    def get_formatted_info(self) -> str:
        """
        Форматирует информацию о книге пользователя.
        
        Returns:
            Форматированная строка
        """
        status_map = {
            'planned': '📅 Запланировано',
            'reading': '📖 Читаю сейчас',
            'completed': '✅ Прочитано',
            'dropped': '❌ Брошено'
        }
        
        lines = [
            f"📖 {self.title}",
            f"👤 {self.author}",
            f"📂 Статус: {status_map.get(self.status, self.status)}"
        ]
        
        if self.status == 'reading' and self.current_page > 0:
            progress = self.get_progress_percentage()
            lines.append(f"📊 Прогресс: стр. {self.current_page}/{self.total_pages} ({progress:.1f}%)")
        
        if self.rating:
            stars = "⭐" * self.rating
            lines.append(f"⭐ Ваша оценка: {stars} ({self.rating}/5)")
        
        return "\n".join(lines)


class BookManagerError(Exception):
    """Исключение для ошибок менеджера книг."""
    pass


class UserManagerError(Exception):
    """Исключение для ошибок менеджера пользователей."""
    pass


class BookManager:
    """Менеджер для работы с книгами."""
    
    def __init__(self, database: Database):
        """
        Инициализация менеджера книг.
        
        Args:
            database: Экземпляр базы данных
        """
        self.db = database
        self.logger = logging.getLogger(__name__)
    
    def get_book(self, book_id: int) -> Optional[Book]:
        """
        Получает книгу по ID.
        
        Args:
            book_id: ID книги
            
        Returns:
            Объект Book или None если не найдена
            
        Raises:
            BookManagerError: При ошибке базы данных
        """
        try:
            book_data = self.db.get_book(book_id)
            return Book(book_data) if book_data else None
        except DatabaseError as e:
            self.logger.error(f"Ошибка получения книги: {e}")
            raise BookManagerError(f"Ошибка получения книги: {e}")
    
    def search_books(self, query: str = "", genre: str = "", limit: int = 10) -> List[Book]:
        """
        Ищет книги по запросу.
        
        Args:
            query: Строка поиска
            genre: Жанр для фильтрации
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных книг
            
        Raises:
            BookManagerError: При ошибке поиска
        """
        try:
            books_data = self.db.search_books(query, genre, limit)
            return [Book(book) for book in books_data]
        except DatabaseError as e:
            self.logger.error(f"Ошибка поиска книг: {e}")
            raise BookManagerError(f"Ошибка поиска книг: {e}")
    
    def get_book_with_stats(self, book_id: int) -> tuple[Optional[Book], Dict[str, Any]]:
        """
        Получает книгу со статистикой.
        
        Args:
            book_id: ID книги
            
        Returns:
            Кортеж (книга, статистика)
            
        Raises:
            BookManagerError: При ошибке запроса
        """
        try:
            book = self.get_book(book_id)
            if not book:
                return None, {}
            
            stats = self.db.get_book_statistics(book_id)
            return book, stats
        except DatabaseError as e:
            self.logger.error(f"Ошибка получения книги со статистикой: {e}")
            raise BookManagerError(f"Ошибка получения книги со статистикой: {e}")
    
    def get_top_books(self, criteria: str = "rating", genre: str = "", 
                     author: str = "", limit: int = 5) -> List[Book]:
        """
        Получает топ книг.
        
        Args:
            criteria: Критерий сортировки ('rating' или 'popularity')
            genre: Жанр для фильтрации
            author: Автор для фильтрации
            limit: Количество результатов
            
        Returns:
            Список книг
            
        Raises:
            BookManagerError: При ошибке запроса
            ValueError: При неверном критерии
        """
        try:
            books_data = self.db.get_top_books(criteria, genre, author, limit)
            return [Book(book) for book in books_data]
        except DatabaseError as e:
            self.logger.error(f"Ошибка получения топ книг: {e}")
            raise BookManagerError(f"Ошибка получения топ книг: {e}")
    
    def get_all_genres(self) -> List[str]:
        """
        Получает все жанры.
        
        Returns:
            Список жанров
        """
        try:
            return self.db.get_all_genres()
        except:
            return ["Классика", "Фэнтези", "Роман", "Детектив", "Антиутопия", 
                   "Научная фантастика", "Приключения", "Ужасы", "Биография"]


class UserManager:
    """Менеджер для работы с пользователями."""
    
    def __init__(self, database: Database):
        """
        Инициализация менеджера пользователей.
        
        Args:
            database: Экземпляр базы данных
        """
        self.db = database
        self.logger = logging.getLogger(__name__)
    
    def get_or_create_user(self, telegram_id: int, **kwargs) -> int:
        """
        Получает или создает пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            **kwargs: Дополнительные данные
            
        Returns:
            ID пользователя в базе
            
        Raises:
            UserManagerError: При ошибке базы данных
        """
        try:
            return self.db.get_or_create_user(telegram_id, **kwargs)
        except DatabaseError as e:
            self.logger.error(f"Ошибка создания пользователя: {e}")
            raise UserManagerError(f"Ошибка создания пользователя: {e}")
    
    def add_book(self, user_id: int, book_id: int, status: str = "planned") -> bool:
        """
        Добавляет книгу пользователю.
        
        Args:
            user_id: ID пользователя
            book_id: ID книги
            status: Статус книги
            
        Returns:
            True если успешно
            
        Raises:
            UserManagerError: При ошибке базы данных
        """
        try:
            return self.db.add_user_book(user_id, book_id, status)
        except DatabaseError as e:
            self.logger.error(f"Ошибка добавления книги: {e}")
            raise UserManagerError(f"Ошибка добавления книги: {e}")
    
    def remove_book(self, user_id: int, book_id: int) -> bool:
        """
        Удаляет книгу у пользователя.
        
        Args:
            user_id: ID пользователя
            book_id: ID книги
            
        Returns:
            True если успешно
            
        Raises:
            UserManagerError: При ошибке базы данных
        """
        try:
            return self.db.remove_user_book(user_id, book_id)
        except DatabaseError as e:
            self.logger.error(f"Ошибка удаления книги: {e}")
            raise UserManagerError(f"Ошибка удаления книги: {e}")
    
    def update_book_status(self, user_id: int, book_id: int, 
                          status: str, current_page: int = 0) -> bool:
        """
        Обновляет статус книги.
        
        Args:
            user_id: ID пользователя
            book_id: ID книги
            status: Новый статус
            current_page: Текущая страница
            
        Returns:
            True если успешно
            
        Raises:
            UserManagerError: При ошибке базы данных
        """
        try:
            return self.db.update_book_status(user_id, book_id, status, current_page)
        except DatabaseError as e:
            self.logger.error(f"Ошибка обновления статуса: {e}")
            raise UserManagerError(f"Ошибка обновления статуса: {e}")
    
    def rate_book(self, user_id: int, book_id: int, rating: int) -> bool:
        """
        Оценивает книгу.
        
        Args:
            user_id: ID пользователя
            book_id: ID книги
            rating: Оценка от 1 до 5
            
        Returns:
            True если успешно
            
        Raises:
            UserManagerError: При ошибке базы данных
            ValueError: При неверной оценке
        """
        try:
            return self.db.rate_book(user_id, book_id, rating)
        except DatabaseError as e:
            self.logger.error(f"Ошибка оценки книги: {e}")
            raise UserManagerError(f"Ошибка оценки книги: {e}")
    
    def get_user_books(self, user_id: int, status: str = None) -> List[UserBook]:
        """
        Получает книги пользователя.
        
        Args:
            user_id: ID пользователя
            status: Статус для фильтрации
            
        Returns:
            Список книг пользователя
            
        Raises:
            UserManagerError: При ошибке базы данных
        """
        try:
            books_data = self.db.get_user_books(user_id, status)
            return [UserBook(book) for book in books_data]
        except DatabaseError as e:
            self.logger.error(f"Ошибка получения книг пользователя: {e}")
            raise UserManagerError(f"Ошибка получения книг пользователя: {e}")
    
    def get_book_info(self, user_id: int, book_id: int) -> Optional[UserBook]:
        """
        Получает информацию о конкретной книге пользователя.
        
        Args:
            user_id: ID пользователя
            book_id: ID книги
            
        Returns:
            Книга пользователя или None
            
        Raises:
            UserManagerError: При ошибке базы данных
        """
        try:
            books = self.get_user_books(user_id)
            for book in books:
                if book.book_id == book_id:
                    return book
            return None
        except DatabaseError as e:
            self.logger.error(f"Ошибка получения информации о книге: {e}")
            raise UserManagerError(f"Ошибка получения информации о книге: {e}")
    
    def has_book(self, user_id: int, book_id: int) -> bool:
        """
        Проверяет, есть ли книга у пользователя.
        
        Args:
            user_id: ID пользователя
            book_id: ID книги
            
        Returns:
            True если книга есть у пользователя
        """
        return self.get_book_info(user_id, book_id) is not None
    
    def update_progress(self, user_id: int, book_id: int, current_page: int) -> bool:
        """
        Обновляет прогресс чтения.
        
        Args:
            user_id: ID пользователя
            book_id: ID книги
            current_page: Номер текущей страницы
            
        Returns:
            True если успешно
        """
        return self.update_book_status(user_id, book_id, 'reading', current_page)
    
    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получает статистику пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь со статистикой
            
        Raises:
            UserManagerError: При ошибке базы данных
        """
        try:
            return self.db.get_user_stats(user_id)
        except DatabaseError as e:
            self.logger.error(f"Ошибка получения статистики: {e}")
            raise UserManagerError(f"Ошибка получения статистики: {e}")
