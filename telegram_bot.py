import sqlite3
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from database import Database
from models import UserManager, BookManager

TOKEN = "8371793740:AAGyHz10Ro6JabxomkyjDGsjWhNaf3SUeMI"

WELCOME_STICKER = ["CAACAgIAAxkBAAEQBuppQu2eapVruh31VNO-DbF4QASQtQACbywAAyqpSB6hphm49sfPNgQ",
                   "CAACAgIAAxkBAAEQBuRpQuzOOVsJCOzPROSP0_2cvPe3UgACrykAAsDB-UtHA9Ns9W-TxTYE",
                   "CAACAgIAAxkBAAEQBtBpQuv1eht4rjoa9972B65DnRT3AgACKEAAAjIw0EvVKxizS16ujDYE",
                   "CAACAgIAAxkBAAEQBsppQuuVRAqB9AaCT17igXGF3clG2gAC-TUAArBpGEq2evopyqompzYE",
                   "CAACAgIAAxkBAAEQBsJpQutAeVdOqss38879qtPj45n1GgACjTgAAlplUErvEgk6b5K9kDYE",
                   "CAACAgIAAxkBAAEQBr5pQumA4mdBmTRtUR9KclFRJW7eSwACDSwAAsUXOEql6yqd-6--vDYE",
                   "CAACAgQAAxkBAAEQBrppQukKzzvEw1A04OK2TpQ5LB0hKwAChRwAAj90WVE_bp6QnNmEhTYE",
                   "CAACAgQAAxkBAAEQBrhpQujcKtkYCVApslr-DrWO-Jt58wACUhQAAtYTaFDtJffHUNfvxjYE",
                   "CAACAgQAAxkBAAEQBrZpQujPI7GK7fV6FBm6vgmYB9KPDAAC2xMAAlW38FB67b-yfmf_TTYE",
                   "CAACAgIAAxkBAAEQBeBpQn4DXTxY6eU5CEdf7NGV9vEWAgACkTYAAoGgUUoW1U_-NFdM8jYE"]

EMOJI = { "search": "🔍", "plus": "➕", "list": "📋", "help": "❓", "home": "🏠", "book": "📚",
          "info": "ℹ️", "read": "📖", "star": "🌟", "prev": "⬅️", "hello": "👋", "wow": "🎉",
          "user": "👤", "chart": "📊", "cross": "❌", "folder": "📂", "check": "✅",
          "calendar": "📅", "trophy": "🏆", "mail": "📬"}

db = Database()
user_manager = UserManager(db)
book_manager = BookManager(db)

async def start_command(update: Update, context):
    user = update.effective_user

    user_id = user_manager.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    random_sticker = random.choice(WELCOME_STICKER)
    await update.message.reply_sticker(random_sticker)

    text = f"""{EMOJI['hello']} Привет, {user.first_name}!

Я — HSEBookBot, помогу вести список книг.

Выбери действие:"""

    keyboard = [
        [InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")],
        [InlineKeyboardButton(f"{EMOJI['search']} Найти книгу", callback_data="search")],
        [InlineKeyboardButton(f"{EMOJI['plus']} Добавить книгу", callback_data="add_book")],
        [InlineKeyboardButton(f"{EMOJI['read']} Начать читать", callback_data="start_reading")],
        [InlineKeyboardButton(f"{EMOJI['info']} Статистика", callback_data="stats")],
        [InlineKeyboardButton(f"{EMOJI['star']} Оценить книгу", callback_data="rate_book")],
        [InlineKeyboardButton(f"{EMOJI['help']} Помощь", callback_data="help")]
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def help_command(update: Update, context):
    help_text = f"""{EMOJI['book']} HSE BookBot - помощник для учета книг

{EMOJI['list']} Команды:
/start - Главное меню
/help - Справка
/progress <ID> <страница> - Обновить прогресс
/add <ID> - Добавить книгу по ID
/addbook - Добавить новую книгу в каталог
/search <запрос> - Поиск книг
/stats - Статистика
/top <rating|popularity> [жанр] - Топ книги

💡 Используй кнопки!"""

    keyboard = [
        [InlineKeyboardButton(f"{EMOJI['book']} Главное меню", callback_data="main_menu"),
         InlineKeyboardButton(f"{EMOJI['search']} Поиск книг", callback_data="search")]
    ]

    await update.message.reply_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard))


