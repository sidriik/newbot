#!/usr/bin/env python3
"""
bot.py - Основной модуль Telegram бота BookBot
"""

import logging
import asyncio
from typing import Optional

# Импорт библиотеки для работы с Telegram
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, CallbackQueryHandler,
        ContextTypes, filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError as e:
    print(f"Внимание: Библиотека python-telegram-bot не установлена: {e}")
    print("Установите её командой: pip install python-telegram-bot")
    TELEGRAM_AVAILABLE = False

from database import Database
from models import UserManager, BookManager, Book, UserBook


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class BookBot:
    """Основной класс Telegram бота для учета книг."""
    
    def __init__(self, token: str):
        """
        Инициализация бота.
        
        Args:
            token: Токен Telegram бота
        """
        if not TELEGRAM_AVAILABLE:
            raise ImportError("Библиотека python-telegram-bot не установлена")
        
        self.token = token
        
        # Инициализируем базу данных
        try:
            self.db = Database("data/books.db")
            self.user_manager = UserManager(self.db)
            self.book_manager = BookManager(self.db)
            logger.info("База данных и менеджеры инициализированы")
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise
        
        # Создаем приложение Telegram
        self.application = Application.builder().token(token).build()
        
        # Регистрируем обработчики
        self._register_handlers()
        
        logger.info("BookBot инициализирован успешно")
    
    def _register_handlers(self):
        """Регистрирует обработчики команд."""
        # Команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("progress", self.progress_command))
        self.application.add_handler(CommandHandler("add", self.add_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("top", self.top_command))
        
        # Обработчики кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Обработчик текстовых сообщений
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message_handler)
        )
        
        # Обработчик ошибок
        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /start.
        
        Показывает приветственное сообщение и главное меню.
        """
        try:
            user = update.effective_user
            
            # Получаем или создаем пользователя
            user_id = self.user_manager.get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            logger.info(f"Пользователь {user_id} ({user.username}) использовал /start")
            
            welcome_text = f"""👋 Привет, {user.first_name}!

Я — BookBot, ваш помощник для учета книг!

📚 Что я умею:
• 🔍 Искать книги по названию, автору или жанру
• 📚 Добавлять книги в вашу коллекцию
• 📖 Отслеживать прогресс чтения
• ⭐ Оценивать прочитанные книги
• 📊 Показывать статистику чтения
• 🏆 Находить самые популярные книги

Выберите действие из меню:"""
            
            keyboard = self._create_main_menu_keyboard()
            await update.message.reply_text(welcome_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка в команде /start: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help."""
        help_text = """📚 BookBot - Помощник для учета книг

📋 Основные команды:
/start - Главное меню
/help - Эта справка
/progress <ID> <страница> - Обновить прогресс чтения
/add <ID> - Добавить книгу по ID
/search <запрос> - Поиск книг
/stats - Ваша статистика
/top <rating|popularity> [жанр|автор] - Топ книг

🎯 Как начать:
1. 🔍 Найдите книгу через "Поиск книг"
2. ➕ Добавьте понравившуюся книгу
3. 📖 Начните читать из раздела "Начать читать"
4. 📊 Обновляйте прогресс командой /progress
5. ⭐ Оцените книгу после прочтения

💡 Для удобства используйте кнопки меню!"""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📚 Главное меню", callback_data="main_menu"),
            InlineKeyboardButton("🔍 Поиск книг", callback_data="search")
        ]])
        
        await update.message.reply_text(help_text, reply_markup=keyboard)
    
    async def progress_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /progress."""
        if not context.args or len(context.args) != 2:
            await update.message.reply_text(
                "📝 Использование: /progress <ID_книги> <номер_страницы>\n"
                "Пример: /progress 1 150\n\n"
                "ID книги можно найти в разделе 'Мои книги'."
            )
            return
        
        try:
            user = update.effective_user
            book_id = int(context.args[0])
            current_page = int(context.args[1])
            
            # Получаем ID пользователя
            user_db_id = self.user_manager.get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            
            # Проверяем, есть ли книга у пользователя
            book_info = self.user_manager.get_book_info(user_db_id, book_id)
            if not book_info:
                await update.message.reply_text(
                    "❌ У вас нет этой книги в коллекции.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            # Проверяем статус
            if book_info.status != 'reading':
                await update.message.reply_text(
                    "❌ Эту книгу вы сейчас не читаете.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📖 Начать читать", callback_data=f"start_{book_id}"),
                        InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")
                    ]])
                )
                return
            
            # Получаем информацию о книге
            book = self.book_manager.get_book(book_id)
            if not book:
                await update.message.reply_text(
                    "❌ Книга не найдена.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            # Проверяем номер страницы
            if current_page > book.total_pages:
                await update.message.reply_text(
                    f"❌ В этой книге только {book.total_pages} страниц!",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            # Обновляем прогресс
            success = self.user_manager.update_progress(user_db_id, book_id, current_page)
            
            if not success:
                await update.message.reply_text(
                    "❌ Не удалось обновить прогресс.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            # Рассчитываем прогресс
            progress = (current_page / book.total_pages) * 100
            
            if progress >= 100:
                # Автоматически завершаем чтение
                self.user_manager.update_book_status(user_db_id, book_id, 'completed')
                
                message = f"""🎉 Поздравляем! Вы прочитали книгу!

