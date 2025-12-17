#!/usr/bin/env python3
"""
telegram_bot.py - Telegram бот для учета книг BookBot
"""

from database import Database
from models import UserManager, BookManager, Book, UserBook

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ваш токен Telegram бота
TOKEN = "8371793740:AAGyHz10Ro6JabxomkyjDGsjWhNaf3SUeMI"

# Инициализируем базу данных и менеджеры
db = Database()
user_manager = UserManager(db)
book_manager = BookManager(db)


# ==================== КОМАНДЫ ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user = update.effective_user
    
    # Получаем или создаем пользователя
    user_id = user_manager.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    welcome_text = f"""👋 Привет, {user.first_name}!

Я — BookBot, помогу тебе вести список книг.

Выбери действие:"""
    
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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help."""
    help_text = """📚 BookBot - Помощник для учета книг

📋 Команды:
/start - Главное меню
/help - Эта справка
/progress <ID> <страница> - Обновить прогресс чтения
/add <ID> - Добавить книгу по ID
/search <запрос> - Поиск книг
/stats - Ваша статистика
/top <rating|popularity> [жанр|автор] - Топ книги

💡 Используйте кнопки для удобства!"""
    
    keyboard = [
        [InlineKeyboardButton("📚 Главное меню", callback_data="main_menu"),
         InlineKeyboardButton("🔍 Поиск книг", callback_data="search")]
    ]
    
    await update.message.reply_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard))


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /progress."""
    if not context.args or len(context.args) != 2:
        await update.message.reply_text(
            "Использование: /progress <ID_книги> <номер_страницы>\n"
            "Пример: /progress 1 150"
        )
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        current_page = int(context.args[1])
        
        # Получаем ID пользователя в базе
        user_db_id = user_manager.get_or_create_user(
            telegram_id=user_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name
        )
        
        # Получаем информацию о книге
        book_info = user_manager.get_book_info(user_db_id, book_id)
        if not book_info:
            await update.message.reply_text("У вас нет этой книги в коллекции.")
            return
        
        if book_info.status != 'reading':
            await update.message.reply_text("Эту книгу вы сейчас не читаете.")
            return
        
        # Получаем информацию о книге
        book = book_manager.get_book(book_id)
        if not book:
            await update.message.reply_text("Книга не найдена.")
            return
        
        if current_page > book.total_pages:
            await update.message.reply_text(f"В этой книге только {book.total_pages} страниц!")
            return
        
        # Обновляем прогресс
        success = user_manager.update_progress(user_db_id, book_id, current_page)
        
        if not success:
            await update.message.reply_text("Не удалось обновить прогресс.")
            return
        
        progress = (current_page / book.total_pages) * 100
        
        if progress >= 100:
            # Завершаем чтение
            user_manager.update_book_status(user_db_id, book_id, 'completed')
            
            message = f"""🎉 Поздравляем! Вы прочитали книгу!

{book.title}
👤 {book.author}

Прогресс: {current_page}/{book.total_pages} страниц (100%)"""
            
            keyboard = [
                [InlineKeyboardButton("⭐ Оценить книгу", callback_data=f"rate_{book_id}"),
                 InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")]
            ]
        else:
            message = f"""📖 Прогресс обновлен!

{book.title}
👤 {book.author}

Страница: {current_page} из {book.total_pages}
Прогресс: {progress:.1f}%"""
            
            keyboard = [
                [InlineKeyboardButton("📊 Продолжить обновлять", callback_data=f"progress_{book_id}"),
                 InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")]
            ]
        
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except ValueError:
        await update.message.reply_text("ID книги и номер страницы должны быть числами.")
    except Exception as e:
        logger.error(f"Ошибка в команде /progress: {e}")
        await update.message.reply_text("Произошла ошибка.")


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /add."""
    if not context.args:
        await update.message.reply_text(
            "Использование: /add <ID_книги>\n"
            "Пример: /add 1\n\n"
            "ID книги можно найти при поиске."
        )
        return
    
    try:
        user_id = update.effective_user.id
        book_id = int(context.args[0])
        
        # Получаем ID пользователя в базе
        user_db_id = user_manager.get_or_create_user(
            telegram_id=user_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name
        )
        
        # Проверяем существование книги
        book = book_manager.get_book(book_id)
        if not book:
            await update.message.reply_text(f"Книга с ID {book_id} не найдена.")
            return
        
        # Добавляем книгу
        success = user_manager.add_book(user_db_id, book_id, 'planned')
        
        if not success:
            await update.message.reply_text("Эта книга уже есть в вашей коллекции.")
            return
        
        message = f"""✅ Книга добавлена!

{book.title}
👤 {book.author}
📄 Страниц: {book.total_pages}
📂 Статус: Запланировано"""
        
        keyboard = [
            [InlineKeyboardButton("📖 Начать читать", callback_data=f"start_{book_id}"),
             InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton("➕ Добавить еще", callback_data="add_book")]
        ]
        
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except ValueError:
        await update.message.reply_text("ID книги должен быть числом.")
    except Exception as e:
        logger.error(f"Ошибка в команде /add: {e}")
        await update.message.reply_text("Произошла ошибка.")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /search."""
    if not context.args:
        # Показываем меню поиска
        await show_search_menu(update)
        return
    
    query = " ".join(context.args)
    await perform_search(update, query, "")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stats."""
    user_id = update.effective_user.id
    
    try:
        # Получаем ID пользователя в базе
        user_db_id = user_manager.get_or_create_user(
            telegram_id=user_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name
        )
        
        # Получаем статистику
        stats = user_manager.get_stats(user_db_id)
        
        message = f"""📊 Ваша статистика чтения:

📚 Всего книг: {stats['total']}
📅 Запланировано: {stats['planned']}
📖 Читаю сейчас: {stats['reading']}
✅ Прочитано: {stats['completed']}
❌ Брошено: {stats['dropped']}"""
        
        if stats['avg_rating'] > 0:
            message += f"\n⭐ Средняя оценка: {stats['avg_rating']}"
        
        keyboard = [
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
             InlineKeyboardButton("⭐ Оценить книгу", callback_data="rate_book")]
        ]
        
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Ошибка в команде /stats: {e}")
        await update.message.reply_text("Произошла ошибка при получении статистики.")


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /top."""
    if not context.args:
        # Показываем меню выбора критерия
        keyboard = [
            [InlineKeyboardButton("⭐ По рейтингу", callback_data="top_rating"),
             InlineKeyboardButton("👥 По популярности", callback_data="top_popularity")],
            [InlineKeyboardButton("🔍 Поиск книг", callback_data="search")]
        ]
        
        await update.message.reply_text(
            "🏆 Выберите критерий для топ книг:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    criteria = context.args[0].lower()
    filter_by = context.args[1] if len(context.args) > 1 else ""
    
    if criteria not in ['rating', 'popularity']:
        await update.message.reply_text(
            "Использование: /top <rating|popularity> [жанр|автор]\n"
            "Примеры:\n"
            "/top rating - книги с наивысшим рейтингом\n"
            "/top popularity - самые популярные книги\n"
            "/top rating фэнтези - лучшие книги в жанре фэнтези"
        )
        return
    
    await show_top_books(update, criteria, filter_by)


# ==================== ОБРАБОТЧИК КНОПОК ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех кнопок."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Получаем ID пользователя в базе
    user_db_id = user_manager.get_or_create_user(
        telegram_id=user_id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name
    )
    
    callback_data = query.data
    
    # Главное меню
    if callback_data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton("🔍 Найти книгу", callback_data="search")],
            [InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book")],
            [InlineKeyboardButton("📖 Начать читать", callback_data="start_reading")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("⭐ Оценить книгу", callback_data="rate_book")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        
        await query.edit_message_text(
            text="📚 Главное меню BookBot\n\nВыбери действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Мои книги
    elif callback_data == "mybooks":
        books = user_manager.get_user_books(user_db_id)
        
        if not books:
            keyboard = [
                [InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book"),
                 InlineKeyboardButton("🔍 Найти книгу", callback_data="search")],
                [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(
                text="📭 У вас пока нет книг в коллекции.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Группируем книги по статусу
        books_by_status = {}
        for status in ['planned', 'reading', 'completed', 'dropped']:
            status_books = user_manager.get_user_books(user_db_id, status)
            if status_books:
                books_by_status[status] = status_books
        
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
                if status == 'reading' and book.current_page > 0:
                    progress = book.get_progress_percentage()
                    message_lines.append(f"{i}. {book.title[:20]}... - стр. {book.current_page} ({progress:.1f}%)")
                else:
                    rating = f" ⭐ {book.rating}" if book.rating else ""
                    message_lines.append(f"{i}. {book.title[:20]}...{rating}")
        
        keyboard = [
            [InlineKeyboardButton("🔍 Найти книгу", callback_data="search"),
             InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats"),
             InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text="\n".join(message_lines),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Поиск книг
    elif callback_data == "search":
        await show_search_menu(query)
    
    # Добавить книгу
    elif callback_data == "add_book":
        # Получаем несколько популярных книг
        popular_books = book_manager.search_books(limit=5)
        
        keyboard_buttons = []
        for book in popular_books:
            keyboard_buttons.append([
                InlineKeyboardButton(f"📖 {book.title[:20]}...", callback_data=f"add_{book.id}")
            ])
        
        keyboard_buttons.append([InlineKeyboardButton("🔍 Найти другую книгу", callback_data="search")])
        keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        await query.edit_message_text(
            text="📚 Выберите книгу для добавления:",
            reply_markup=InlineKeyboardMarkup(keyboard_buttons)
        )
    
    # Начать читать
    elif callback_data == "start_reading":
        planned_books = user_manager.get_user_books(user_db_id, "planned")
        
        if not planned_books:
            keyboard = [
                [InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book"),
                 InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
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
            keyboard_buttons.append([
                InlineKeyboardButton(f"📖 {book.title[:20]}...", callback_data=f"read_{book.book_id}")
            ])
        
        keyboard_buttons.append([InlineKeyboardButton("📚 Все мои книги", callback_data="mybooks")])
        keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        await query.edit_message_text(
            text="📚 Выберите книгу для чтения:",
            reply_markup=InlineKeyboardMarkup(keyboard_buttons)
        )
    
    # Статистика
    elif callback_data == "stats":
        stats = user_manager.get_stats(user_db_id)
        
        message = f"""📊 Ваша статистика чтения:

📚 Всего книг: {stats['total']}
📅 Запланировано: {stats['planned']}
📖 Читаю сейчас: {stats['reading']}
✅ Прочитано: {stats['completed']}
❌ Брошено: {stats['dropped']}"""
        
        if stats['avg_rating'] > 0:
            message += f"\n⭐ Средняя оценка: {stats['avg_rating']}"
        
        keyboard = [
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
             InlineKeyboardButton("⭐ Оценить книгу", callback_data="rate_book")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Оценить книгу
    elif callback_data == "rate_book":
        completed_books = user_manager.get_user_books(user_db_id, "completed")
        
        if not completed_books:
            keyboard = [
                [InlineKeyboardButton("📖 Начать читать", callback_data="start_reading"),
                 InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
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
            # Если книга уже оценена, показываем оценку
            if book.rating:
                keyboard_buttons.append([
                    InlineKeyboardButton(f"⭐ {book.rating}/5 - {book.title[:15]}...", callback_data="no_action")
                ])
            else:
                # Кнопки оценки от 1 до 5 звезд
                rating_buttons = []
                for rating in range(1, 6):
                    rating_buttons.append(
                        InlineKeyboardButton(f"{rating}⭐", callback_data=f"rate_{book.book_id}_{rating}")
                    )
                keyboard_buttons.append(rating_buttons)
        
        keyboard_buttons.append([InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")])
        keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        await query.edit_message_text(
            text="⭐ Оцените прочитанные книги:",
            reply_markup=InlineKeyboardMarkup(keyboard_buttons)
        )
    
    # Помощь
    elif callback_data == "help":
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
/add <id> - Добавить книгу по ID"""
        
        keyboard = [
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
             InlineKeyboardButton("🔍 Поиск", callback_data="search")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text=help_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Поиск по жанру
    elif callback_data.startswith("search_"):
        search_query = callback_data.replace("search_", "")
        
        if search_query == "input":
            await query.edit_message_text(
                text="📝 Введите название книги или автора:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="search")]
                ])
            )
            return
        
        books = book_manager.search_books(genre=search_query)
        
        if not books:
            keyboard = [
                [InlineKeyboardButton("🔍 Попробовать другой запрос", callback_data="search"),
                 InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(
                text=f"📭 По жанру '{search_query}' ничего не найдено.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Формируем сообщение с кнопками для добавления
        message_lines = [f"🔍 Найдено книг: {len(books)}\n"]
        
        keyboard_buttons = []
        for i, book in enumerate(books[:5], 1):
            stats = db.get_book_statistics(book.id)
            rating_info = f" ⭐ {stats.get('avg_rating', 0)}" if stats.get('avg_rating', 0) > 0 else ""
            message_lines.append(f"\n{i}. {book.title} - {book.author}{rating_info}")
            
            # Кнопка для добавления книги
            keyboard_buttons.append([
                InlineKeyboardButton(f"➕ Добавить '{book.title[:15]}...'", callback_data=f"add_{book.id}")
            ])
        
        # Кнопки навигации
        keyboard_buttons.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="search")])
        keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        await query.edit_message_text(
            text="\n".join(message_lines),
            reply_markup=InlineKeyboardMarkup(keyboard_buttons)
        )
    
    # Добавить книгу по ID
    elif callback_data.startswith("add_"):
        try:
            book_id = int(callback_data.replace("add_", ""))
            book = book_manager.get_book(book_id)
            
            if not book:
                await query.edit_message_text(
                    text="❌ Книга не найдена.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="add_book")]
                    ])
                )
                return
            
            if user_manager.add_book(user_db_id, book_id, "planned"):
                keyboard = [
                    [InlineKeyboardButton("📖 Начать читать", callback_data=f"read_{book_id}"),
                     InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
                    [InlineKeyboardButton("➕ Добавить еще", callback_data="add_book"),
                     InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                ]
                
                await query.edit_message_text(
                    text=f"""✅ Книга добавлена!

{book.title}
👤 {book.author}
📄 Страниц: {book.total_pages}
📂 Статус: Запланировано""",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(
                    text="❌ Эта книга уже есть в вашей коллекции.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="add_book")]
                    ])
                )
        except ValueError:
            await query.edit_message_text(
                text="❌ Ошибка: неверный ID книги.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="add_book")]
                ])
            )
    
    # Начать читать конкретную книгу
    elif callback_data.startswith("read_"):
        try:
            book_id = int(callback_data.replace("read_", ""))
            
            if not user_manager.has_book(user_db_id, book_id):
                await query.edit_message_text(
                    text="❌ У вас нет этой книги в коллекции.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="start_reading")]
                    ])
                )
                return
            
            if user_manager.update_book_status(user_db_id, book_id, "reading"):
                book = book_manager.get_book(book_id)
                
                keyboard = [
                    [InlineKeyboardButton("📊 Обновить прогресс", callback_data=f"progress_{book_id}"),
                     InlineKeyboardButton("✅ Закончить чтение", callback_data=f"finish_{book_id}")],
                    [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
                     InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                ]
                
                await query.edit_message_text(
                    text=f"""📖 Начинаем читать!

{book.title}
👤 {book.author}
📄 Всего страниц: {book.total_pages}

Чтобы обновить прогресс, отправьте:
/progress {book_id} <номер_страницы>""",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(
                    text="❌ Не удалось начать чтение.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="start_reading")]
                    ])
                )
        except ValueError:
            await query.edit_message_text(
                text="❌ Ошибка: неверный ID книги.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="start_reading")]
                ])
            )
    
    # Оценить книгу
    elif callback_data.startswith("rate_"):
        try:
            parts = callback_data.replace("rate_", "").split("_")
            if len(parts) == 2:
                book_id = int(parts[0])
                rating = int(parts[1])
                
                if user_manager.rate_book(user_db_id, book_id, rating):
                    book = book_manager.get_book(book_id)
                    stats = db.get_book_statistics(book_id)
                    
                    keyboard = [
                        [InlineKeyboardButton("⭐ Оценить другую книгу", callback_data="rate_book"),
                         InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
                        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                    ]
                    
                    stars = "⭐" * rating
                    await query.edit_message_text(
                        text=f"""✅ Оценка поставлена!

{book.title}
{stars} ({rating}/5)

Общий рейтинг: {stats.get('avg_rating', 0)}/5
({stats.get('rating_count', 0)} оценок)""",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await query.edit_message_text(
                        text="❌ Не удалось поставить оценку.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Назад", callback_data="rate_book")]
                        ])
                    )
        except (ValueError, IndexError):
            await query.edit_message_text(
                text="❌ Ошибка оценки.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="rate_book")]
                ])
            )
    
    # Обновить прогресс
    elif callback_data.startswith("progress_"):
        book_id = int(callback_data.replace("progress_", ""))
        await query.edit_message_text(
            text=f"📊 Чтобы обновить прогресс чтения, отправьте команду:\n"
                 f"/progress {book_id} <номер_страницы>\n\n"
                 f"Например: /progress {book_id} 150",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="mybooks")]
            ])
        )
    
    # Закончить чтение
    elif callback_data.startswith("finish_"):
        try:
            book_id = int(callback_data.replace("finish_", ""))
            
            if not user_manager.has_book(user_db_id, book_id):
                await query.edit_message_text(
                    text="❌ У вас нет этой книги в коллекции.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="mybooks")]
                    ])
                )
                return
            
            if user_manager.update_book_status(user_db_id, book_id, "completed"):
                book = book_manager.get_book(book_id)
                
                keyboard = [
                    [InlineKeyboardButton("⭐ Оценить книгу", callback_data=f"rate_{book_id}"),
                     InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                ]
                
                await query.edit_message_text(
                    text=f"""🎉 Поздравляем с прочтением!

{book.title}
👤 {book.author}""",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(
                    text="❌ Не удалось отметить как прочитанную.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="mybooks")]
                    ])
                )
        except ValueError:
            await query.edit_message_text(
                text="❌ Ошибка: неверный ID книги.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="mybooks")]
                ])
            )
    
    # Топ книги
    elif callback_data.startswith("top_"):
        criteria = callback_data.replace("top_", "")
        await show_top_books(query, criteria)
    
    # Пустое действие
    elif callback_data == "no_action":
        await query.answer(text="Выберите действие из меню")


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def show_search_menu(update_or_query):
    """Показывает меню поиска."""
    genres = book_manager.get_all_genres()
    
    keyboard_buttons = []
    for i in range(0, min(len(genres), 8), 2):
        row = []
        row.append(InlineKeyboardButton(f"📂 {genres[i]}", callback_data=f"search_{genres[i]}"))
        if i + 1 < len(genres):
            row.append(InlineKeyboardButton(f"📂 {genres[i+1]}", callback_data=f"search_{genres[i+1]}"))
        keyboard_buttons.append(row)
    
    keyboard_buttons.append([InlineKeyboardButton("🔍 Поиск по названию/автору", callback_data="search_input")])
    keyboard_buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    
    text = "🔍 Выберите жанр или поиск по названию:"
    
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    else:
        await update_or_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard_buttons))


async def perform_search(update_or_query, query: str, genre: str):
    """Выполняет поиск книг."""
    books = book_manager.search_books(query, genre, limit=10)
    
    if not books:
        if query:
            message = f"📭 По запросу '{query}' ничего не найдено."
        else:
            message = f"📭 В жанре '{genre}' ничего не найдено."
        
        keyboard = [
            [InlineKeyboardButton("🔍 Новый поиск", callback_data="search"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update_or_query.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Формируем сообщение
    if query:
        title = f"🔍 Результаты поиска по запросу '{query}':"
    else:
        title = f"🔍 Книги в жанре '{genre}':"
    
    message_lines = [f"{title}\n"]
    
    keyboard_buttons = []
    for i, book in enumerate(books, 1):
        stats = db.get_book_statistics(book.id)
        rating_info = f" ⭐ {stats.get('avg_rating', 0)}" if stats.get('avg_rating', 0) > 0 else ""
        popularity_info = f" 👥 {stats.get('total_added', 0)}"
        
        message_lines.append(f"\n{i}. {book.title}")
        message_lines.append(f"   👤 {book.author}")
        message_lines.append(f"   📂 {book.genre}")
        message_lines.append(f"   📊{rating_info}{popularity_info}")
        
        # Кнопка для добавления
        short_title = book.title[:15] + "..." if len(book.title) > 15 else book.title
        keyboard_buttons.append([
            InlineKeyboardButton(f"➕ Добавить '{short_title}'", callback_data=f"add_{book.id}")
        ])
    
    keyboard_buttons.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="search")])
    keyboard_buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text("\n".join(message_lines), 
                                              reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    else:
        await update_or_query.message.reply_text("\n".join(message_lines),
                                               reply_markup=InlineKeyboardMarkup(keyboard_buttons))


async def show_top_books(update_or_query, criteria: str, filter_by: str = ""):
    """Показывает топ книги."""
    # Определяем, что фильтровать
    genres = book_manager.get_all_genres()
    genre = filter_by if filter_by in genres else ""
    author = filter_by if not genre and filter_by else ""
    
    books = book_manager.get_top_books(criteria, genre, author, limit=5)
    
    if not books:
        message = "📭 Не найдено книг по выбранному критерию."
        if genre:
            message = f"📭 В жанре '{genre}' не найдено книг."
        elif author:
            message = f"📭 У автора '{author}' не найдено книг."
        
        keyboard = [
            [InlineKeyboardButton("🏆 Другой критерий", callback_data="top_books"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update_or_query.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
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
        stats = db.get_book_statistics(book.id)
        
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
            InlineKeyboardButton(f"➕ Добавить '{short_title}'", callback_data=f"add_{book.id}")
        ])
    
    keyboard_buttons.append([InlineKeyboardButton("⭐ По рейтингу", callback_data="top_rating"),
                           InlineKeyboardButton("👥 По популярности", callback_data="top_popularity")])
    keyboard_buttons.append([InlineKeyboardButton("🔍 Поиск книг", callback_data="search"),
                           InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text("\n".join(message_lines), 
                                              reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    else:
        await update_or_query.message.reply_text("\n".join(message_lines),
                                               reply_markup=InlineKeyboardMarkup(keyboard_buttons))


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений."""
    text = update.message.text.strip()
    
    if len(text) < 2:
        return
    
    # Если это ответ на поиск
    books = book_manager.search_books(text)
    
    if not books:
        keyboard = [
            [InlineKeyboardButton("🔍 Попробовать другой запрос", callback_data="search"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await update.message.reply_text(
            f"По запросу '{text}' ничего не найдено.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Формируем сообщение с кнопками
    message_lines = [f"🔍 Найдено по запросу '{text}':\n"]
    
    keyboard_buttons = []
    for i, book in enumerate(books[:5], 1):
        stats = db.get_book_statistics(book.id)
        rating_info = f" ⭐ {stats.get('avg_rating', 0)}" if stats.get('avg_rating', 0) > 0 else ""
        
        message_lines.append(f"\n{i}. {book.title} - {book.author}{rating_info}")
        
        keyboard_buttons.append([
            InlineKeyboardButton(f"➕ Добавить '{book.title[:15]}...'", callback_data=f"add_{book.id}")
        ])
    
    keyboard_buttons.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="search")])
    keyboard_buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    
    await update.message.reply_text(
        text="\n".join(message_lines),
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок."""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        keyboard = [
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except:
        pass


# ==================== ЗАПУСК БОТА ====================

def main():
    """Запуск бота."""
    print("=" * 50)
    print(" Запуск BookBot...")
    print("=" * 50)
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("progress", progress_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("top", top_command))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота
    print(" BookBot запущен успешно!")
    print(" Ожидание сообщений...")
    print("Для остановки нажмите Ctrl+C")
    
    application.run_polling(allowed_updates=None)


if __name__ == '__main__':
    main()