async def progress_command(update: Update, context):
    if not context.args or len(context.args) != 2:
        await update.message.reply_text("Используй: /progress <ID_книги> <страница>\nПример: /progress 1 150")
        return

    try:
        user = update.effective_user
        book_id = int(context.args[0])
        page = int(context.args[1])
user_db_id = user_manager.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

        book_info = user_manager.get_book_info(user_db_id, book_id)
        if not book_info:
            await update.message.reply_text("У тебя нет этой книги.")
            return

        book = book_manager.get_book(book_id)
        if not book:
            await update.message.reply_text("Книга не найдена.")
            return

        if page > book.total_pages:
            await update.message.reply_text(f"В книге всего {book.total_pages} страниц!")
            return

        progress = (page / book.total_pages) * 100

        if progress >= 100:
            user_manager.update_book_status(user_db_id, book_id, 'completed')
            message = f"""{EMOJI['wow']} Поздравляю! Прочитал книгу!

{book.title}
{EMOJI['user']} {book.author}

Страниц: {page}/{book.total_pages} (100%)"""
            keyboard = [[
                InlineKeyboardButton(f"{EMOJI['star']} Оценить книгу", callback_data=f"ratebook_{book_id}"),
                InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")
            ]]
        else:
            message = f"""{EMOJI['read']} Прогресс обновлен!

{book.title}
{EMOJI['user']} {book.author}

Страница: {page} из {book.total_pages}
Прогресс: {progress:.1f}%"""
            keyboard = [[
                InlineKeyboardButton(f"{EMOJI['chart']} Еще обновить", callback_data=f"progress_{book_id}"),
                InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")
            ]]

        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    except ValueError:
        await update.message.reply_text("ID и страница должны быть числами.")
    except Exception as e:
        await update.message.reply_text("Ошибка.")
        print(f"Ошибка /progress: {e}")


async def add_command(update: Update, context):
    if not context.args:
        await update.message.reply_text("Используй: /add <ID_книги>\nПример: /add 1\n\nID найди при поиске.")
        return

    try:
        user = update.effective_user
        book_id = int(context.args[0])

        user_db_id = user_manager.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

        book = book_manager.get_book(book_id)
        if not book:
            await update.message.reply_text(f"Книга {book_id} не найдена.")
            return

        ok = user_manager.add_book(user_db_id, book_id, 'planned')

        if not ok:
            await update.message.reply_text("Эта книга уже есть.")
            return

        message = f"""{EMOJI['check']} Книга добавлена!

{book.title}
{EMOJI['user']} {book.author}
{EMOJI['list']} {book.total_pages} стр.
Статус: Запланировано"""

        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['read']} Начать читать", callback_data=f"start_{book_id}"),
             InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton(f"{EMOJI['plus']} Добавить еще", callback_data="add_book")]
        ]

        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    except ValueError:
        await update.message.reply_text("ID должен быть числом.")
    except Exception as e:
        await update.message.reply_text("Ошибка.")
        print(f"Ошибка /add: {e}")


async def addbook_command(update: Update, context):
    if not context.args or len(context.args) < 4:
        await update.message.reply_text(
            f"{EMOJI['cross']} Использование: /addbook <название> <автор> <страницы> <жанр> [описание]\n\n"
            "Пример:\n"
            f"/addbook Мастер_и_Маргарита Михаил_Булгаков 480 Классика\n"
            f"/addbook 1984 Джордж_Оруэлл 328 Антиутопия Роман_о_тоталитарном_обществе\n\n"
            "📝 Пробелы в словах заменяйте на '_'"
        )
        return

    try:
        args = context.args
