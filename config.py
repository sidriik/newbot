#!/usr/bin/env python3
"""
config.py - Конфигурация BookBot
"""

import os
from pathlib import Path


class Config:
    """Конфигурация приложения."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "books.db"
        self.genres = [
            "Классика", "Фэнтези", "Роман", "Детектив", "Научная фантастика",
            "Приключения", "Ужасы", "Исторический", "Биография", "Психология",
            "Поэзия", "Драма", "Комедия", "Триллер", "Мистика"
        ]
        
        # Создаем директорию для данных
        self.data_dir.mkdir(exist_ok=True, parents=True)


config = Config()