{book.title}
👤 {book.author}

📊 Прогресс: {current_page}/{book.total_pages} страниц (100%)"""
                
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("⭐ Оценить книгу", callback_data=f"rate_{book_id}"),
                    InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")
                ]])
            else:
                message = f"""📖 Прогресс обновлен!

{book.title}
👤 {book.author}

📊 Страница: {current_page} из {book.total_pages}
📈 Прочитано: {progress:.1f}%"""
                
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 Обновить еще", callback_data=f"progress_{book_id}"),
                    InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")
                ]])
            
            await update.message.reply_text(message, reply_markup=keyboard)
            
        except ValueError:
            await update.message.reply_text(
                "❌ ID книги и номер страницы должны быть числами.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка в команде /progress: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
    
    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /add."""
        if not context.args:
            await update.message.reply_text(
                "📝 Использование: /add <ID_книги>\n"
                "Пример: /add 1\n\n"
                "ID книги можно найти при поиске."
            )
            return
        
        try:
            user = update.effective_user
            book_id = int(context.args[0])
            
            # Получаем ID пользователя
            user_db_id = self.user_manager.get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            
            # Проверяем существование книги
            book = self.book_manager.get_book(book_id)
            if not book:
                await update.message.reply_text(
                    f"❌ Книга с ID {book_id} не найдена.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔍 Найти книгу", callback_data="search"),
                        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                    ]])
                )
                return
            
            # Добавляем книгу
            success = self.user_manager.add_book(user_db_id, book_id, 'planned')
            
            if not success:
                await update.message.reply_text(
                    "❌ Эта книга уже есть в вашей коллекции.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
                        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                    ]])
                )
                return
            
            message = f"""✅ Книга добавлена!

{book.title}
👤 {book.author}
📂 {book.genre}
📄 {book.total_pages} страниц

📂 Статус: 📅 Запланировано

Что дальше?"""
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📖 Начать читать", callback_data=f"start_{book_id}"),
                InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")
            ], [
                InlineKeyboardButton("➕ Добавить еще", callback_data="add_book"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
            
            await update.message.reply_text(message, reply_markup=keyboard)
            
        except ValueError:
            await update.message.reply_text(
                "❌ ID книги должен быть числом.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка в команде /add: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /search."""
        if not context.args:
            # Показываем меню поиска
            await self._show_search_menu(update)
            return
        
        query = " ".join(context.args)
        await self._perform_search(update, query, "")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stats."""
        try:
            user = update.effective_user
            
            # Получаем ID пользователя
            user_db_id = self.user_manager.get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            
            # Получаем статистику
            stats = self.user_manager.get_stats(user_db_id)
            
            # Формируем сообщение
            message_lines = [
                "📊 Ваша статистика чтения:",
                "",
                f"📚 Всего книг: {stats['total']}",
                f"📅 Запланировано: {stats['planned']}",
                f"📖 Читаю сейчас: {stats['reading']}",
                f"✅ Прочитано: {stats['completed']}",
                f"❌ Брошено: {stats['dropped']}",
                "",
                f"📈 Прочитано страниц: {stats['total_pages_read']}"
            ]
            
            if stats['avg_rating'] > 0:
                message_lines.append(f"⭐ Средняя оценка: {stats['avg_rating']}/5")
            
            # Получаем последние прочитанные книги
            completed_books = self.user_manager.get_user_books(user_db_id, 'completed')[:3]
            if completed_books:
                message_lines.extend(["", "📖 Последние прочитанные книги:"])
                for book in completed_books:
                    rating = f" ⭐ {book.rating}/5" if book.rating else ""
                    message_lines.append(f"• {book.title[:20]}...{rating}")
            
            message = "\n".join(message_lines)
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
                InlineKeyboardButton("⭐ Оценить книги", callback_data="rate_book")
            ], [
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
            
            await update.message.reply_text(message, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка в команде /stats: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при получении статистики.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
    
    async def top_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /top."""
        if not context.args:
            # Показываем меню выбора критерия
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("⭐ По рейтингу", callback_data="top_rating"),
                InlineKeyboardButton("👥 По популярности", callback_data="top_popularity")
            ], [
                InlineKeyboardButton("🔍 Поиск книг", callback_data="search"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
            
            await update.message.reply_text(
                "🏆 Выберите критерий для топ книг:",
                reply_markup=keyboard
            )
            return
        
        criteria = context.args[0].lower()
        filter_by = context.args[1] if len(context.args) > 1 else ""
        
        if criteria not in ['rating', 'popularity']:
            await update.message.reply_text(
                "📝 Использование: /top <rating|popularity> [жанр|автор]\n"
                "Примеры:\n"
                "/top rating - книги с наивысшим рейтингом\n"
                "/top popularity - самые популярные книги\n"
                "/top rating фэнтези - лучшие книги в жанре фэнтези"
            )
            return
        
        await self._show_top_books(update, criteria, filter_by)
    
    async def text_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений."""
        query = update.message.text.strip()
        
        if len(query) < 2:
            await update.message.reply_text(
                "🔍 Введите запрос для поиска (минимум 2 символа).",
                reply_markup=self._create_back_to_menu_keyboard()
            )
            return
        
        await self._perform_search(update, query, "")
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на inline-кнопки."""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        callback_data = query.data
        
        logger.info(f"Пользователь {user.id} нажал кнопку: {callback_data}")
        
        # Получаем ID пользователя
        try:
            user_db_id = self.user_manager.get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка. Попробуйте позже.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
            return
        
        # Обрабатываем callback_data
        if callback_data == "main_menu":
            await self._show_main_menu(query)
        
        elif callback_data == "mybooks":
            await self._show_user_books(query, user_db_id)
        
        elif callback_data == "search":
            await self._show_search_menu(query)
        
        elif callback_data == "add_book":
            await self._show_add_book_menu(query, user_db_id)
        
        elif callback_data == "start_reading":
            await self._show_start_reading_menu(query, user_db_id)
        
        elif callback_data == "stats":
            await self._show_user_stats(query, user_db_id)
        
        elif callback_data == "rate_book":
            await self._show_rate_book_menu(query, user_db_id)
        
        elif callback_data == "top_books":
            await self._show_top_books_menu(query)
        
        elif callback_data.startswith("top_"):
            criteria = callback_data.replace("top_", "")
            await self._show_top_books(query, criteria)
        
        elif callback_data.startswith("genre_"):
            genre = callback_data.replace("genre_", "")
            await self._perform_search(query, "", genre)
        
        elif callback_data.startswith("search_"):
            # Обработка специальных поисковых запросов
            pass
        
        elif callback_data.startswith("add_"):
            try:
                book_id = int(callback_data.replace("add_", ""))
                await self._add_book_from_button(query, user_db_id, book_id)
            except ValueError:
                await query.edit_message_text(
                    "❌ Ошибка: неверный ID книги.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
        
        elif callback_data.startswith("start_"):
            try:
                book_id = int(callback_data.replace("start_", ""))
                await self._start_reading_book(query, user_db_id, book_id)
            except ValueError:
                await query.edit_message_text(
                    "❌ Ошибка: неверный ID книги.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
        
        elif callback_data.startswith("progress_"):
            try:
                book_id = int(callback_data.replace("progress_", ""))
                await self._show_progress_instructions(query, book_id)
            except ValueError:
                await query.edit_message_text(
                    "❌ Ошибка: неверный ID книги.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
        
        elif callback_data.startswith("rate_"):
            try:
                parts = callback_data.replace("rate_", "").split("_")
                if len(parts) == 2:
                    book_id = int(parts[0])
                    rating = int(parts[1])
                    await self._rate_book_from_button(query, user_db_id, book_id, rating)
                else:
                    # Просто показываем меню оценки
                    book_id = int(parts[0])
                    await self._show_rate_specific_book(query, user_db_id, book_id)
            except ValueError:
                await query.edit_message_text(
                    "❌ Ошибка оценки.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
        
        elif callback_data.startswith("finish_"):
            try:
                book_id = int(callback_data.replace("finish_", ""))
                await self._finish_reading_book(query, user_db_id, book_id)
            except ValueError:
                await query.edit_message_text(
                    "❌ Ошибка: неверный ID книги.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
        
        elif callback_data.startswith("remove_"):
            try:
                book_id = int(callback_data.replace("remove_", ""))
                await self._remove_book_from_collection(query, user_db_id, book_id)
            except ValueError:
                await query.edit_message_text(
                    "❌ Ошибка: неверный ID книги.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
        
        else:
            logger.warning(f"Неизвестный callback_data: {callback_data}")
            await query.edit_message_text(
                "❌ Неизвестная команда.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок."""
        logger.error(f"Ошибка: {context.error}")
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Произошла ошибка. Попробуйте позже.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
        except Exception as e:
            logger.error(f"Ошибка в обработчике ошибок: {e}")
    
    # Вспомогательные методы
    
    def _create_main_menu_keyboard(self):
        """Создает клавиатуру главного меню."""
        keyboard = [
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton("🔍 Поиск книг", callback_data="search")],
            [InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book")],
            [InlineKeyboardButton("📖 Начать читать", callback_data="start_reading")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("⭐ Оценить книги", callback_data="rate_book")],
            [InlineKeyboardButton("🏆 Топ книги", callback_data="top_books")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _create_back_to_menu_keyboard(self):
        """Создает клавиатуру с кнопкой возврата."""
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]])
    
    async def _show_main_menu(self, query):
        """Показывает главное меню."""
        keyboard = self._create_main_menu_keyboard()
        await query.edit_message_text(
            "📚 BookBot - Главное меню\n\nВыберите действие:",
            reply_markup=keyboard
        )
    
    async def _show_user_books(self, query, user_db_id):
        """Показывает книги пользователя."""
        try:
            books = self.user_manager.get_user_books(user_db_id)
            
            if not books:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book"),
                    InlineKeyboardButton("🔍 Найти книгу", callback_data="search")
                ], [
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]])
                
                await query.edit_message_text(
                    "📭 У вас пока нет книг в коллекции.",
                    reply_markup=keyboard
                )
                return
            
            # Группируем книги по статусу
            books_by_status = {
                'planned': [],
                'reading': [],
                'completed': [],
                'dropped': []
            }
            
            for book in books:
                if book.status in books_by_status:
                    books_by_status[book.status].append(book)
            
            # Формируем сообщение
            message_lines = ["📚 Ваша коллекция книг:\n"]
            
            status_names = {
                'planned': '📅 Запланировано',
                'reading': '📖 Читаю сейчас',
                'completed': '✅ Прочитано',
                'dropped': '❌ Брошено'
            }
            
            for status, books_list in books_by_status.items():
                if books_list:
                    message_lines.append(f"\n{status_names[status]} ({len(books_list)}):")
                    for i, book in enumerate(books_list[:5], 1):
                        short_title = book.title[:20] + "..." if len(book.title) > 20 else book.title
                        
                        if status == 'reading' and book.current_page > 0:
                            progress = book.get_progress_percentage()
                            message_lines.append(f"{i}. {short_title} - стр. {book.current_page} ({progress:.1f}%)")
                        else:
                            rating = f" ⭐ {book.rating}" if book.rating else ""
                            message_lines.append(f"{i}. {short_title}{rating}")
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📖 Начать читать", callback_data="start_reading"),
                InlineKeyboardButton("⭐ Оценить", callback_data="rate_book")
            ], [
                InlineKeyboardButton("🔍 Поиск", callback_data="search"),
                InlineKeyboardButton("➕ Добавить", callback_data="add_book")
            ], [
                InlineKeyboardButton("📊 Статистика", callback_data="stats"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
            
            await query.edit_message_text("\n".join(message_lines), reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка при показе книг пользователя: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при загрузке ваших книг.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
    
    async def _show_search_menu(self, update_or_query):
        """Показывает меню поиска."""
        genres = self.book_manager.get_all_genres()
        
        # Создаем клавиатуру с жанрами
        keyboard_buttons = []
        for i in range(0, min(len(genres), 8), 2):
            row = []
            row.append(InlineKeyboardButton(
                f"📂 {genres[i]}", 
                callback_data=f"genre_{genres[i]}"
            ))
            if i + 1 < len(genres):
                row.append(InlineKeyboardButton(
                    f"📂 {genres[i+1]}", 
                    callback_data=f"genre_{genres[i+1]}"
                ))
            keyboard_buttons.append(row)
        
        keyboard_buttons.append([
            InlineKeyboardButton("🔍 Поиск по названию/автору", callback_data="search_input")
        ])
        keyboard_buttons.append([
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        text = "🔍 Поиск книг\n\nВыберите жанр или выполните поиск по названию/автору:"
        
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(text, reply_markup=keyboard)
        else:
            await update_or_query.message.reply_text(text, reply_markup=keyboard)
    
    async def _perform_search(self, update_or_query, query: str, genre: str):
        """Выполняет поиск книг."""
        try:
            books = self.book_manager.search_books(query, genre, limit=10)
            
            if not books:
                if query:
                    message = f"📭 По запросу '{query}' ничего не найдено."
                elif genre:
                    message = f"📭 В жанре '{genre}' ничего не найдено."
                else:
                    message = "📭 Книги не найдены."
                
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔍 Новый поиск", callback_data="search"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]])
                
                if hasattr(update_or_query, 'edit_message_text'):
                    await update_or_query.edit_message_text(message, reply_markup=keyboard)
                else:
                    await update_or_query.message.reply_text(message, reply_markup=keyboard)
                return
            
            # Формируем сообщение с результатами
            if query:
                title = f"🔍 Найдено по запросу '{query}':"
            elif genre:
                title = f"🔍 Книги в жанре '{genre}':"
            else:
                title = "🔍 Все книги:"
            
            message_lines = [f"{title}\n"]
            
            keyboard_buttons = []
            for i, book in enumerate(books, 1):
                # Получаем статистику для книги
                stats = self.db.get_book_statistics(book.id)
                
                rating_info = f" ⭐ {stats.get('avg_rating', 0)}" if stats.get('avg_rating', 0) > 0 else ""
                popularity_info = f" 👥 {stats.get('total_added', 0)}"
                
                message_lines.append(f"\n{i}. {book.title}")
                message_lines.append(f"   👤 {book.author}")
                message_lines.append(f"   📂 {book.genre}")
                message_lines.append(f"   📊{rating_info}{popularity_info}")
                
                # Кнопка для добавления
                short_title = book.title[:15] + "..." if len(book.title) > 15 else book.title
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        f"➕ Добавить '{short_title}'",
                        callback_data=f"add_{book.id}"
                    )
                ])
            
            # Кнопки навигации
            keyboard_buttons.append([
                InlineKeyboardButton("🔍 Новый поиск", callback_data="search"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ])
            
            keyboard = InlineKeyboardMarkup(keyboard_buttons)
            
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(
                    "\n".join(message_lines),
                    reply_markup=keyboard
                )
            else:
                await update_or_query.message.reply_text(
                    "\n".join(message_lines),
                    reply_markup=keyboard
                )
            
        except Exception as e:
            logger.error(f"Ошибка при поиске книг: {e}")
            error_message = "❌ Произошла ошибка при поиске книг."
            
            keyboard = self._create_back_to_menu_keyboard()
            
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(error_message, reply_markup=keyboard)
            else:
                await update_or_query.message.reply_text(error_message, reply_markup=keyboard)
    
    async def _show_add_book_menu(self, query, user_db_id):
        """Показывает меню добавления книги."""
        # Получаем несколько популярных книг
        popular_books = self.book_manager.get_top_books('popularity', limit=5)
        
        if not popular_books:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 Найти книгу", callback_data="search"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
            
            await query.edit_message_text(
                "📚 Популярные книги не найдены.",
                reply_markup=keyboard
            )
            return
        
        # Формируем сообщение
        message_lines = ["📚 Популярные книги для добавления:\n"]
        
        keyboard_buttons = []
        for book in popular_books:
            # Проверяем, есть ли уже эта книга у пользователя
            has_book = self.user_manager.has_book(user_db_id, book.id)
            
            short_title = book.title[:20] + "..." if len(book.title) > 20 else book.title
            button_text = f"📖 {short_title}"
            
            if has_book:
                button_text += " ✓"
                callback = "no_action"
            else:
                callback = f"add_{book.id}"
            
            keyboard_buttons.append([InlineKeyboardButton(button_text, callback_data=callback)])
            
            # Добавляем информацию о книге
            stats = self.db.get_book_statistics(book.id)
            rating_info = f" ⭐ {stats.get('avg_rating', 0)}" if stats.get('avg_rating', 0) > 0 else ""
            message_lines.append(f"\n• {book.title}{rating_info}")
        
        # Дополнительные кнопки
        keyboard_buttons.append([
            InlineKeyboardButton("🔍 Найти другую книгу", callback_data="search")
        ])
        keyboard_buttons.append([
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await query.edit_message_text("\n".join(message_lines), reply_markup=keyboard)
    
    async def _add_book_from_button(self, query, user_db_id, book_id):
        """Добавляет книгу из кнопки."""
        try:
            book = self.book_manager.get_book(book_id)
            if not book:
                await query.edit_message_text(
                    "❌ Книга не найдена.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            success = self.user_manager.add_book(user_db_id, book_id, 'planned')
            
            if not success:
                await query.edit_message_text(
                    "❌ Эта книга уже есть в вашей коллекции.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
                        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                    ]])
                )
                return
            
            message = f"""✅ Книга добавлена!

{book.title}
👤 {book.author}
📂 {book.genre}

📂 Статус: 📅 Запланировано

Что дальше?"""
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📖 Начать читать", callback_data=f"start_{book_id}"),
                InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")
            ], [
                InlineKeyboardButton("➕ Добавить еще", callback_data="add_book"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
            
            await query.edit_message_text(message, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении книги: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при добавлении книги.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
    
    async def _show_start_reading_menu(self, query, user_db_id):
        """Показывает меню начала чтения."""
        planned_books = self.user_manager.get_user_books(user_db_id, 'planned')
        
        if not planned_books:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book"),
                InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")
            ], [
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
            
            await query.edit_message_text(
                "📭 У вас нет запланированных книг для чтения.",
                reply_markup=keyboard
            )
            return
        
        # Формируем сообщение
        message_lines = ["📚 Выберите книгу для начала чтения:\n"]
        
        keyboard_buttons = []
        for book in planned_books[:5]:
            short_title = book.title[:20] + "..." if len(book.title) > 20 else book.title
            keyboard_buttons.append([
                InlineKeyboardButton(f"📖 {short_title}", callback_data=f"start_{book.book_id}")
            ])
            
            # Информация о книге
            book_info = self.book_manager.get_book(book.book_id)
            if book_info:
                message_lines.append(f"\n• {book.title}")
                message_lines.append(f"  👤 {book.author}")
                if book_info.total_pages:
                    message_lines.append(f"  📄 {book_info.total_pages} страниц")
        
        # Дополнительные кнопки
        keyboard_buttons.append([
            InlineKeyboardButton("📚 Все мои книги", callback_data="mybooks")
        ])
        keyboard_buttons.append([
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await query.edit_message_text("\n".join(message_lines), reply_markup=keyboard)
    
    async def _start_reading_book(self, query, user_db_id, book_id):
        """Начинает чтение книги."""
        try:
            if not self.user_manager.has_book(user_db_id, book_id):
                await query.edit_message_text(
                    "❌ У вас нет этой книги в коллекции.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book"),
                        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                    ]])
                )
                return
            
            success = self.user_manager.update_book_status(user_db_id, book_id, 'reading')
            
            if not success:
                await query.edit_message_text(
                    "❌ Не удалось начать чтение.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            book = self.book_manager.get_book(book_id)
            if not book:
                await query.edit_message_text(
                    "❌ Информация о книге не найдена.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            message = f"""📖 Начинаем читать!

{book.title}
👤 {book.author}
📄 Всего страниц: {book.total_pages}

📂 Статус: 📖 Читаю сейчас

Чтобы обновить прогресс, отправьте:
/progress {book_id} <номер_страницы>

Пример:
/progress {book_id} 50"""
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📊 Обновить прогресс", callback_data=f"progress_{book_id}"),
                InlineKeyboardButton("✅ Закончить чтение", callback_data=f"finish_{book_id}")
            ], [
                InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
            
            await query.edit_message_text(message, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка при начале чтения книги: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при начале чтения.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
    
    async def _show_progress_instructions(self, query, book_id):
        """Показывает инструкции по обновлению прогресса."""
        await query.edit_message_text(
            f"📊 Чтобы обновить прогресс чтения, отправьте команду:\n"
            f"/progress {book_id} <номер_страницы>\n\n"
            f"Например: /progress {book_id} 150\n\n"
            f"Эта команда обновит текущую страницу книги и рассчитает процент прочтения.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
    
    async def _finish_reading_book(self, query, user_db_id, book_id):
        """Завершает чтение книги."""
        try:
            if not self.user_manager.has_book(user_db_id, book_id):
                await query.edit_message_text(
                    "❌ У вас нет этой книги в коллекции.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            success = self.user_manager.update_book_status(user_db_id, book_id, 'completed')
            
            if not success:
                await query.edit_message_text(
                    "❌ Не удалось отметить книгу как прочитанную.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            book = self.book_manager.get_book(book_id)
            if not book:
                await query.edit_message_text(
                    "❌ Информация о книге не найдена.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            message = f"""🎉 Поздравляем с прочтением книги!

{book.title}
👤 {book.author}

📂 Статус: ✅ Прочитано

Хотите оценить книгу?"""
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("⭐ Оценить книгу", callback_data=f"rate_{book_id}"),
                InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")
            ], [
                InlineKeyboardButton("📖 Начать новую книгу", callback_data="start_reading"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
            
            await query.edit_message_text(message, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка при завершении чтения книги: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при завершении чтения.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
    
    async def _show_user_stats(self, query, user_db_id):
        """Показывает статистику пользователя."""
        try:
            stats = self.user_manager.get_stats(user_db_id)
            
            message_lines = [
                "📊 Ваша статистика чтения:",
                "",
                f"📚 Всего книг в коллекции: {stats['total']}",
                f"📅 Запланировано: {stats['planned']}",
                f"📖 Читаю сейчас: {stats['reading']}",
                f"✅ Прочитано: {stats['completed']}",
                f"❌ Брошено: {stats['dropped']}",
                "",
                f"📈 Всего прочитано страниц: {stats['total_pages_read']}"
            ]
            
            if stats['avg_rating'] > 0:
                stars = "⭐" * int(round(stats['avg_rating']))
                message_lines.append(f"⭐ Средняя оценка: {stars} ({stats['avg_rating']}/5)")
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
                InlineKeyboardButton("⭐ Оценить книги", callback_data="rate_book")
            ], [
                InlineKeyboardButton("🏆 Топ книги", callback_data="top_books"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
            
            await query.edit_message_text("\n".join(message_lines), reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка при показе статистики: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при получении статистики.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
    
    async def _show_rate_book_menu(self, query, user_db_id):
        """Показывает меню оценки книг."""
        completed_books = self.user_manager.get_user_books(user_db_id, 'completed')
        unrated_books = [book for book in completed_books if not book.rating]
        
        if not unrated_books:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📖 Начать читать", callback_data="start_reading"),
                InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")
            ], [
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
            
            await query.edit_message_text(
                "🎉 Все ваши прочитанные книги уже оценены!",
                reply_markup=keyboard
            )
            return
        
        # Формируем сообщение
        message_lines = ["⭐ Оцените прочитанные книги:\n"]
        
        keyboard_buttons = []
        for book in unrated_books[:3]:
            message_lines.append(f"\n📖 {book.title}")
            message_lines.append(f"   👤 {book.author}")
            
            # Кнопки оценки от 1 до 5
            rating_row = []
            for rating in range(1, 6):
                rating_row.append(
                    InlineKeyboardButton(f"{rating}⭐", callback_data=f"rate_{book.book_id}_{rating}")
                )
            keyboard_buttons.append(rating_row)
        
        # Дополнительные кнопки
        keyboard_buttons.append([
            InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await query.edit_message_text("\n".join(message_lines), reply_markup=keyboard)
    
    async def _show_rate_specific_book(self, query, user_db_id, book_id):
        """Показывает меню оценки конкретной книги."""
        try:
            book_info = self.user_manager.get_book_info(user_db_id, book_id)
            if not book_info or book_info.status != 'completed':
                await query.edit_message_text(
                    "❌ Эту книгу нельзя оценить (она не прочитана).",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            book = self.book_manager.get_book(book_id)
            if not book:
                await query.edit_message_text(
                    "❌ Книга не найдена.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            message = f"⭐ Оцените книгу:\n\n{book.title}\n👤 {book.author}"
            
            # Кнопки оценки
            keyboard_buttons = []
            rating_row = []
            for rating in range(1, 6):
                rating_row.append(
                    InlineKeyboardButton(f"{rating}⭐", callback_data=f"rate_{book_id}_{rating}")
                )
            keyboard_buttons.append(rating_row)
            
            keyboard_buttons.append([
                InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ])
            
            keyboard = InlineKeyboardMarkup(keyboard_buttons)
            
            await query.edit_message_text(message, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка при показе оценки книги: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
    
    async def _rate_book_from_button(self, query, user_db_id, book_id, rating):
        """Оценивает книгу из кнопки."""
        try:
            success = self.user_manager.rate_book(user_db_id, book_id, rating)
            
            if not success:
                await query.edit_message_text(
                    "❌ Не удалось оценить книгу.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            book = self.book_manager.get_book(book_id)
            if not book:
                await query.edit_message_text(
                    "✅ Книга оценена!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
                        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                    ]])
                )
                return
            
            stars = "⭐" * rating
            stats = self.db.get_book_statistics(book_id)
            
            message = f"""✅ Спасибо за оценку!

{book.title}
👤 {book.author}

Ваша оценка: {stars} ({rating}/5)

Общий рейтинг книги: {stats.get('avg_rating', 0)}/5
({stats.get('rating_count', 0)} оценок)"""
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("⭐ Оценить другую книгу", callback_data="rate_book"),
                InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")
            ], [
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
            
            await query.edit_message_text(message, reply_markup=keyboard)
            
        except ValueError as e:
            logger.error(f"Ошибка значения при оценке книги: {e}")
            await query.edit_message_text(
                "❌ Оценка должна быть от 1 до 5.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка при оценке книги: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при оценке книги.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
    
    async def _show_top_books_menu(self, query):
        """Показывает меню выбора критерия для топ книг."""
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⭐ По рейтингу", callback_data="top_rating"),
            InlineKeyboardButton("👥 По популярности", callback_data="top_popularity")
        ], [
            InlineKeyboardButton("🔍 Поиск книг", callback_data="search"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]])
        
        await query.edit_message_text(
            "🏆 Выберите критерий для топ книг:",
            reply_markup=keyboard
        )
    
    async def _show_top_books(self, update_or_query, criteria: str, filter_by: str = ""):
        """Показывает топ книги по критерию."""
        try:
            # Определяем, что фильтровать
            genres = self.book_manager.get_all_genres()
            genre = filter_by if filter_by in genres else ""
            author = filter_by if not genre and filter_by else ""
            
            books = self.book_manager.get_top_books(criteria, genre, author, limit=5)
            
            if not books:
                message = "📭 Не найдено книг по выбранному критерию."
                if genre:
                    message = f"📭 В жанре '{genre}' не найдено книг."
                elif author:
                    message = f"📭 У автора '{author}' не найдено книг."
                
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏆 Другой критерий", callback_data="top_books"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]])
                
                if hasattr(update_or_query, 'edit_message_text'):
                    await update_or_query.edit_message_text(message, reply_markup=keyboard)
                else:
                    await update_or_query.message.reply_text(message, reply_markup=keyboard)
                return
            
            # Формируем сообщение
            if criteria == 'rating':
                title = "🏆 Книги с наивысшим рейтингом"
            else:
                title = "🏆 Самые популярные книги"
            
            if genre:
                title += f" (жанр: {genre})"
            elif author:
                title += f" (автор: {author})"
            
            message_lines = [f"{title}:\n"]
            
            keyboard_buttons = []
            for i, book in enumerate(books, 1):
                # Получаем статистику
                stats = self.db.get_book_statistics(book.id)
                
                if criteria == 'rating':
                    rating = stats.get('avg_rating', 0)
                    rating_count = stats.get('rating_count', 0)
                    info_line = f"{i}. {book.title} - ⭐ {rating}/5 ({rating_count} оценок)"
                else:
                    total_added = stats.get('total_added', 0)
                    currently_reading = stats.get('currently_reading', 0)
                    info_line = f"{i}. {book.title} - 👥 {total_added} читателей ({currently_reading} сейчас)"
                
                message_lines.append(f"\n{info_line}")
                message_lines.append(f"   👤 {book.author}")
                message_lines.append(f"   📂 {book.genre}")
                
                # Кнопка для добавления
                short_title = book.title[:15] + "..." if len(book.title) > 15 else book.title
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        f"➕ Добавить '{short_title}'",
                        callback_data=f"add_{book.id}"
                    )
                ])
            
            # Дополнительные кнопки
            keyboard_buttons.append([
                InlineKeyboardButton("⭐ По рейтингу", callback_data="top_rating"),
                InlineKeyboardButton("👥 По популярности", callback_data="top_popularity")
            ])
            keyboard_buttons.append([
                InlineKeyboardButton("🔍 Поиск книг", callback_data="search"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ])
            
            keyboard = InlineKeyboardMarkup(keyboard_buttons)
            
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(
                    "\n".join(message_lines),
                    reply_markup=keyboard
                )
            else:
                await update_or_query.message.reply_text(
                    "\n".join(message_lines),
                    reply_markup=keyboard
                )
            
        except Exception as e:
            logger.error(f"Ошибка при показе топ книг: {e}")
            error_message = "❌ Произошла ошибка при получении топ книг."
            
            keyboard = self._create_back_to_menu_keyboard()
            
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(error_message, reply_markup=keyboard)
            else:
                await update_or_query.message.reply_text(error_message, reply_markup=keyboard)
    
    async def _remove_book_from_collection(self, query, user_db_id, book_id):
        """Удаляет книгу из коллекции."""
        try:
            success = self.user_manager.remove_book(user_db_id, book_id)
            
            if not success:
                await query.edit_message_text(
                    "❌ Книга не найдена в вашей коллекции.",
                    reply_markup=self._create_back_to_menu_keyboard()
                )
                return
            
            await query.edit_message_text(
                "✅ Книга удалена из вашей коллекции.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]])
            )
            
        except Exception as e:
            logger.error(f"Ошибка при удалении книги: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при удалении книги.",
                reply_markup=self._create_back_to_menu_keyboard()
            )
    
    def run(self):
        """
        Запускает бота.
        
        Этот метод запускает бота в режиме опроса (polling).
        """
        logger.info("Запуск BookBot...")
        print("=" * 50)
        print(" BookBot запущен успешно!")
        print(" Бот готов к работе")
        print(" База данных: data/books.db")
        print("=" * 50)
        print("Ожидание сообщений...")
        print("Для остановки нажмите Ctrl+C")
        
        self.application.run_polling(allowed_updates=None)
