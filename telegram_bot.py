#!/usr/bin/env python3
"""
telegram_bot.py - Telegram бот для учета книг
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Импортируем наши модули
try:
    from models import UserManager
    from database import db
    print("[INFO] Модули загружены успешно")
except ImportError as e:
    print(f"[ERROR] Ошибка импорта: {e}")
    exit(1)

# Создаем менеджеры
user_manager = UserManager()
book_db = db

# ==================== КОМАНДЫ БОТА ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    try:
        user = update.effective_user
        
        welcome_text = f"""👋 Привет, {user.first_name}!

Я — BookBot, помогу тебе вести список книг.

📖 Доступные команды:
/mybooks - Мои книги
/add <id> - Добавить книгу
/search <название> - Найти книгу
/read <id> - Начать читать книгу
/progress <id> <страница> - Обновить прогресс
/finish <id> - Закончить чтение
/rate <id> <1-5> - Оценить книгу
/stats - Статистика
/remove <id> - Удалить книгу
/help - Помощь

Просто начни вводить название книги для поиска!"""
        
        keyboard = [
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton("🔍 Поиск книг", callback_data="search")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")
        await update.message.reply_text("Произошла ошибка")

async def mybooks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /mybooks"""
    try:
        user_id = update.effective_user.id
        books = user_manager.get_user_books(user_id)
        
        if not books:
            await update.message.reply_text("У вас пока нет книг в коллекции. Используйте /add чтобы добавить книгу.")
            return
        
        books_by_status = {}
        for status in ['planned', 'reading', 'completed', 'dropped']:
            status_books = user_manager.get_user_books(user_id, status)
            if status_books:
                books_by_status[status] = status_books
        
        status_names = {
            'planned': 'Запланировано',
            'reading': 'Читаю сейчас',
            'completed': 'Прочитано',
            'dropped': 'Брошено'
        }
        
        message_lines = ["Ваша библиотека:\n"]
        
        for status, books_list in books_by_status.items():
            message_lines.append(f"\n{status_names[status]} ({len(books_list)}):")
            for i, book in enumerate(books_list[:5], 1):
                book_info = book_db.get_book(book['book_id'])
                if book_info:
                    title = book_info['title']
                    if status == 'reading' and book['current_page'] > 0:
                        message_lines.append(f"{i}. {title} - стр. {book['current_page']}")
                    else:
                        rating = f" ⭐ {book['rating']}" if book['rating'] else ""
                        message_lines.append(f"{i}. {title}{rating}")
        
        await update.message.reply_text("\n".join(message_lines))
    except Exception as e:
        logger.error(f"Ошибка в mybooks: {e}")
        await update.message.reply_text("Произошла ошибка")

async def add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add <id>"""
    try:
        if not context.args:
            await update.message.reply_text("Использование: /add <id_книги>\nПример: /add 1")
            return
        
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        book_info = book_db.get_book(book_id)
        if not book_info:
            await update.message.reply_text(f"Книга с ID {book_id} не найдена.")
            return
        
        if user_manager.add_book(user_id, book_id):
            await update.message.reply_text(
                f"Книга добавлена!\n\n"
                f"{book_info['title']}\n"
                f"Автор: {book_info['author']}\n"
                f"Статус: запланировано"
            )
        else:
            await update.message.reply_text("Не удалось добавить книгу.")
    
    except ValueError:
        await update.message.reply_text("ID книги должен быть числом.")
    except Exception as e:
        logger.error(f"Ошибка в add_book: {e}")
        await update.message.reply_text("Произошла ошибка")

async def search_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /search <запрос>"""
    try:
        if not context.args:
            await update.message.reply_text("Использование: /search <запрос>\nПример: /search Гарри Поттер")
            return
        
        query = " ".join(context.args)
        books = book_db.search_books(query)
        
        if not books:
            await update.message.reply_text(f"По запросу '{query}' ничего не найдено.")
            return
        
        message_parts = [f"Найдено книг: {len(books)}\n"]
        
        for i, book in enumerate(books[:10], 1):
            genre = f" ({book['genre']})" if book['genre'] else ""
            message_parts.append(f"{i}. {book['title']} - {book['author']}{genre}")
            message_parts.append(f"   ID: {book['id']}")
        
        message_parts.append("\nЧтобы добавить книгу: /add <id>")
        
        await update.message.reply_text("\n".join(message_parts))
    except Exception as e:
        logger.error(f"Ошибка в search_books: {e}")
        await update.message.reply_text("Произошла ошибка")

