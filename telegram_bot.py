#!/usr/bin/env python3
"""
telegram_bot.py - Telegram бот для учета книг
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Импортируем наши модули
try:
    from models import UserManager
    from database import db
    print("Модули загружены успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    exit(1)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем менеджеры
user_manager = UserManager()
book_db = db

# ==================== КОМАНДЫ БОТА ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    
    welcome_text = f"""
📚 Привет, {user.first_name}!

Я — BookBot, твой помощник в учёте прочитанных книг.

📖 Основные команды:
/mybooks - Мои книги
/add <id> - Добавить книгу
/search <название> - Найти книгу
/read <id> - Начать читать книгу
/progress <id> <страница> - Обновить прогресс
/finish <id> - Закончить чтение
/rate <id> <1-5> - Оценить книгу
/stats - Статистика
/remove <id> - Удалить книгу
/help - Справка

Просто напиши название книги для поиска!
"""
    
    await update.message.reply_text(welcome_text)

async def mybooks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /mybooks"""
    user_id = update.effective_user.id
    books = user_manager.get_user_books(user_id)
    
    if not books:
        await update.message.reply_text("📭 У вас пока нет книг в коллекции.")
        return
    
    # Группируем книги по статусу
    books_by_status = {'planned': [], 'reading': [], 'completed': [], 'dropped': []}
    
    for book in books:
        books_by_status[book['status']].append(book)
    
    # Формируем сообщение
    message_parts = ["📚 Ваша библиотека:\n"]
    
    status_names = {
        'planned': '📅 Запланировано',
        'reading': '📖 Читаю сейчас',
        'completed': '✅ Прочитано',
        'dropped': '❌ Брошено'
    }
    
    for status, status_books in books_by_status.items():
        if status_books:
            message_parts.append(f"\n{status_names[status]}:")
            for book in status_books[:5]:
                book_info = book_db.get_book(book['book_id'])
                if book_info:
                    title = book_info['title']
                    if status == 'reading' and book.get('current_page'):
                        message_parts.append(f"• {title} - стр. {book['current_page']}")
                    else:
                        rating = f" ⭐ {book['rating']}" if book.get('rating') else ""
                        message_parts.append(f"• {title}{rating}")
    
    await update.message.reply_text("\n".join(message_parts))

async def add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add <id>"""
    if not context.args:
        await update.message.reply_text("📝 Использование: /add <id_книги>")
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        book_info = book_db.get_book(book_id)
        if not book_info:
            await update.message.reply_text(f"❌ Книга с ID {book_id} не найдена.")
            return
        
        if user_manager.add_book(user_id, book_id):
            await update.message.reply_text(
                f"✅ Книга добавлена!\n\n"
                f"📖 {book_info['title']}\n"
                f"👤 {book_info['author']}\n"
                f"📂 Статус: запланировано"
            )
        else:
            await update.message.reply_text("❌ Не удалось добавить книгу.")
    
    except ValueError:
        await update.message.reply_text("❌ ID книги должен быть числом.")

async def search_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /search <запрос>"""
    if not context.args:
        await update.message.reply_text("🔍 Использование: /search <запрос>")
        return
    
    query = " ".join(context.args)
    books = book_db.search_books(query)
    
    if not books:
        await update.message.reply_text(f"🔍 По запросу '{query}' ничего не найдено.")
        return
    
    # Формируем ответ
    message_parts = [f"🔍 Найдено книг: {len(books)}\n"]
    
    for i, book in enumerate(books[:10], 1):
        genre = f" ({book['genre']})" if book.get('genre') else ""
        message_parts.append(f"{i}. {book['title']} - {book['author']}{genre}")
        message_parts.append(f"   📚 ID: {book['id']}")
    
    message_parts.append("\n📝 Чтобы добавить книгу: /add <id>")
    
    await update.message.reply_text("\n".join(message_parts))

async def start_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /read <id> - начать читать"""
    if not context.args:
        await update.message.reply_text("📖 Использование: /read <id_книги>")
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        if not user_manager.has_book(user_id, book_id):
            await update.message.reply_text("❌ У вас нет этой книги в коллекции.")
            return
        
        if user_manager.update_book_status(user_id, book_id, "reading"):
            book_info = book_db.get_book(book_id)
            await update.message.reply_text(
                f"📖 Начинаем читать!\n\n"
                f"{book_info['title']}\n"
                f"Автор: {book_info['author']}"
            )
        else:
            await update.message.reply_text("❌ Не удалось начать чтение.")
    
    except ValueError:
        await update.message.reply_text("❌ ID книги должен быть числом.")

async def update_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /progress <id> <страница>"""
    if len(context.args) != 2:
        await update.message.reply_text("📊 Использование: /progress <id> <страница>")
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        current_page = int(context.args[1])
        
        book_user_info = user_manager.get_book_info(user_id, book_id)
        if not book_user_info:
            await update.message.reply_text("❌ У вас нет этой книги в коллекции.")
            return
        
        if book_user_info['status'] != 'reading':
            await update.message.reply_text("❌ Эту книгу вы сейчас не читаете.")
            return
        
        if user_manager.update_progress(user_id, book_id, current_page):
            book_info = book_db.get_book(book_id)
            progress = (current_page / book_info['total_pages']) * 100 if book_info['total_pages'] > 0 else 0
            
            await update.message.reply_text(
                f"📖 Прогресс обновлен!\n"
                f"Страница: {current_page}\n"
                f"Прогресс: {progress:.1f}%"
            )
        else:
            await update.message.reply_text("❌ Не удалось обновить прогресс.")
    
    except ValueError:
        await update.message.reply_text("❌ ID книги и номер страницы должны быть числами.")

