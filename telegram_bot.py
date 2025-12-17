#!/usr/bin/env python3
"""
telegram_bot.py - Telegram бот для учета книг
Интерфейс для работы с моделями и базой данных
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from models import UserManager
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем менеджеры
user_manager = UserManager()  # Для данных пользователей в памяти
book_db = db                  # Для каталога книг в SQLite

# ==================== КОМАНДЫ БОТА ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

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

Просто начни вводить название книги для поиска!
"""
    
    keyboard = [
        [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
        [InlineKeyboardButton("🔍 Поиск книг", callback_data="search")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def mybooks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /mybooks - показывает книги пользователя"""
    user_id = update.effective_user.id
    books = user_manager.get_user_books(user_id)
    
    if not books:
        await update.message.reply_text(
            "📭 У вас пока нет книг в коллекции.\n"
            "Используйте /add чтобы добавить книгу."
        )
        return
    
    # Группируем книги по статусу
    books_by_status = {}
    for status in ['planned', 'reading', 'completed', 'dropped']:
        status_books = user_manager.get_user_books(user_id, status)
        if status_books:
            books_by_status[status] = status_books
    
    # Формируем сообщение
    status_names = {
        'planned': '📅 Запланировано',
        'reading': '📖 Читаю сейчас',
        'completed': '✅ Прочитано',
        'dropped': '❌ Брошено'
    }
    
    message_lines = [f"📚 Ваша библиотека:\n"]
    
    for status, books_list in books_by_status.items():
        message_lines.append(f"\n{status_names[status]} ({len(books_list)}):")
        for i, book in enumerate(books_list[:10], 1):
            book_info = book_db.get_book(book['book_id'])
            if book_info:
                title = book_info['title']
                
                # Для читаемых книг показываем прогресс
                if status == 'reading' and book['current_page'] > 0:
                    progress = (book['current_page'] / book_info['total_pages']) * 100
                    message_lines.append(f"{i}. {title} - стр. {book['current_page']} ({progress:.1f}%)")
                else:
                    rating = f" ⭐ {book['rating']}" if book['rating'] else ""
                    message_lines.append(f"{i}. {title}{rating}")
    
    stats = user_manager.get_stats(user_id)
    if stats['avg_rating'] > 0:
        message_lines.append(f"\n📊 Средний рейтинг: {stats['avg_rating']}")
    
    await update.message.reply_text("\n".join(message_lines))

async def add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add <id> - добавляет книгу"""
    if not context.args:
        await update.message.reply_text(
            "📝 Использование: /add <id_книги> [статус]\n"
            "Статусы: planned, reading, completed, dropped\n"
            "Пример: /add 123 reading"
        )
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        status = context.args[1] if len(context.args) > 1 else "planned"
        
        if status not in ['planned', 'reading', 'completed', 'dropped']:
            await update.message.reply_text(
                "❌ Неверный статус. Используйте: planned, reading, completed, dropped"
            )
            return
        
        # Проверяем, есть ли книга в базе
        book_info = book_db.get_book(book_id)
        if not book_info:
            await update.message.reply_text(
                f"❌ Книга с ID {book_id} не найдена в каталоге.\n"
                "Сначала найдите книгу через /search"
            )
            return
        
        # Добавляем книгу
        if user_manager.add_book(user_id, book_id, status):
            status_texts = {
                'planned': 'запланирована',
                'reading': 'добавлена в читаю',
                'completed': 'отмечена как прочитанная',
                'dropped': 'отмечена как брошенная'
            }
            await update.message.reply_text(
                f"✅ Книга '{book_info['title']}' {status_texts[status]}!"
            )
        else:
            await update.message.reply_text("❌ Не удалось добавить книгу.")
    
    except ValueError:
        await update.message.reply_text("❌ ID книги должен быть числом.")
    except Exception as e:
        logger.error(f"Error adding book: {e}")
        await update.message.reply_text("❌ Произошла ошибка.")

async def start_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /read <id> - начать читать книгу"""
    if not context.args:
        await update.message.reply_text("📖 Использование: /read <id_книги>\nПример: /read 1")
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        # Проверяем, есть ли книга у пользователя
        if not user_manager.has_book(user_id, book_id):
            await update.message.reply_text("❌ У вас нет этой книги в коллекции.")
            return
        
        # Меняем статус на "читаю"
        if user_manager.update_book_status(user_id, book_id, "reading"):
            book_info = book_db.get_book(book_id)
            await update.message.reply_text(
                f"📖 Начинаем читать!\n\n"
                f"{book_info['title']}\n"
                f"Автор: {book_info['author']}\n"
                f"Всего страниц: {book_info['total_pages']}\n\n"
                f"Чтобы обновить прогресс: /progress {book_id} <номер_страницы>"
            )
        else:
            await update.message.reply_text("❌ Не удалось начать чтение.")
    
    except ValueError:
        await update.message.reply_text("❌ ID книги должен быть числом.")

async def update_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /progress <id> <страница> - обновить прогресс чтения"""
    if len(context.args) != 2:
        await update.message.reply_text("📊 Использование: /progress <id_книги> <номер_страницы>\nПример: /progress 1 150")
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        current_page = int(context.args[1])
        
        # Проверяем, есть ли книга и читается ли она
        book_user_info = user_manager.get_book_info(user_id, book_id)
        if not book_user_info:
            await update.message.reply_text("❌ У вас нет этой книги в коллекции.")
            return
        
        if book_user_info['status'] != 'reading':
            await update.message.reply_text("❌ Эту книгу вы сейчас не читаете.")
            return
        
        book_info = book_db.get_book(book_id)
        
        # Проверяем, что страница не больше общего количества
        if current_page > book_info['total_pages']:
            await update.message.reply_text(f"❌ В этой книге только {book_info['total_pages']} страниц!")
            return
        
        # Обновляем прогресс
        if user_manager.update_progress(user_id, book_id, current_page):
            progress = (current_page / book_info['total_pages']) * 100
            
            if progress >= 100:
                message = f"🎉 Поздравляем! Вы прочитали книгу!\n\n"
                message += f"{book_info['title']}\n"
                message += f"Прогресс: {current_page}/{book_info['total_pages']} страниц (100%)\n\n"
                message += f"Чтобы отметить как прочитанную: /finish {book_id}"
            else:
                message = f"📖 Прогресс обновлен!\n\n"
                message += f"{book_info['title']}\n"
                message += f"Страница: {current_page} из {book_info['total_pages']}\n"
                message += f"Прогресс: {progress:.1f}%"
            
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ Не удалось обновить прогресс.")
    
    except ValueError:
        await update.message.reply_text("❌ ID книги и номер страницы должны быть числами.")

async def finish_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /finish <id> - закончить чтение книги"""
    if not context.args:
        await update.message.reply_text("✅ Использование: /finish <id_книги>\nПример: /finish 1")
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        # Проверяем, есть ли книга
        if not user_manager.has_book(user_id, book_id):
            await update.message.reply_text("❌ У вас нет этой книги в коллекции.")
            return
        
        # Меняем статус на "прочитано"
        if user_manager.update_book_status(user_id, book_id, "completed"):
            book_info = book_db.get_book(book_id)
            book_user_info = user_manager.get_book_info(user_id, book_id)
            
            message = f"🎉 Поздравляем с прочтением!\n\n"
            message += f"{book_info['title']}\n"
            message += f"Автор: {book_info['author']}\n"
            
            if book_user_info['current_page'] > 0:
                message += f"Прочитано страниц: {book_user_info['current_page']}\n"
            
            message += f"\nТеперь можете оценить книгу: /rate {book_id} <1-5>"
            
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ Не удалось отметить как прочитанную.")
    
    except ValueError:
        await update.message.reply_text("❌ ID книги должен быть числом.")

async def search_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /search <запрос> - поиск книг"""
    if not context.args:
        await update.message.reply_text(
            "🔍 Использование: /search <название или автор>\n"
            "Пример: /search Гарри Поттер"
        )
        return
    
    query = " ".join(context.args)
    books = book_db.search_books(query)
    
    if not books:
        await update.message.reply_text(f"📭 По запросу '{query}' ничего не найдено.")
        return
    
    # Формируем список книг
    message_lines = [f"📚 Найдено книг: {len(books)}\n"]
    
    for i, book in enumerate(books[:15], 1):
        genre = f" ({book['genre']})" if book.get('genre') else ""
        message_lines.append(
            f"{i}. {book['title']} - {book['author']}{genre}\n"
            f"   ID: {book['id']}"
        )
    
    message = "\n".join(message_lines)
    
    # Если сообщение слишком длинное, разбиваем на части
    if len(message) > 4000:
        parts = []
        current_part = []
        current_length = 0
        
        for line in message_lines:
            if current_length + len(line) + 1 > 4000:
                parts.append("\n".join(current_part))
                current_part = [line]
                current_length = len(line) + 1
            else:
                current_part.append(line)
                current_length += len(line) + 1
        
        if current_part:
            parts.append("\n".join(current_part))
        
        for part in parts:
            await update.message.reply_text(part)
    else:
        await update.message.reply_text(message)

async def rate_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rate <id> <оценка> - оценить книгу"""
    if len(context.args) != 2:
        await update.message.reply_text(
            "⭐ Использование: /rate <id_книги> <оценка_1-5>\n"
            "Пример: /rate 123 5"
        )
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        rating = int(context.args[1])
        
        if rating < 1 or rating > 5:
            await update.message.reply_text("❌ Оценка должна быть от 1 до 5.")
            return
        
        # Проверяем, есть ли книга у пользователя
        if not user_manager.has_book(user_id, book_id):
            await update.message.reply_text(
                "❌ У вас нет этой книги в коллекции.\n"
                "Сначала добавьте книгу через /add"
            )
            return
        
        # Ставим оценку
        if user_manager.rate_book(user_id, book_id, rating):
            book_info = book_db.get_book(book_id)
            title = book_info['title'] if book_info else f"Книга #{book_id}"
            await update.message.reply_text(f"✅ Вы поставили {rating}⭐ книге '{title}'")
        else:
            await update.message.reply_text("❌ Не удалось поставить оценку.")
    
    except ValueError:
        await update.message.reply_text("❌ ID книги и оценка должны быть числами.")
    except Exception as e:
        logger.error(f"Error rating book: {e}")
        await update.message.reply_text("❌ Произошла ошибка.")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - статистика чтения"""
    user_id = update.effective_user.id
    stats = user_manager.get_stats(user_id)
    
    message = (
        f"📊 Ваша статистика чтения:\n\n"
        f"📚 Всего книг: {stats['total']}\n"
        f"📅 Запланировано: {stats['planned']}\n"
        f"📖 Читаю сейчас: {stats['reading']}\n"
        f"✅ Прочитано: {stats['completed']}\n"
        f"❌ Брошено: {stats['dropped']}\n"
    )
    
    if stats['total_pages'] > 0:
        message += f"📖 Всего прочитано страниц: {stats['total_pages']}\n"
    
    if stats['avg_rating'] > 0:
        message += f"\n⭐ Средний рейтинг: {stats['avg_rating']}"
    
    await update.message.reply_text(message)

async def remove_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /remove <id> - удалить книгу"""
    if not context.args:
        await update.message.reply_text(
            "🗑️ Использование: /remove <id_книги>\n"
            "Пример: /remove 123"
        )
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        if user_manager.remove_book(user_id, book_id):
            await update.message.reply_text(f"✅ Книга удалена из вашей коллекции.")
        else:
            await update.message.reply_text("❌ Книга не найдена в вашей коллекции.")
    
    except ValueError:
        await update.message.reply_text("❌ ID книги должен быть числом.")
    except Exception as e:
        logger.error(f"Error removing book: {e}")
        await update.message.reply_text("❌ Произошла ошибка.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - помощь"""
    help_text = (
        "📚 *BookBot - помощник для учета книг*\n\n"
        "*Основные команды:*\n"
        "/start - Начать работу с ботом\n"
        "/mybooks - Показать мои книги\n"
        "/add <id> [статус] - Добавить книгу\n"
        "/search <запрос> - Найти книгу\n"
        "/read <id> - Начать читать книгу\n"
        "/progress <id> <страница> - Обновить прогресс чтения\n"
        "/finish <id> - Закончить чтение книги\n"
        "/rate <id> <1-5> - Оценить книгу\n"
        "/remove <id> - Удалить книгу\n"
        "/stats - Показать статистику\n"
        "/help - Эта справка\n\n"
        "*Статусы книг:*\n"
        "• planned - Запланировано\n"
        "• reading - Читаю сейчас\n"
        "• completed - Прочитано\n"
        "• dropped - Брошено\n\n"
        "Просто напишите название книги для поиска!"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик инлайн-кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "mybooks":
        stats = user_manager.get_stats(user_id)
        if stats['total'] == 0:
            await query.edit_message_text(
                "📭 У вас пока нет книг в коллекции.\n"
                "Используйте /add чтобы добавить книгу."
            )
        else:
            await query.edit_message_text(
                f"📚 В вашей коллекции {stats['total']} книг.\n"
                f"✅ Прочитано: {stats['completed']}\n"
                f"📖 Читаю сейчас: {stats['reading']}\n\n"
                "Используйте /mybooks для подробного списка."
            )
    
    elif query.data == "search":
        await query.edit_message_text(
            "🔍 Для поиска книг используйте команду /search\n"
            "Пример: /search Гарри Поттер\n\n"
            "Или просто напишите название книги:"
        )
    
    elif query.data == "stats":
        stats = user_manager.get_stats(user_id)
        await query.edit_message_text(
            f"📊 Ваша статистика:\n\n"
            f"📚 Всего книг: {stats['total']}\n"
            f"📅 Запланировано: {stats['planned']}\n"
            f"📖 Читаю сейчас: {stats['reading']}\n"
            f"✅ Прочитано: {stats['completed']}\n"
            f"❌ Брошено: {stats['dropped']}"
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений для поиска книг"""
    text = update.message.text.strip()
    
    if len(text) < 2:
        return
    
    # Если сообщение похоже на поисковый запрос
    books = book_db.search_books(text)
    
    if not books:
        await update.message.reply_text(
            f"📭 По запросу '{text}' ничего не найдено.\n"
            "Попробуйте другой запрос или используйте /search <запрос>"
        )
        return
    
    # Показываем первые 5 результатов
    message_lines = [f"🔍 Результаты поиска по '{text}':\n"]
    
    for i, book in enumerate(books[:5], 1):
        message_lines.append(f"{i}. {book['title']} - {book['author']}")
        message_lines.append(f"   ID: {book['id']}\n")
    
    message_lines.append("Чтобы добавить книгу, используйте /add <id>")
    
    await update.message.reply_text("\n".join(message_lines))

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")
    except:
        pass

def main():
    """Запуск бота"""
    # ВАЖНО: Вставьте свой токен сюда!
    TOKEN = "8371793740:AAGyHz10Ro6JabxomkyjDGsjWhNaf3SUeMI"
    
    # Проверка токена
    if "ВАШ_ТОКЕН" in TOKEN or len(TOKEN) < 30:
        print("ОШИБКА: Вставьте свой токен от @BotFather!")
        print("   Получите токен: 1) Найти @BotFather 2) /newbot 3) Скопировать токен")
        return
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mybooks", mybooks