title = args[0].replace('_', ' ').strip()
        author = args[1].replace('_', ' ').strip()

        try:
            pages = int(args[2])
            if pages <= 0:
                await update.message.reply_text(
                    f"{EMOJI['cross']} Количество страниц должно быть положительным числом!"
                )
                return
        except ValueError:
            await update.message.reply_text(
                f"{EMOJI['cross']} Количество страниц должно быть числом!"
            )
            return

        genre = args[3].replace('_', ' ').strip()

        description = ""
        if len(args) > 4:
            desc_parts = args[4:]
            description = " ".join(desc_parts).replace('_', ' ').strip()

        if not title or not author:
            await update.message.reply_text(
                f"{EMOJI['cross']} Название и автор не могут быть пустыми!"
            )
            return

        conn = sqlite3.connect('books.db')
        cursor = conn.cursor()

        cursor.execute(
            'SELECT id FROM books WHERE LOWER(title) = LOWER(?) AND LOWER(author) = LOWER(?)',
            (title, author)
        )
        existing = cursor.fetchone()

        if existing:
            book_id = existing[0]
            conn.close()
            await update.message.reply_text(
                f"{EMOJI['cross']} Книга уже есть в каталоге!\n\n"
                f"{EMOJI['book']} {title}\n"
                f"{EMOJI['user']} {author}\n"
                f"{EMOJI['list']} ID: {book_id}\n\n"
                f"Добавить себе: /add {book_id}"
            )
            return

        cursor.execute('''
            INSERT INTO books (title, author, total_pages, genre, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, author, pages, genre, description))

        book_id = cursor.lastrowid
        conn.commit()
        conn.close()

        response = (
            f"{EMOJI['check']} Книга добавлена в каталог!\n\n"
            f"{EMOJI['list']} ID: {book_id}\n"
            f"{EMOJI['book']} Название: {title}\n"
            f"{EMOJI['user']} Автор: {author}\n"
            f"{EMOJI['list']} Страниц: {pages}\n"
            f"{EMOJI['folder']} Жанр: {genre}"
        )

        if description:
            response += f"\n{EMOJI['info']} Описание: {description}"

        response += f"\n\n{EMOJI['plus']} Добавить себе: /add {book_id}"

        await update.message.reply_text(response)

        print(f"[LOG] Добавлена новая книга: '{title}' - '{author}' (ID: {book_id})")

    except sqlite3.Error as e:
        await update.message.reply_text(
            f"{EMOJI['cross']} Ошибка базы данных: {str(e)}"
        )
        print(f"[ERROR] Ошибка БД в /addbook: {e}")

    except Exception as e:
        await update.message.reply_text(
            f"{EMOJI['cross']} Неизвестная ошибка: {str(e)}"
        )
        print(f"[ERROR] Ошибка в /addbook: {e}")

async def search_command(update: Update, context):
    if not context.args:
        await show_search_menu(update)
        return

    query = " ".join(context.args)
    await do_search(update, query, "")


async def stats_command(update: Update, context):
    user = update.effective_user

    user_db_id = user_manager.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )

    stats = user_manager.get_stats(user_db_id)

    message = f"""📊 Твоя статистика:

{EMOJI['book']} Всего книг: {stats['total']}
{EMOJI['calendar']} Запланировано: {stats['planned']}
{EMOJI['read']} Читаю сейчас: {stats['reading']}
{EMOJI['check']} Прочитано: {stats['completed']}
{EMOJI['cross']} Брошено: {stats['dropped']}"""

    if stats['avg_rating'] > 0:
        message += f"\n{EMOJI['star']} Средняя оценка: {stats['avg_rating']:.1f}"

    keyboard = [
        [InlineKeyboardButton(f"{EMOJI['read']} Мои книги", callback_data="mybooks"),
         InlineKeyboardButton(f"{EMOJI['star']} Оценить книгу", callback_data="rate_book")]
    ]
await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


async def top_command(update: Update, context):
    if not context.args:
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['star']} По рейтингу", callback_data="top_rating"),
             InlineKeyboardButton(f"{EMOJI['user']} По популярности", callback_data="top_popularity")],
            [InlineKeyboardButton(f"{EMOJI['search']} Поиск книг", callback_data="search")]
        ]
        await update.message.reply_text(f"{EMOJI['trophy']} Выбери критерий:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    criteria = context.args[0].lower()
    filter_by = context.args[1] if len(context.args) > 1 else ""

    if criteria not in ['rating', 'popularity']:
        await update.message.reply_text("Используй: /top rating  или  /top popularity")
        return

    await show_top_books(update, criteria, filter_by)

async def handle_text_message(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if len(text) >= 2:
        books = book_manager.search_books(text, limit=5)

        if not books:
            keyboard = [
                [InlineKeyboardButton(f"{EMOJI['search']} Попробовать другой", callback_data="search"),
                 InlineKeyboardButton(f"{EMOJI['home']} Главное меню", callback_data="main_menu")]
            ]

            await update.message.reply_text(f"По запросу '{text}' ничего не найдено.",
                                            reply_markup=InlineKeyboardMarkup(keyboard))
            return

        message = f"{EMOJI['search']} Найдено по запросу '{text}':\n"

        keyboard_buttons = []
        for i, book in enumerate(books, 1):
            stats = db.get_book_stats(book.id)
            rating = f" {EMOJI['star']}{stats['avg_rating']:.1f}" if stats['avg_rating'] > 0 else ""

            message += f"\n{i}. {book.title}"
            message += f"\n   {EMOJI['user']} {book.author}{rating} (ID: {book.id})"

            short = book.title[:12] + "..." if len(book.title) > 12 else book.title
            keyboard_buttons.append([
                InlineKeyboardButton(f"{EMOJI['plus']} Добавить '{short}'", callback_data=f"add_{book.id}")
            ])

        keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['search']} Новый поиск", callback_data="search")])
        keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['home']} Главное меню", callback_data="main_menu")])

        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard_buttons))

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    data = query.data

    user_db_id = user_manager.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )

    if data == "main_menu":
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton(f"{EMOJI['search']} Найти книгу", callback_data="search")],
            [InlineKeyboardButton(f"{EMOJI['plus']} Добавить книгу", callback_data="add_book")],
            [InlineKeyboardButton(f"{EMOJI['read']} Начать читать", callback_data="start_reading")],
            [InlineKeyboardButton(f"{EMOJI['chart']} Статистика", callback_data="stats")],
            [InlineKeyboardButton(f"{EMOJI['star']} Оценить книгу", callback_data="rate_book")],
            [InlineKeyboardButton(f"{EMOJI['help']} Помощь", callback_data="help")]
        ]
        await query.edit_message_text(f"{EMOJI['home']} Главное меню\n\nВыбери действие:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "mybooks":
        books = user_manager.get_user_books(user_db_id)
if not books:
            keyboard = [
                [InlineKeyboardButton(f"{EMOJI['plus']} Добавить книгу", callback_data="add_book"),
                 InlineKeyboardButton(f"{EMOJI['search']} Найти книгу", callback_data="search")],
                [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text(f"{EMOJI['cross']} У тебя пока нет книг.", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        planned = []
        reading = []
        completed = []
        dropped = []

        for book in books:
            if book.status == 'planned':
                planned.append(book)
            elif book.status == 'reading':
                reading.append(book)
            elif book.status == 'completed':
                completed.append(book)
            elif book.status == 'dropped':
                dropped.append(book)

        message = f"{EMOJI['book']} Твои книги:\n"

        if reading:
            message += f"\n{EMOJI['read']}  Читаю сейчас ({len(reading)}):"
            for i, book in enumerate(reading[:3], 1):
                prog = book.get_progress()
                short = book.title[:15] + "..." if len(book.title) > 15 else book.title
                message += f"\n{i}. {short} - {prog:.0f}%"

        if planned:
            message += f"\n\n{EMOJI['calendar']}  Запланировано ({len(planned)}):"
            for i, book in enumerate(planned[:3], 1):
                short = book.title[:15] + "..." if len(book.title) > 15 else book.title
                message += f"\n{i}. {short}"

        if completed:
            message += f"\n\n{EMOJI['check']}  Прочитано ({len(completed)}):"
            for i, book in enumerate(completed[:3], 1):
                short = book.title[:15] + "..." if len(book.title) > 15 else book.title
                rating = f" {EMOJI['star']} {book.rating}" if book.rating else ""
                message += f"\n{i}. {short}{rating}"

        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['search']}  Найти книгу", callback_data="search"),
             InlineKeyboardButton(f"{EMOJI['plus']} Добавить книгу", callback_data="add_book")],
            [InlineKeyboardButton(f"{EMOJI['chart']} Статистика", callback_data="stats"),
             InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")]
        ]

        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "search":
        await show_search_menu(query)

    elif data == "add_book":
        popular = book_manager.search_books(limit=5)

        if not popular:
            keyboard = [
                [InlineKeyboardButton(f"{EMOJI['search']}  Найти книгу", callback_data="search"),
                 InlineKeyboardButton(f"{EMOJI['prev']}  Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text("Нет популярных книг.", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        keyboard_buttons = []
        for book in popular:
            keyboard_buttons.append([
                InlineKeyboardButton(f"{EMOJI['read']}  {book.get_short()}", callback_data=f"add_{book.id}")
            ])

        keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['search']}  Найти другую", callback_data="search")])
        keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['prev']}  Назад", callback_data="main_menu")])

        await query.edit_message_text(f"{EMOJI['book']}  Выбери книгу для добавления:",
                                      reply_markup=InlineKeyboardMarkup(keyboard_buttons))

    elif data == "start_reading":
        planned = user_manager.get_user_books(user_db_id, "planned")
if not planned:
            keyboard = [
                [InlineKeyboardButton(f"{EMOJI['search']}  Добавить книгу", callback_data="add_book"),
                 InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
                [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text("📭 Нет запланированных книг.", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        keyboard_buttons = []
        for book in planned[:5]:
            keyboard_buttons.append([
                InlineKeyboardButton(f"📖 {book.title[:15]}...", callback_data=f"start_{book.book_id}")
            ])

        keyboard_buttons.append([InlineKeyboardButton("📚 Все книги", callback_data="mybooks")])
        keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])

        await query.edit_message_text("📚 Выбери книгу для чтения:", reply_markup=InlineKeyboardMarkup(keyboard_buttons))

    elif data == "stats":
        stats = user_manager.get_stats(user_db_id)

        message = f"""📊 Твоя статистика:

📚 Всего книг: {stats['total']}
📅 Запланировано: {stats['planned']}
📖 Читаю сейчас: {stats['reading']}
✅ Прочитано: {stats['completed']}
❌ Брошено: {stats['dropped']}"""

        if stats['avg_rating'] > 0:
            message += f"\n⭐️ Средняя оценка: {stats['avg_rating']:.1f}"

        keyboard = [
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
             InlineKeyboardButton("⭐️ Оценить книгу", callback_data="rate_book")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]

        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "rate_book":
        completed = user_manager.get_user_books(user_db_id, "completed")

        if not completed:
            keyboard = [
                [InlineKeyboardButton("📖 Начать читать", callback_data="start_reading"),
                 InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
                [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text("📭 Нет прочитанных книг для оценки.",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            return

        keyboard_buttons = []
        for book in completed[:3]:
            if book.rating:
                keyboard_buttons.append([
                    InlineKeyboardButton(f"⭐️ {book.rating}/5 - {book.title[:10]}...", callback_data="no_action")
                ])
            else:
                keyboard_buttons.append([
                    InlineKeyboardButton(f"📖 {book.title[:15]}...", callback_data=f"rateshow_{book.book_id}")
                ])

        keyboard_buttons.append([InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")])
        keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])

        await query.edit_message_text("⭐️ Выбери книгу для оценки:", reply_markup=InlineKeyboardMarkup(keyboard_buttons))

    elif data.startswith("rateshow_"):
        try:
            book_id = int(data.replace("rateshow_", ""))
            book = book_manager.get_book(book_id)

            if not book:
                await query.edit_message_text("❌ Книга не найдена.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="rate_book")]
                ]))
                return

            keyboard_buttons = []
            row = []
            for r in range(1, 6):
                row.append(InlineKeyboardButton(f"{r}⭐️", callback_data=f"rate_{book_id}_{r}"))
            keyboard_buttons.append(row)

            keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="rate_book")])