async def finish_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /finish <id>"""
    if not context.args:
        await update.message.reply_text("✅ Использование: /finish <id_книги>")
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        if not user_manager.has_book(user_id, book_id):
            await update.message.reply_text("❌ У вас нет этой книги в коллекции.")
            return
        
        if user_manager.update_book_status(user_id, book_id, "completed"):
            book_info = book_db.get_book(book_id)
            await update.message.reply_text(
                f"🎉 Поздравляем с прочтением!\n\n"
                f"{book_info['title']}\n"
                f"Автор: {book_info['author']}"
            )
        else:
            await update.message.reply_text("❌ Не удалось отметить как прочитанную.")
    
    except ValueError:
        await update.message.reply_text("❌ ID книги должен быть числом.")

async def rate_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rate <id> <оценка>"""
    if len(context.args) != 2:
        await update.message.reply_text("⭐ Использование: /rate <id> <оценка_1-5>")
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        rating = int(context.args[1])
        
        if rating < 1 or rating > 5:
            await update.message.reply_text("❌ Оценка должна быть от 1 до 5.")
            return
        
        if not user_manager.has_book(user_id, book_id):
            await update.message.reply_text("❌ У вас нет этой книги в коллекции.")
            return
        
        if user_manager.rate_book(user_id, book_id, rating):
            book_info = book_db.get_book(book_id)
            stars = "⭐" * rating
            await update.message.reply_text(f"✅ Оценка поставлена!\n\n{book_info['title']}\n{stars} ({rating}/5)")
        else:
            await update.message.reply_text("❌ Не удалось поставить оценку.")
    
    except ValueError:
        await update.message.reply_text("❌ ID книги и оценка должны быть числами.")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats"""
    user_id = update.effective_user.id
    stats = user_manager.get_stats(user_id)
    
    message = f"""
📊 Ваша статистика чтения:

📚 Всего книг: {stats['total']}
📅 Запланировано: {stats['planned']}
📖 Читаю сейчас: {stats['reading']}
✅ Прочитано: {stats['completed']}
❌ Брошено: {stats['dropped']}
"""
    
    if stats.get('avg_rating', 0) > 0:
        message += f"\n⭐ Средняя оценка: {stats['avg_rating']}"
    
    await update.message.reply_text(message)

async def remove_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /remove <id>"""
    if not context.args:
        await update.message.reply_text("🗑️ Использование: /remove <id_книги>")
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        if user_manager.remove_book(user_id, book_id):
            await update.message.reply_text("✅ Книга удалена из вашей коллекции.")
        else:
            await update.message.reply_text("❌ Книга не найдена в вашей коллекции.")
    
    except ValueError:
        await update.message.reply_text("❌ ID книги должен быть числом.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
📚 BookBot - помощник для учета книг

📖 Основные команды:
/start - Начать работу с ботом
/mybooks - Мои книги
/add <id> - Добавить книгу
/search <запрос> - Найти книгу
/read <id> - Начать читать книгу
/progress <id> <страница> - Обновить прогресс
/finish <id> - Закончить чтение книги
/rate <id> <1-5> - Оценить книгу
/remove <id> - Удалить книгу
/stats - Статистика
/help - Эта справка

📖 Процесс чтения:
1. Найдите книгу: /search Гарри Поттер
2. Добавьте книгу: /add 4
3. Начните читать: /read 4
4. Обновляйте прогресс: /progress 4 150
5. Закончите чтение: /finish 4
6. Оцените книгу: /rate 4 5
"""
    
    await update.message.reply_text(help_text)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text.strip()
    
    if len(text) < 2 or text.startswith('/'):
        return
    
    books = book_db.search_books(text, limit=5)
    
    if not books:
        await update.message.reply_text(f"🔍 По запросу '{text}' ничего не найдено.")
        return
    
    message_parts = [f"🔍 Найдено по запросу '{text}':\n"]
    
    for i, book in enumerate(books, 1):
        message_parts.append(f"{i}. {book['title']} - {book['author']}")
        message_parts.append(f"   📚 ID: {book['id']}")
    
    message_parts.append("\n📝 Чтобы добавить книгу: /add <id>")
    
    await update.message.reply_text("\n".join(message_parts))

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    
    try:
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")
    except:
        pass

def main():
    """Запуск бота"""
    print(" Запуск BookBot...")
    
    # ⚠️ ВАЖНО: Токен уже правильный, проверен через curl
    TOKEN = "8371793740:AAGyHz10Ro6JabxomkyjDGsjWhNaf3SUeMI"
    
    print(f" Токен: {TOKEN[:15]}...")
    
    # Создаем приложение
    try:
        application = Application.builder().token(TOKEN).build()
        print(" Приложение создано")
    except Exception as e:
        print(f"❌ Ошибка создания приложения: {e}")
        return
    
    # Добавляем обработчики команд
    handlers = [
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
    
    for command, handler in handlers:
        application.add_handler(CommandHandler(command, handler))
        print(f" Добавлена команда /{command}")
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
 
    
    application.run_polling()

if __name__ == '__main__':
    main()
