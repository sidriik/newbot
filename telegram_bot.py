#!/usr/bin/env python3
"""
telegram_bot.py - Telegram бот для учета книг с интерфейсом кнопок
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Импортируем наши модули
from models import UserManager
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем менеджеры
user_manager = UserManager()
book_db = db

# ==================== КОМАНДЫ БОТА С КНОПКАМИ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start с кнопками"""
    user = update.effective_user
    
    welcome_text = f"""👋 Привет, {user.first_name}!

Я — BookBot, помогу тебе вести список книг.

Выбери действие:"""
    
    # Создаем клавиатуру с кнопками
    keyboard = [
        [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
        [InlineKeyboardButton("🔍 Найти книгу", callback_data="search")],
        [InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book")],
        [InlineKeyboardButton("📖 Начать читать", callback_data="start_reading")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("⭐ Оценить книгу", callback_data="rate_book")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# ==================== ОБРАБОТЧИКИ КНОПОК ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Обработка разных кнопок
    if query.data == "mybooks":
        await show_my_books(query, user_id)
    
    elif query.data == "search":
        await search_books_menu(query)
    
    elif query.data == "add_book":
        await add_book_menu(query)
    
    elif query.data == "start_reading":
        await start_reading_menu(query, user_id)
    
    elif query.data == "stats":
        await show_stats_menu(query, user_id)
    
    elif query.data == "rate_book":
        await rate_book_menu(query, user_id)
    
    elif query.data == "help":
        await help_menu(query)
    
    elif query.data.startswith("search_"):
        search_query = query.data.replace("search_", "")
        await perform_search(query, search_query)
    
    elif query.data.startswith("add_"):
        book_id = int(query.data.replace("add_", ""))
        await add_book_to_collection(query, user_id, book_id)
    
    elif query.data.startswith("read_"):
        book_id = int(query.data.replace("read_", ""))
        await start_reading_book(query, user_id, book_id)
    
    elif query.data.startswith("rate_"):
        parts = query.data.replace("rate_", "").split("_")
        if len(parts) == 2:
            book_id = int(parts[0])
            rating = int(parts[1])
            await rate_book_action(query, user_id, book_id, rating)

async def show_my_books(query, user_id):
    """Показывает книги пользователя"""
    books = user_manager.get_user_books(user_id)
    
    if not books:
        await query.edit_message_text(
            text="📭 У вас пока нет книг в коллекции.",
            reply_markup=get_main_keyboard()
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
    
    message_lines = ["📚 Ваша библиотека:\n"]
    
    for status, books_list in books_by_status.items():
        message_lines.append(f"\n{status_names[status]} ({len(books_list)}):")
        for i, book in enumerate(books_list[:5], 1):
            book_info = book_db.get_book(book['book_id'])
            if book_info:
                title = book_info['title']
                
                # Создаем кнопки для каждой книги
                if status == 'planned':
                    message_lines.append(f"{i}. {title}")
                elif status == 'reading':
                    progress = (book['current_page'] / book_info['total_pages']) * 100 if book['current_page'] > 0 else 0
                    message_lines.append(f"{i}. {title} - стр. {book['current_page']} ({progress:.1f}%)")
                else:
                    rating = f" ⭐ {book['rating']}" if book['rating'] else ""
                    message_lines.append(f"{i}. {title}{rating}")
    
    # Кнопки действий
    keyboard = [
        [InlineKeyboardButton("🔍 Найти книгу", callback_data="search")],
        [InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        text="\n".join(message_lines),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def search_books_menu(query):
    """Меню поиска книг"""
    keyboard = [
        [InlineKeyboardButton("📚 Классика", callback_data="search_классика")],
        [InlineKeyboardButton("🧙 Фэнтези", callback_data="search_фэнтези")],
        [InlineKeyboardButton("💑 Роман", callback_data="search_роман")],
        [InlineKeyboardButton("🔍 Поиск по названию", callback_data="search_input")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        text="🔍 Выберите жанр или поиск по названию:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def perform_search(query, search_query):
    """Выполняет поиск книг"""
    if search_query == "input":
        await query.edit_message_text(
            text="📝 Введите название книги или автора:",
            reply_markup=get_back_keyboard()
        )
        return
    
    books = book_db.search_books(search_query)
    
    if not books:
        keyboard = [
            [InlineKeyboardButton("🔍 Попробовать другой запрос", callback_data="search")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text=f"📭 По запросу '{search_query}' ничего не найдено.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Формируем сообщение с кнопками для добавления
    message_lines = [f"🔍 Найдено книг: {len(books)}\n"]
    
    keyboard_buttons = []
    for i, book in enumerate(books[:5], 1):
        genre = f" ({book['genre']})" if book['genre'] else ""
        message_lines.append(f"\n{i}. {book['title']} - {book['author']}{genre}")
        
        # Кнопка для добавления книги
        keyboard_buttons.append([
            InlineKeyboardButton(f"➕ Добавить '{book['title'][:15]}...'", callback_data=f"add_{book['id']}")
        ])
    
    # Кнопки навигации
    keyboard_buttons.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="search")])
    keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    
    await query.edit_message_text(
        text="\n".join(message_lines),
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )

async def add_book_menu(query):
    """Меню добавления книги"""
    # Популярные книги для быстрого добавления
    popular_books = [
        (1, "Преступление и наказание", "Достоевский"),
        (4, "Гарри Поттер", "Роулинг"),
        (2, "Мастер и Маргарита", "Булгаков"),
        (3, "1984", "Оруэлл"),
        (6, "Маленький принц", "Сент-Экзюпери")
    ]
    
    keyboard_buttons = []
    for book_id, title, author in popular_books:
        keyboard_buttons.append([
            InlineKeyboardButton(f"📖 {title[:20]}", callback_data=f"add_{book_id}")
        ])
    
    keyboard_buttons.append([InlineKeyboardButton("🔍 Найти другую книгу", callback_data="search")])
    keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    
    await query.edit_message_text(
        text="📚 Выберите книгу для добавления:",
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )

async def add_book_to_collection(query, user_id, book_id):
    """Добавляет книгу в коллекцию"""
    book_info = book_db.get_book(book_id)
    
    if not book_info:
        await query.edit_message_text(
            text="❌ Книга не найдена.",
            reply_markup=get_back_keyboard()
        )
        return
    
    if user_manager.add_book(user_id, book_id, "planned"):
        keyboard = [
            [InlineKeyboardButton("📖 Начать читать", callback_data=f"read_{book_id}")],
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton("➕ Добавить еще", callback_data="add_book")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text=f"✅ Книга добавлена!\n\n"
                 f"📖 {book_info['title']}\n"
                 f"👤 {book_info['author']}\n"
                 f"📄 Страниц: {book_info['total_pages']}\n"
                 f"📂 Статус: Запланировано",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text(
            text="❌ Не удалось добавить книгу.",
            reply_markup=get_back_keyboard()
        )

async def start_reading_menu(query, user_id):
    """Меню начала чтения"""
    planned_books = user_manager.get_user_books(user_id, "planned")
    
    if not planned_books:
        keyboard = [
            [InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book")],
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text="📭 У вас нет запланированных книг.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Кнопки для каждой запланированной книги
    keyboard_buttons = []
    for book in planned_books[:5]:
        book_info = book_db.get_book(book['book_id'])
        if book_info:
            keyboard_buttons.append([
                InlineKeyboardButton(f"📖 {book_info['title'][:20]}", callback_data=f"read_{book['book_id']}")
            ])
    
    keyboard_buttons.append([InlineKeyboardButton("📚 Все мои книги", callback_data="mybooks")])
    keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    
    await query.edit_message_text(
        text="📚 Выберите книгу для чтения:",
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )

async def start_reading_book(query, user_id, book_id):
    """Начинает чтение книги"""
    if not user_manager.has_book(user_id, book_id):
        await query.edit_message_text(
            text="❌ У вас нет этой книги в коллекции.",
            reply_markup=get_back_keyboard()
        )
        return
    
    if user_manager.update_book_status(user_id, book_id, "reading"):
        book_info = book_db.get_book(book_id)
        
        keyboard = [
            [InlineKeyboardButton("📊 Обновить прогресс", callback_data="update_progress")],
            [InlineKeyboardButton("✅ Закончить чтение", callback_data=f"finish_{book_id}")],
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text=f"📖 Начинаем читать!\n\n"
                 f"{book_info['title']}\n"
                 f"👤 {book_info['author']}\n"
                 f"📄 Всего страниц: {book_info['total_pages']}\n\n"
                 f"Чтобы обновить прогресс, отправьте:\n"
                 f"/progress {book_id} <номер_страницы>",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text(
            text="❌ Не удалось начать чтение.",
            reply_markup=get_back_keyboard()
        )

async def show_stats_menu(query, user_id):
    """Показывает статистику"""
    stats = user_manager.get_stats(user_id)
    
    message = f"""📊 Ваша статистика чтения:

📚 Всего книг: {stats['total']}
📅 Запланировано: {stats['planned']}
📖 Читаю сейчас: {stats['reading']}
✅ Прочитано: {stats['completed']}
❌ Брошено: {stats['dropped']}"""
    
    if stats['avg_rating'] > 0:
        message += f"\n⭐ Средняя оценка: {stats['avg_rating']}"
    
    keyboard = [
        [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
        [InlineKeyboardButton("⭐ Оценить книгу", callback_data="rate_book")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def rate_book_menu(query, user_id):
    """Меню оценки книг"""
    completed_books = user_manager.get_user_books(user_id, "completed")
    
    if not completed_books:
        keyboard = [
            [InlineKeyboardButton("📖 Начать читать", callback_data="start_reading")],
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text="📭 У вас нет прочитанных книг для оценки.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Кнопки для оценки каждой книги
    keyboard_buttons = []
    for book in completed_books[:3]:
        book_info = book_db.get_book(book['book_id'])
        if book_info:
            # Если книга уже оценена, показываем оценку
            if book['rating']:
                keyboard_buttons.append([
                    InlineKeyboardButton(f"⭐ {book['rating']}/5 - {book_info['title'][:15]}", 
                                       callback_data=f"rate_{book['book_id']}_{book['rating']}")
                ])
            else:
                # Кнопки оценки от 1 до 5 звезд
                rating_buttons = []
                for rating in range(1, 6):
                    rating_buttons.append(
                        InlineKeyboardButton(f"{rating}⭐", callback_data=f"rate_{book['book_id']}_{rating}")
                    )
                keyboard_buttons.append(rating_buttons)
                keyboard_buttons.append([
                    InlineKeyboardButton(f"📖 {book_info['title'][:20]}", callback_data="no_action")
                ])
    
    keyboard_buttons.append([InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")])
    keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    
    await query.edit_message_text(
        text="⭐ Оцените прочитанные книги:",
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )

async def rate_book_action(query, user_id, book_id, rating):
    """Ставит оценку книге"""
    if user_manager.rate_book(user_id, book_id, rating):
        book_info = book_db.get_book(book_id)
        
        keyboard = [
            [InlineKeyboardButton("⭐ Оценить другую книгу", callback_data="rate_book")],
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        
        stars = "⭐" * rating
        await query.edit_message_text(
            text=f"✅ Оценка поставлена!\n\n"
                 f"{book_info['title']}\n"
                 f"{stars} ({rating}/5)",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text(
            text="❌ Не удалось поставить оценку.",
            reply_markup=get_back_keyboard()
        )

async def help_menu(query):
    """Меню помощи"""
    help_text = """📚 BookBot - помощник для учета книг

📖 Как пользоваться:
1. Добавьте книгу через "➕ Добавить книгу"
2. Начните чтение через "📖 Начать читать"
3. Обновляйте прогресс командой /progress <id> <страница>
4. Закончив, оцените книгу через "⭐ Оценить книгу"

📋 Команды:
/start - Главное меню
/progress <id> <страница> - Обновить прогресс чтения
/search <запрос> - Поиск книг (текстом)
/add <id> - Добавить книгу по ID

📞 Для связи с разработчиком:
@ваш_логин"""
    
    keyboard = [
        [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
        [InlineKeyboardButton("🔍 Поиск", callback_data="search")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        text=help_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_main_keyboard():
    """Главная клавиатура"""
    keyboard = [
        [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
        [InlineKeyboardButton("🔍 Найти книгу", callback_data="search")],
        [InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book")],
        [InlineKeyboardButton("📖 Начать читать", callback_data="start_reading")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("⭐ Оценить книгу", callback_data="rate_book")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    """Клавиатура "Назад" """
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ТЕКСТОВЫЕ КОМАНДЫ ====================

async def handle_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /progress <id> <страница>"""
    if len(context.args) != 2:
        await update.message.reply_text(
            "Использование: /progress <id_книги> <номер_страницы>\nПример: /progress 1 150"
        )
        return
    
    try:
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
        
        if current_page > book_info['total_pages']:
            await update.message.reply_text(f"В этой книге только {book_info['total_pages']} страниц!")
            return
        
        if user_manager.update_progress(user_id, book_id, current_page):
            progress = (current_page / book_info['total_pages']) * 100
            
            if progress >= 100:
                message = f"🎉 Поздравляем! Вы прочитали книгу!\n\n"
                message += f"{book_info['title']}\n"
                message += f"Прогресс: {current_page}/{book_info['total_pages']} страниц (100%)"
                
                # Автоматически меняем статус на "прочитано"
                user_manager.update_book_status(user_id, book_id, "completed")
                
                keyboard = [
                    [InlineKeyboardButton("⭐ Оценить книгу", callback_data=f"rate_{book_id}")],
                    [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                ]
                
                await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                message = f"📖 Прогресс обновлен!\n\n"
                message += f"{book_info['title']}\n"
                message += f"Страница: {current_page} из {book_info['total_pages']}\n"
                message += f"Прогресс: {progress:.1f}%"
                
                await update.message.reply_text(message, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text("Не удалось обновить прогресс.")
    
    except ValueError:
        await update.message.reply_text("ID книги и номер страницы должны быть числами.")

async def handle_text_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстового поиска"""
    text = update.message.text.strip()
    
    if len(text) < 2:
        return
    
    books = book_db.search_books(text)
    
    if not books:
        await update.message.reply_text(
            f"По запросу '{text}' ничего не найдено.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Формируем сообщение с кнопками
    message_lines = [f"🔍 Найдено по запросу '{text}':\n"]
    
    keyboard_buttons = []
    for i, book in enumerate(books[:5], 1):
        genre = f" ({book['genre']})" if book['genre'] else ""
        message_lines.append(f"\n{i}. {book['title']} - {book['author']}{genre}")
        
        keyboard_buttons.append([
            InlineKeyboardButton(f"➕ Добавить '{book['title'][:15]}...'", callback_data=f"add_{book['id']}")
        ])
    
    keyboard_buttons.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    
    await update.message.reply_text(
        text="\n".join(message_lines),
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )

async def handle_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add <id>"""
    if not context.args:
        await update.message.reply_text(
            "Использование: /add <id_книги>\nПример: /add 1",
            reply_markup=get_main_keyboard()
        )
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        book_info = book_db.get_book(book_id)
        if not book_info:
            await update.message.reply_text(
                f"Книга с ID {book_id} не найдена.",
                reply_markup=get_main_keyboard()
            )
            return
        
        if user_manager.add_book(user_id, book_id, "planned"):
            keyboard = [
                [InlineKeyboardButton("📖 Начать читать", callback_data=f"read_{book_id}")],
                [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
                [InlineKeyboardButton("➕ Добавить еще", callback_data="add_book")],
                [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
            ]
            
            await update.message.reply_text(
                f"✅ Книга добавлена!\n\n"
                f"📖 {book_info['title']}\n"
                f"👤 {book_info['author']}\n"
                f"📄 Страниц: {book_info['total_pages']}\n"
                f"📂 Статус: Запланировано",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                "Не удалось добавить книгу.",
                reply_markup=get_main_keyboard()
            )
    
    except ValueError:
        await update.message.reply_text(
            "ID книги должен быть числом.",
            reply_markup=get_main_keyboard()
        )

async def handle_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /search <запрос>"""
    if not context.args:
        await update.message.reply_text(
            "Использование: /search <запрос>\nПример: /search Гарри Поттер",
            reply_markup=get_main_keyboard()
        )
        return
    
    query = " ".join(context.args)
    books = book_db.search_books(query)
    
    if not books:
        await update.message.reply_text(
            f"По запросу '{query}' ничего не найдено.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Формируем сообщение с кнопками
    message_lines = [f"🔍 Найдено книг: {len(books)}\n"]
    
    keyboard_buttons = []
    for i, book in enumerate(books[:5], 1):
        genre = f" ({book['genre']})" if book['genre'] else ""
        message_lines.append(f"\n{i}. {book['title']} - {book['author']}{genre}")
        
        keyboard_buttons.append([
            InlineKeyboardButton(f"➕ Добавить '{book['title'][:15]}...'", callback_data=f"add_{book['id']}")
        ])
    
    keyboard_buttons.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    
    await update.message.reply_text(
        text="\n".join(message_lines),
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )

# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================

def main():
    """Запуск бота"""
    TOKEN = "8371793740:AAGyHz10Ro6JabxomkyjDGsjWhNaf3SUeMI"
    
    print("[INFO] Запуск BookBot с интерфейсом кнопок...")
    print(f"[INFO] Токен: {TOKEN[:15]}...")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("progress", handle_progress))
    application.add_handler(CommandHandler("add", handle_add_command))
    application.add_handler(CommandHandler("search", handle_search_command))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик текстовых сообщений (для поиска)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_search))
    
    # Запуск бота
    print("[INFO] BookBot запущен успешно!")
    print("[INFO] Доступные команды: /start, /progress, /add, /search")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
