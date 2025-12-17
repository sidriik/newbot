#!/usr/bin/env python3
"""
main.py - Точка входа для запуска BookBot

Этот модуль запускает Telegram бота для учета книг.
"""

import sys
import os
from pathlib import Path

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent))

try:
    from bot import BookBot
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что все файлы находятся в одной директории.")
    sys.exit(1)


def main():
    """
    Основная функция запуска бота.
    
    Инициализирует и запускает Telegram бота для учета книг.
    """
    print("=" * 50)
    print(" Запуск BookBot - помощника для учета книг")
    print("=" * 50)
    
    # Ваш токен Telegram бота
    TOKEN = "8371793740:AAGyHz10Ro6JabxomkyjDGsjWhNaf3SUeMI"
    
    if not TOKEN or TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        print(" Ошибка: Токен бота не указан.")
        print("Пожалуйста, укажите токен в переменной TOKEN в файле main.py")
        sys.exit(1)
    
    # Проверяем структуру токена
    if not TOKEN.startswith("8371793740:"):
        print("  Внимание: Токен выглядит нестандартно.")
        print("Убедитесь, что это правильный токен от @BotFather")
    
    try:
        # Создаем и запускаем бота
        print(" Инициализация бота...")
        bot = BookBot(TOKEN)
        
        print(" Бот инициализирован успешно")
        print(" Запуск в режиме опроса...")
        
        bot.run()
        
    except ImportError as e:
        print(f" Ошибка: Не установлена библиотека python-telegram-bot")
        print("Установите её командой: pip install python-telegram-bot")
        print(f"Подробности: {e}")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n Остановка BookBot...")
        print(" До свидания!")
    
    except Exception as e:
        print(f" Критическая ошибка: {e}")
        print("\nВозможные причины:")
        print("1. Неправильный токен бота")
        print("2. Проблемы с интернет-соединением")
        print("3. Бот заблокирован в Telegram")
        print("4. Проблемы с базой данных")
        sys.exit(1)


if __name__ == '__main__':
    main()
