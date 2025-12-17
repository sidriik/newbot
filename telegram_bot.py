#!/usr/bin/env python3
"""
telegram_bot.py - главный файл Telegram бота
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from models import UserManager
from database import db
import html

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем менеджеры
user_manager = UserManager()  # Для пользовательских данных в памяти
book_db = db                  # Для каталога книг в SQLite

# ==================== КОМАНДЫ БОТА ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user = update.effective_user
    welcome_text = (
        f"📚 *Добро пожаловать, {user.first_name}!*\n\n"
        "Я — BookBot, ваш помощник в учёте прочитанных книг.\n\n"
        "*Основные команды:*\n"
        "• /mybooks — Мои книги\n"
        "• /add <id> — Добавить книгу\n"
        "• /search <название> — Найти книгу\n"
        "• /rate <id> <1-5> — Оценить книгу\n"
        "• /stats — Статистика\n"
        "• /remove <id> — Удалить книгу\n"
        "• /help — Справка\n\n"
        "Просто напишите название книги для поиска!"
    )
    
    keyboard = [
        [InlineKeyboardButton("📖 Мои книги", callback_data="mybooks")],
        [InlineKeyboardButton("🔍 Поиск", callback_data="search")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, 
                                   parse_mode='Markdown',
                                   reply_markup=reply_markup)

async def mybooks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает книги пользователя."""
    user_id = update.effective_user.id
    stats = user_manager.get_stats(user_id)
    
    if stats['total'] == 0:
        await update.message.reply_text(
            "📭 *У вас пока нет книг в коллекции.*\n\n"
            "Чтобы добавить книгу:\n"
            "1. Найдите книгу через /search\n"
            "2. Используйте /add <id_книги>",
            parse_mode='Markdown'
        )
        return
    
    # Получаем книги по статусам
    status_names = {
        'planned': '📅 Запланировано',
        'reading': '📖 Читаю сейчас',
        'completed': '✅ Прочитано',
        'dropped': '❌ Брошено'
    }
    
    message_lines = [f"📚 *Ваша библиотека* ({stats['total']} книг):\n"]
    
    for status_code, status_name in status_names.items():
        books = user_manager.get_user_books(user_id, status_code)
        if books:
            message_lines.append(f"\n*{status_name}* ({len(books)}):")
            for i, book in enumerate(books[:5], 1):  # Показываем первые 5
                book_info = book_db.get_book(book['book_id'])
                if book_info:
                    title = book_info['title']
                    rating = f" ⭐ {book['rating']}" if book['rating'] else ""
                    message_lines.append(f"{i}. {title}{rating}")
    
    if stats['avg_rating'] > 0:
        message_lines.append(f"\n📈 *Средняя оценка:* {stats['avg_rating']}")
    
    await update.message.reply_text(
        "\n".join(message_lines),
        parse_mode='Markdown'
    )