async def start_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /read <id>"""
    try:
        if not context.args:
            await update.message.reply_text("Использование: /read <id_книги>\nПример: /read 1")
            return
        
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        if not user_manager.has_book(user_id, book_id):
            await update.message.reply_text("У вас нет этой книги в коллекции.")
            return
        
        if user_manager.update_book_status(user_id, book_id, "reading"):
            book_info = book_db.get_book(book_id)
            await update.message.reply_text(
                f"Начинаем читать!\n\n"
                f"{book_info['title']}\n"
                f"Автор: {book_info['author']}\n"
                f"Всего страниц: {book_info['total_pages']}"
            )
        else:
            await update.message.reply_text("Не удалось начать чтение.")
    
    except ValueError:
        await update.message.reply_text("ID книги должен быть числом.")
    except Exception as e:
        logger.error(f"Ошибка в start_reading: {e}")
        await update.message.reply_text("Произошла ошибка")

async def update_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /progress <id> <страница>"""
    try:
        if len(context.args) != 2:
            await update.message.reply_text("Использование: /progress <id_книги> <номер_страницы>\nПример: /progress 1 150")
            return
        
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        current_page = int(context.args[1])
        
        book_user_info = user_manager.get_book_info(user_id, book_id)
        if not book_user_info:
            await update.message.reply_text("У вас нет этой книги в коллекции.")
            return
        
        if book_user_info['status'] != 'reading':
            await update.message.reply_text("Эту книгу вы сейчас не читаете.")
            return
        
        book_info = book_db.get_book(book_id)
        
        if user_manager.update_progress(user_id, book_id, current_page):
            progress = (current_page / book_info['total_pages']) * 100
            await update.message.reply_text(
                f"Прогресс обновлен!\n"
                f"Страница: {current_page}\n"
                f"Прогресс: {progress:.1f}%"
            )
        else:
            await update.message.reply_text("Не удалось обновить прогресс.")
    
    except ValueError:
        await update.message.reply_text("ID книги и номер страницы должны быть числами.")
    except Exception as e:
        logger.error(f"Ошибка в update_progress: {e}")
        await update.message.reply_text("Произошла ошибка")

async def finish_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /finish <id>"""
    try:
        if not context.args:
            await update.message.reply_text("Использование: /finish <id_книги>\nПример: /finish 1")
            return
        
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        if not user_manager.has_book(user_id, book_id):
            await update.message.reply_text("У вас нет этой книги в коллекции.")
            return
        
        if user_manager.update_book_status(user_id, book_id, "completed"):
            book_info = book_db.get_book(book_id)
            await update.message.reply_text(
                f"Поздравляем с прочтением!\n\n"
                f"{book_info['title']}\n"
                f"Автор: {book_info['author']}"
            )
        else:
            await update.message.reply_text("Не удалось отметить как прочитанную.")
    
    except ValueError:
        await update.message.reply_text("ID книги должен быть числом.")
    except Exception as e:
        logger.error(f"Ошибка в finish_reading: {e}")
        await update.message.reply_text("Произошла ошибка")

async def rate_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rate <id> <оценка>"""
    try:
        if len(context.args) != 2:
            await update.message.reply_text("Использование: /rate <id_книги> <оценка_1-5>\nПример: /rate 1 5")
            return
        
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        rating = int(context.args[1])
        
        if rating < 1 or rating > 5:
            await update.message.reply_text("Оценка должна быть от 1 до 5.")
            return
        
        if not user_manager.has_book(user_id, book_id):
            await update.message.reply_text("У вас нет этой книги в коллекции.")
            return
        
        if user_manager.rate_book(user_id, book_id, rating):
            book_info = book_db.get_book(book_id)
            stars = "⭐" * rating
            await update.message.reply_text(f"Оценка поставлена!\n\n{book_info['title']}\n{stars} ({rating}/5)")
        else:
            await update.message.reply_text("Не удалось поставить оценку.")
    
    except ValueError:
        await update.message.reply_text("ID книги и оценка должны быть числами.")
    except Exception as e:
        logger.error(f"Ошибка в rate_book: {e}")
        await update.message.reply_text("Произошла ошибка")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats"""
    try:
        user_id = update.effective_user.id
        stats = user_manager.get_stats(user_id)
        
        message = f"""Ваша статистика чтения:

Всего книг: {stats['total']}
Запланировано: {stats['planned']}
Читаю сейчас: {stats['reading']}
Прочитано: {stats['completed']}
Брошено: {stats['dropped']}"""
        
        if stats['avg_rating'] > 0:
            message += f"\nСредняя оценка: {stats['avg_rating']}"
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Ошибка в show_stats: {e}")
        await update.message.reply_text("Произошла ошибка")

async def remove_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /remove <id>"""
    try:
        if not context.args:
            await update.message.reply_text("Использование: /remove <id_книги>\nПример: /remove 1")
            return
        
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        if user_manager.remove_book(user_id, book_id):
            await update.message.reply_text("Книга удалена из вашей коллекции.")
        else:
            await update.message.reply_text("Книга не найдена в вашей коллекции.")
    
    except ValueError:
        await update.message.reply_text("ID книги должен быть числом.")
    except Exception as e:
        logger.error(f"Ошибка в remove_book: {e}")
        await update.message.reply_text("Произошла ошибка")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    try:
        help_text = """BookBot - помощник для учета книг

Основные команды:
/start - Начать работу с ботом
/mybooks - Мои книги
/add <id> - Добавить книгу
/search <запрос> - Найти книгу
/read <id> - Начать читать книгу
/progress <id> <страница> - Обновить прогресс чтения
/finish <id> - Закончить чтение книги
/rate <id> <1-5> - Оценить книгу
/remove <id> - Удалить книгу
/stats - Статистика
/help - Эта справка

Статусы книг:
• planned - Запланировано
• reading - Читаю сейчас
• completed - Прочитано
• dropped - Брошено

Просто напишите название книги для поиска!"""
        
        await update.message.reply_text(help_text)
    except Exception as e:
        logger.error(f"Ошибка в help_command: {e}")
        await update.message.reply_text("Произошла ошибка")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик инлайн-кнопок"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        if query.data == "mybooks":
            stats = user_manager.get_stats(user_id)
            if stats['total'] == 0:
                await query.edit_message_text(
                    "У вас пока нет книг в коллекции. Используйте /add чтобы добавить книгу."
                )
            else:
                await query.edit_message_text(
                    f"В вашей коллекции {stats['total']} книг.\n"
                    f"Прочитано: {stats['completed']}\n"
                    f"Читаю сейчас: {stats['reading']}\n\n"
                    "Используйте /mybooks для подробного списка."
                )
        
        elif query.data == "search":
            await query.edit_message_text(
                "Для поиска книг используйте команду /search\n"
                "Пример: /search Гарри Поттер\n\n"
                "Или просто напишите название книги:"
            )
        
        elif query.data == "stats":
            stats = user_manager.get_stats(user_id)
            await query.edit_message_text(
                f"Ваша статистика:\n\n"
                f"Всего книг: {stats['total']}\n"
                f"Запланировано: {stats['planned']}\n"
                f"Читаю сейчас: {stats['reading']}\n"
                f"Прочитано: {stats['completed']}\n"
                f"Брошено: {stats['dropped']}"
            )
    except Exception as e:
        logger.error(f"Ошибка в button_handler: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений для поиска книг"""
    try:
        text = update.message.text.strip()
        
        if len(text) < 2:
            return
        
        books = book_db.search_books(text)
        
        if not books:
            await update.message.reply_text(
                f"По запросу '{text}' ничего не найдено.\n"
                "Попробуйте другой запрос или используйте /search <запрос>"
            )
            return
        
        message_lines = [f"Найдено по запросу '{text}':\n"]
        
        for i, book in enumerate(books[:5], 1):
            message_lines.append(f"{i}. {book['title']} - {book['author']}")
            message_lines.append(f"   ID: {book['id']}\n")
        
        message_lines.append("Чтобы добавить книгу, используйте /add <id>")
        
        await update.message.reply_text("\n".join(message_lines))
    except Exception as e:
        logger.error(f"Ошибка в handle_text: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
    except:
        pass

def main():
    """Запуск бота"""
    TOKEN = "8371793740:AAGyHz10Ro6JabxomkyjDGsjWhNaf3SUeMI"
    
    print("[INFO] Запуск BookBot...")
    print(f"[INFO] Токен: {TOKEN[:15]}...")
    
    # Проверка токена
    if len(TOKEN) < 30:
        print("[ERROR] Токен слишком короткий!")
        return
    
    try:
        # Создаем приложение
        application = Application.builder().token(TOKEN).build()
        print("[INFO] Приложение создано")
        
        # Добавляем обработчики команд
        commands = [
            ("start", start),
            ("mybooks", mybooks),
            ("add", add_book),
            ("search", search_books),
            ("read", start_reading),
            ("progress", update_progress),
            ("finish", finish_reading),
            ("rate", rate_book),
            ("stats", show_stats),
            ("remove", remove_book),
            ("help", help_command),
        ]
        
        for cmd, handler in commands:
            application.add_handler(CommandHandler(cmd, handler))
            print(f"[INFO] Добавлена команда /{cmd}")
        
        # Обработчик инлайн-кнопок
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        # Обработчик ошибок
        application.add_error_handler(error_handler)
        
        # Запуск бота
        print("[INFO] BookBot успешно запущен")
        print("[INFO] Ожидание сообщений...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"[ERROR] Ошибка запуска: {e}")

if __name__ == '__main__':
    main()
