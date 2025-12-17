#!/usr/bin/env python3
"""
config.py - Конфигурация приложения BookBot

Этот модуль содержит настройки конфигурации для приложения BookBot.
Все пути настроены относительными и могут быть изменены при запуске.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any


class Config:
    """Класс конфигурации приложения BookBot."""
    
    def __init__(self, data_dir: str = "data"):
        """
        Инициализация конфигурации.
        
        Args:
            data_dir (str): Директория для хранения данных (по умолчанию "data")
        """
        self.data_dir = Path(data_dir)
        self._ensure_directories()
        
        # Настройки базы данных
        self.db_path = self.data_dir / "books.db"
        
        # Настройки логирования
        self.log_path = self.data_dir / "bookbot.log"
        
        # Список жанров для выбора
        self.genres = [
            "Классика", "Фэнтези", "Роман", "Детектив", "Научная фантастика",
            "Приключения", "Ужасы", "Исторический", "Биография", "Психология",
            "Поэзия", "Драма", "Комедия", "Триллер", "Мистика"
        ]
        
        # Лимиты
        self.search_limit = 10
        self.popular_limit = 5
    
    def _ensure_directories(self) -> None:
        """Создает необходимые директории, если они не существуют."""
        try:
            self.data_dir.mkdir(exist_ok=True, parents=True)
            print(f"[INFO] Директория данных: {self.data_dir.absolute()}")
        except Exception as e:
            raise RuntimeError(f"Не удалось создать директорию данных: {e}")
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию для логирования."""
        return {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'level': logging.INFO,
            'handlers': [
                logging.FileHandler(self.log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        }


# Создаем глобальный экземпляр конфигурации
config = Config()