async def add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавляет книгу в коллекцию."""
    if not context.args:
        await update.message.reply_text(
            "📝 *Использование:* /add <id_книги> [статус]\n\n"
            "*Статусы:*\n"
            "• planned — Запланировано\n"
            "• reading — Читаю сейчас\n"
            "• completed — Прочитано\n"
            "• dropped — Брошено\n\n"
            "*Пример:*\n"
            "/add 123 reading",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        status = context.args[1] if len(context.args) > 1 else "planned"
        
        if status not in ['planned', 'reading', 'completed', 'dropped']:
            await update.message.reply_text(
                "❌ *Неверный статус.* Используйте: planned, reading, completed, dropped",
                parse_mode='Markdown'
            )
            return
        
        # Проверяем, существует ли книга
        book_info = book_db.get_book(book_id)
        if not book_info:
            await update.message.reply_text(
                f"❌ *Книга с ID {book_id} не найдена.*\n"
                "Используйте /search чтобы найти книги.",
                parse_mode='Markdown'
            )
            return
        
        # Добавляем книгу
        if user_manager.add_book(user_id, book_id, status):
            status_emoji = {
                'planned': '📅',
                'reading': '📖', 
                'completed': '✅',
                'dropped': '❌'
            }
            await update.message.reply_text(
                f"{status_emoji[status]} *Книга добавлена!*\n\n"
                f"*{book_info['title']}*\n"
                f"Автор: {book_info['author']}\n"
                f"Статус: {status}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ *Не удалось добавить книгу.*",
                parse_mode='Markdown'
            )
    
    except ValueError:
        await update.message.reply_text(
            "❌ *ID книги должен быть числом.*",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in add_book: {e}")
        await update.message.reply_text(
            "❌ *Произошла ошибка.* Попробуйте еще раз.",
            parse_mode='Markdown'
        )

async def search_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск книг в каталоге."""
    if not context.args:
        await update.message.reply_text(
            "🔍 *Использование:* /search <название или автор>\n\n"
            "*Примеры:*\n"
            "/search Гарри Поттер\n"
            "/search Достоевский",
            parse_mode='Markdown'
        )
        return
    
    query = " ".join(context.args)
    books = book_db.search_books(query)
    
    if not books:
        await update.message.reply_text(
            f"🔍 *По запросу '{query}' ничего не найдено.*",
            parse_mode='Markdown'
        )
        return
    
    # Формируем ответ
    message_lines = [f"🔍 *Найдено книг:* {len(books)}\n"]
    
    for i, book in enumerate(books[:10], 1):  # Показываем первые 10
        genre = f" ({book['genre']})" if book.get('genre') else ""
        desc = book.get('description', '')[:80]
        if desc:
            desc = f"\n   {desc}..."
        
        message_lines.append(
            f"{i}. *{book['title']}* - {book['author']}{genre}\n"
            f"   ID: {book['id']}{desc}"
        )
    
    message_lines.append("\n📝 *Чтобы добавить книгу:* /add <id>")
    
    await update.message.reply_text(
        "\n".join(message_lines),
        parse_mode='Markdown'
    )

async def rate_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Оценивает книгу."""
    if len(context.args) != 2:
        await update.message.reply_text(
            "⭐ *Использование:* /rate <id_книги> <оценка_1-5>\n\n"
            "*Пример:*\n"
            "/rate 123 5",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        rating = int(context.args[1])
        
        if rating < 1 or rating > 5:
            await update.message.reply_text(
                "❌ *Оценка должна быть от 1 до 5.*",
                parse_mode='Markdown'
            )
            return
        
        # Проверяем, есть ли книга у пользователя
        if not user_manager.has_book(user_id, book_id):
            await update.message.reply_text(
                "❌ *У вас нет этой книги в коллекции.*\n"
                "Сначала добавьте книгу через /add",
                parse_mode='Markdown'
            )
            return
        
        # Ставим оценку
        if user_manager.rate_book(user_id, book_id, rating):
            book_info = book_db.get_book(book_id)
            title = book_info['title'] if book_info else f"Книга #{book_id}"
            
            stars = "⭐" * rating
            await update.message.reply_text(
                f"⭐ *Оценка поставлена!*\n\n"
                f"*{title}*\n"
                f"Ваша оценка: {stars} ({rating}/5)",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ *Не удалось поставить оценку.*",
                parse_mode='Markdown'
            )
    
    except ValueError:
        await update.message.reply_text(
            "❌ *ID книги и оценка должны быть числами.*",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in rate_book: {e}")
        await update.message.reply_text(
            "❌ *Произошла ошибка.*",
            parse_mode='Markdown'
        )

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику."""
    user_id = update.effective_user.id
    stats = user_manager.get_stats(user_id)
    
    message = (
        f"📊 *Ваша статистика чтения:*\n\n"
        f"📚 Всего книг: {stats['total']}\n"
        f"📅 Запланировано: {stats['planned']}\n"
        f"📖 Читаю сейчас: {stats['reading']}\n"
        f"✅ Прочитано: {stats['completed']}\n"
        f"❌ Брошено: {stats['dropped']}\n"
    )
    
    if stats['avg_rating'] > 0:
        message += f"\n⭐ Средняя оценка: {stats['avg_rating']}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def remove_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет книгу из коллекции."""
    if not context.args:
        await update.message.reply_text(
            "🗑️ *Использование:* /remove <id_книги>\n\n"
            "*Пример:*\n"
            "/remove 123",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        if user_manager.remove_book(user_id, book_id):
            await update.message.reply_text(
                "✅ *Книга удалена из вашей коллекции.*",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ *Книга не найдена в вашей коллекции.*",
                parse_mode='Markdown'
            )
    
    except ValueError:
        await update.message.reply_text(
            "❌ *ID книги должен быть числом.*",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in remove_book: {e}")
        await update.message.reply_text(
            "❌ *Произошла ошибка.*",
            parse_mode='Markdown'
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку."""
    help_text = (
        "📚 *BookBot - помощник для учета книг*\n\n"
        "*Основные команды:*\n"
        "• /start - Начать работу с ботом\n"
        "• /mybooks - Мои книги\n"
        "• /add <id> [статус] - Добавить книгу\n"
        "• /search <запрос> - Найти книгу\n"
        "• /rate <id> <1-5> - Оценить книгу\n"
        "• /remove <id> - Удалить книгу\n"
        "• /stats - Статистика\n"
        "• /help - Эта справка\n\n"
        "*Статусы книг:*\n"
        "• planned - Запланировано\n"
        "• reading - Читаю сейчас\n"
        "• completed - Прочитано\n"
        "• dropped - Брошено\n\n"
        "*Как начать:*\n"
        "1. Найдите книгу: /search Гарри Поттер\n"
        "2. Добавьте книгу: /add 123\n"
        "3. Следите за прогрессом!\n\n"
        "Просто напишите название книги для поиска!"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (автоматический поиск)."""
    text = update.message.text.strip()
    
    # Игнорируем короткие сообщения и команды
    if len(text) < 2 or text.startswith('/'):
        return
    
    # Выполняем поиск
    books = book_db.search_books(text, limit=5)
    
    if not books:
        await update.message.reply_text(
            f"🔍 *По запросу '{text}' ничего не найдено.*\n"
            "Попробуйте другой запрос или используйте /search",
            parse_mode='Markdown'
        )
        return
    
    # Показываем результаты
    message_lines = [f"🔍 *Результаты поиска по '{text}':*\n"]
    
    for i, book in enumerate(books, 1):
        message_lines.append(
            f"{i}. *{book['title']}* - {book['author']}\n"
            f"   ID: {book['id']}"
        )
    
    message_lines.append("\n📝 *Чтобы добавить книгу:* /add <id>")
    
    await update.message.reply_text(
        "\n".join(message_lines),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик инлайн-кнопок."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "mybooks":
        stats = user_manager.get_stats(user_id)
        if stats['total'] == 0:
            await query.edit_message_text(
                "📭 *У вас пока нет книг в коллекции.*\n\n"
                "Используйте /search чтобы найти книги.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"📚 *В вашей коллекции {stats['total']} книг.*\n\n"
                f"✅ Прочитано: {stats['completed']}\n"
                f"📖 Читаю сейчас: {stats['reading']}\n\n"
                "Используйте /mybooks для подробного списка.",
                parse_mode='Markdown'
            )
    
    elif query.data == "search":
        await query.edit_message_text(
            "🔍 *Поиск книг*\n\n"
            "Напишите название книги или автора.\n"
            "Или используйте команду /search <запрос>",
            parse_mode='Markdown'
        )
    
    elif query.data == "stats":
        stats = user_manager.get_stats(user_id)
        await query.edit_message_text(
            f"📊 *Ваша статистика:*\n\n"
            f"📚 Всего книг: {stats['total']}\n"
            f"📅 Запланировано: {stats['planned']}\n"
            f"📖 Читаю сейчас: {stats['reading']}\n"
            f"✅ Прочитано: {stats['completed']}\n"
            f"❌ Брошено: {stats['dropped']}",
            parse_mode='Markdown'
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок."""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        error_msg = str(context.error)
        
        if "Timed out" in error_msg:
            await update.message.reply_text(
                "⏰ *Операция заняла слишком много времени.*\n"
                "Попробуйте еще раз.",
                parse_mode='Markdown'
            )
        elif "UNION" in error_msg:
            await update.message.reply_text(
                "❌ *Ошибка в базе данных.*\n"
                "Попробуйте позже.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ *Произошла ошибка.*\n"
                "Попробуйте еще раз.",
                parse_mode='Markdown'
            )
    except:
        pass

def main():
    """Запуск бота."""
    TOKEN = "8443150665:AAGT7hc5gi8JP8MFUmaQQDNhru6VkKc5aj4"
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mybooks", mybooks))
    application.add_handler(CommandHandler("add", add_book))
    application.add_handler(CommandHandler("search", search_books))
    application.add_handler(CommandHandler("rate", rate_book))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("remove", remove_book))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик инлайн-кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_text
    ))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота
    print("🤖 Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
