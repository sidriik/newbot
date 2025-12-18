import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from database import Database

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

EMOJI = {"search": "🔍", "plus": "➕", "list": "📋", "help": "❓", "home": "🏠", "book": "📚",
         "info": "ℹ️", "read": "📖", "star": "🌟", "prev": "⬅️", "hello": "👋", "wow": "🎉",
         "user": "👤", "chart": "📊", "cross": "❌", "folder": "📂", "check": "✅",
         "calendar": "📅", "trophy": "🏆", "mail": "📬"}

ADD_BOOK_STATES = {}

db = Database()


async def start_command(update: Update, context):
    """
    Обработчик команды /start. Приветствует пользователя и показывает главное меню.

    :param update: Объект обновления Telegram
    :type update: Update
    :param context: Контекст выполнения
    :type context: ContextTypes
    :returns: None
    """
    user = update.effective_user

    random_sticker = random.choice(WELCOME_STICKER)
    await update.message.reply_sticker(random_sticker)

    db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    text = f"""{EMOJI['hello']} Привет, {user.first_name}!

Я — <b>HSEBookBot</b>, помогу вести список книг.

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


async def progress_command(update: Update, context):
    """
    Обработчик команды /progress. Обновляет прогресс чтения книги.

    :param update: Объект обновления Telegram
    :type update: Update
    :param context: Контекст выполнения
    :type context: ContextTypes
    :returns: None
    :raises ValueError: Если ID книги или номер страницы не являются числами
    """
    if not context.args or len(context.args) != 2:
        await update.message.reply_text(
            f"{EMOJI['cross']} Используй: /progress <ID_книги> <страница>\nПример: /progress 1 150")
        return

    try:
        user = update.effective_user
        book_id = int(context.args[0])
        page = int(context.args[1])

        user_db_id = db.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

        book_info = db.get_book_info(user_db_id, book_id)
        if not book_info:
            await update.message.reply_text(f"{EMOJI['cross']} У тебя нет этой книги.")
            return

        if book_info['status'] != 'reading':
            await update.message.reply_text(f"{EMOJI['cross']} Эту книгу ты сейчас не читаешь.")
            return

        book = db.get_book(book_id)
        if not book:
            await update.message.reply_text(f"{EMOJI['cross']} Книга не найдена.")
            return

        if page > book['total_pages']:
            await update.message.reply_text(f"{EMOJI['cross']} В книге всего {book['total_pages']} страниц!")
            return

        ok = db.update_progress(user_db_id, book_id, page)
        if not ok:
            await update.message.reply_text(f"{EMOJI['cross']} Ошибка обновления.")
            return

        progress = (page / book['total_pages']) * 100

        if progress >= 100:
            db.update_book_status(user_db_id, book_id, 'completed')
            message = f"""{EMOJI['wow']} Поздравляю! Прочитал книгу!

{book['title']}
{EMOJI['user']} {book['author']}

Страниц: {page}/{book['total_pages']} (100%)"""
            keyboard = [[
                InlineKeyboardButton(f"{EMOJI['star']} Оценить книгу", callback_data=f"ratebook_{book_id}"),
                InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")
            ]]
        else:
            message = f"""{EMOJI['read']} Прогресс обновлен!

{book['title']}
{EMOJI['user']} {book['author']}

Страница: {page} из {book['total_pages']}
Прогресс: {progress:.1f}%"""
            keyboard = [[
                InlineKeyboardButton(f"{EMOJI['chart']} Еще обновить", callback_data=f"progress_{book_id}"),
                InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")
            ]]

        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    except ValueError:
        await update.message.reply_text(f"{EMOJI['cross']} ID и страница должны быть числами.")
    except Exception as e:
        await update.message.reply_text(f"{EMOJI['cross']} Ошибка.")
        print(f"Ошибка /progress: {e}")


async def add_command(update: Update, context):
    """
    Обработчик команды /add. Добавляет книгу в список пользователя.

    :param update: Объект обновления Telegram
    :type update: Update
    :param context: Контекст выполнения
    :type context: ContextTypes
    :returns: None
    :raises ValueError: Если ID книги не является числом
    """
    if not context.args:
        await update.message.reply_text(
            f"{EMOJI['cross']} Используй: /add <ID_книги>\nПример: /add 1\n\nID найди при поиске.")
        return

    try:
        user = update.effective_user
        book_id = int(context.args[0])

        user_db_id = db.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

        book = db.get_book(book_id)
        if not book:
            await update.message.reply_text(f"{EMOJI['cross']} Книга {book_id} не найдена.")
            return

        ok = db.add_user_book(user_db_id, book_id, 'planned')

        if not ok:
            await update.message.reply_text(f"{EMOJI['cross']} Эта книга уже есть.")
            return

        message = f"""{EMOJI['check']} Книга добавена!

{book['title']}
{EMOJI['user']} {book['author']}
{EMOJI['list']} {book['total_pages']} стр.
{EMOJI['folder']} Статус: Запланировано"""

        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['read']} Начать читать", callback_data=f"start_{book_id}"),
             InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton(f"{EMOJI['plus']} Добавить еще", callback_data="add_book")]
        ]

        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    except ValueError:
        await update.message.reply_text(f"{EMOJI['cross']} ID должен быть числом.")
    except Exception as e:
        await update.message.reply_text(f"{EMOJI['cross']} Ошибка.")
        print(f"Ошибка /add: {e}")


async def addbook_command(update: Update, context):
    """
    Обработчик команды /addbook. Добавляет новую книгу в общий каталог.

    :param update: Объект обновления Telegram
    :type update: Update
    :param context: Контекст выполнения
    :type context: ContextTypes
    :returns: None
    """
    user_id = update.effective_user.id

    if context.args and len(context.args) >= 4:
        try:
            args = context.args

            if len(args) < 4:
                await update.message.reply_text(
                    f"{EMOJI['cross']} Недостаточно аргументов! Нужно: название, автор, страницы, жанр\n\n"
                    f"Пример: /addbook Мастер_и_Маргарита Михаил_Булгаков 480 Классика\n\n"
                    f"Или используйте /addbook без аргументов для пошагового добавления"
                )
                return

            title = args[0].replace('_', ' ').strip()
            author = args[1].replace('_', ' ').strip()

            try:
                pages = int(args[2])
                if pages <= 0:
                    await update.message.reply_text(
                        f"{EMOJI['cross']} Количество страниц должно быть положительным числом!")
                    return
            except ValueError:
                await update.message.reply_text(f"{EMOJI['cross']} Количество страниц должно быть числом!")
                return

            genre = args[3].replace('_', ' ').strip()

            description = ""
            if len(args) > 4:
                desc_parts = args[4:]
                description = " ".join(desc_parts).replace('_', ' ').strip()

            if not title or not author:
                await update.message.reply_text(f"{EMOJI['cross']} Название и автор не могут быть пустыми!")
                return

            success, book_id, message = db.add_book_to_catalog_simple(title, author, pages, genre, description)

            if not success:
                if "уже есть" in message.lower():
                    await update.message.reply_text(
                        f"{message}\n\n"
                        f"{EMOJI['plus']} Добавить себе: /add {book_id}"
                    )
                else:
                    await update.message.reply_text(message)
                return

            response = f"""{EMOJI['check']} Книга добавлена в каталог!

{EMOJI['list']} ID: {book_id}
{EMOJI['book']} Название: {title}
{EMOJI['user']} Автор: {author}
{EMOJI['list']} Страниц: {pages}
{EMOJI['folder']} Жанр: {genre}"""

            if description:
                response += f"\n{EMOJI['info']} Описание: {description}"

            response += f"\n\n{EMOJI['plus']} Добавить себе: /add {book_id}"

            await update.message.reply_text(response)

            print(f"Добавлена новая книга: '{title}' - '{author}' (ID: {book_id})")

            return

        except Exception as e:
            await update.message.reply_text(f"{EMOJI['cross']} Ошибка: {str(e)}")
            print(f"Ошибка в /addbook (прямой вызов): {e}")
            return

    ADD_BOOK_STATES[user_id] = {'step': 1}

    await update.message.reply_text(
        f"{EMOJI['book']} Добавление новой книги в каталог\n\n"
        f"Давайте добавим книгу по шагам!\n\n"
        f"1️⃣ Отправьте название книги:\n"
        f"(например: Мастер и Маргарита)"
    )


async def search_command(update: Update, context):
    """
    Обработчик команды /search. Поиск книг по запросу.

    :param update: Объект обновления Telegram
    :type update: Update
    :param context: Контекст выполнения
    :type context: ContextTypes
    :returns: None
    """
    if not context.args:
        await show_search_menu(update)
        return

    query = " ".join(context.args)
    await do_search(update, query, "")


async def stats_command(update: Update, context):
    """
    Обработчик команды /stats. Показывает статистику пользователя.

    :param update: Объект обновления Telegram
    :type update: Update
    :param context: Контекст выполнения
    :type context: ContextTypes
    :returns: None
    """
    user = update.effective_user

    user_db_id = db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )

    stats = db.get_user_stats(user_db_id)

    message = f"""{EMOJI['chart']} Твоя статистика:

{EMOJI['book']} Всего книг: {stats['total']}
{EMOJI['calendar']} Запланировано: {stats['planned']}
{EMOJI['read']} Читаю сейчас: {stats['reading']}
{EMOJI['check']} Прочитано: {stats['completed']}
{EMOJI['cross']} Брошено: {stats['dropped']}"""

    if stats['avg_rating'] > 0:
        message += f"\n{EMOJI['star']} Средняя оценка: {stats['avg_rating']:.1f}"

    keyboard = [
        [InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks"),
         InlineKeyboardButton(f"{EMOJI['star']} Оценить книгу", callback_data="rate_book")]
    ]

    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


async def top_command(update: Update, context):
    """
    Обработчик команды /top. Показывает топ книг.

    :param update: Объект обновления Telegram
    :type update: Update
    :param context: Контекст выполнения
    :type context: ContextTypes
    :returns: None
    """
    if not context.args:
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['star']} По рейтингу", callback_data="top_rating"),
             InlineKeyboardButton(f"{EMOJI['user']} По популярности", callback_data="top_popularity")],
            [InlineKeyboardButton(f"{EMOJI['search']} Поиск книг", callback_data="search")]
        ]
        await update.message.reply_text(f"{EMOJI['trophy']} Выбери критерий:",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
        return

    criteria = context.args[0].lower()
    filter_by = context.args[1] if len(context.args) > 1 else ""

    if criteria not in ['rating', 'popularity']:
        await update.message.reply_text(f"{EMOJI['cross']} Используй: /top rating  или  /top popularity")
        return

    await show_top_books(update, criteria, filter_by)


async def handle_text_message(update: Update, context):
    """
    Обработчик текстовых сообщений.

    :param update: Объект обновления Telegram
    :type update: Update
    :param context: Контекст выполнения
    :type context: ContextTypes
    :returns: None
    """
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id in ADD_BOOK_STATES:
        state = ADD_BOOK_STATES[user_id]
        step = state.get('step', 0)

        if step == 1:
            state['title'] = text
            state['step'] = 2
            ADD_BOOK_STATES[user_id] = state

            await update.message.reply_text(
                f"Название: {text}\n\n"
                "2️⃣ Отправьте автора книги:\n"
                "(например: Михаил Булгаков)"
            )

        elif step == 2:
            state['author'] = text
            state['step'] = 3
            ADD_BOOK_STATES[user_id] = state

            await update.message.reply_text(
                f"Автор: {text}\n\n"
                "3️⃣ Отправьте количество страниц (только число):\n"
                "(например: 480)"
            )

        elif step == 3:
            try:
                pages = int(text)
                if pages <= 0:
                    await update.message.reply_text(
                        f"{EMOJI['cross']} Количество страниц должно быть положительным числом! Попробуйте снова:")
                    return

                state['pages'] = pages
                state['step'] = 4
                ADD_BOOK_STATES[user_id] = state

                await update.message.reply_text(
                    f"Страниц: {pages}\n\n"
                    "4️⃣ Отправьте жанр книги:\n"
                    "(например: Классика, Фэнтези, Детектив)"
                )
            except ValueError:
                await update.message.reply_text(
                    f"{EMOJI['cross']} Количество страниц должно быть числом! Попробуйте снова:")

        elif step == 4:
            state['genre'] = text
            state['step'] = 5
            ADD_BOOK_STATES[user_id] = state

            await update.message.reply_text(
                f"Жанр: {text}\n\n"
                "5️⃣ Отправьте описание книги (можно пропустить, отправив '-'):\n"
                "(например: Роман о писателе и его возлюбленной)"
            )

        elif step == 5:
            description = "" if text == "-" else text

            title = state['title']
            author = state['author']
            pages = state['pages']
            genre = state['genre']

            del ADD_BOOK_STATES[user_id]

            success, book_id, message = db.add_book_to_catalog_simple(title, author, pages, genre, description)

            if not success:
                if "уже есть" in message.lower():
                    await update.message.reply_text(
                        f"{message}\n\n"
                        f"{EMOJI['plus']} Добавить себе: /add {book_id}"
                    )
                else:
                    await update.message.reply_text(f"{EMOJI['cross']} Ошибка при добавлении книги: {message}")
                return

            response = f"""{EMOJI['check']} Книга добавлена в каталог!

{EMOJI['list']} ID: {book_id}
{EMOJI['book']} Название: {title}
{EMOJI['user']} Автор: {author}
{EMOJI['list']} Страниц: {pages}
{EMOJI['folder']} Жанр: {genre}"""

            if description:
                response += f"\n{EMOJI['info']} Описание: {description}"

            response += f"\n\n{EMOJI['plus']} Добавить себе: /add {book_id}"

            await update.message.reply_text(response)

            print(f"Добавлена новая книга (пошагово): '{title}' - '{author}' (ID: {book_id})")

        return

    if len(text) >= 2:
        books = db.search_books_by_text(text)

        if not books:
            keyboard = [
                [InlineKeyboardButton(f"{EMOJI['search']} Попробовать другой", callback_data="search"),
                 InlineKeyboardButton(f"{EMOJI['home']} Главное меню", callback_data="main_menu")]
            ]

            await update.message.reply_text(f"{EMOJI['mail']} По запросу '{text}' ничего не найдено.",
                                            reply_markup=InlineKeyboardMarkup(keyboard))
            return

        message = f"{EMOJI['search']} Найдено по запросу '{text}':\n"

        keyboard_buttons = []
        for i, book in enumerate(books, 1):
            stats = db.get_book_stats(book['id'])
            rating = f" {EMOJI['star']}{stats['avg_rating']:.1f}" if stats['avg_rating'] > 0 else ""

            message += f"\n{i}. {book['title']}"
            message += f"\n   {EMOJI['user']} {book['author']}{rating} (ID: {book['id']})"

            short = book['title'][:12] + "..." if len(book['title']) > 12 else book['title']
            keyboard_buttons.append([
                InlineKeyboardButton(f"{EMOJI['plus']} Добавить '{short}'", callback_data=f"add_{book['id']}")
            ])

        keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['search']} Новый поиск", callback_data="search")])
        keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['home']} Главное меню", callback_data="main_menu")])

        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard_buttons))


async def button_handler(update: Update, context):
    """
    Обработчик callback-запросов от inline-кнопок.

    :param update: Объект обновления Telegram
    :type update: Update
    :param context: Контекст выполнения
    :type context: ContextTypes
    :returns: None
    """
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    data = query.data

    user_db_id = db.get_or_create_user(
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
            [InlineKeyboardButton(f"{EMOJI['info']} Статистика", callback_data="stats")],
            [InlineKeyboardButton(f"{EMOJI['star']} Оценить книгу", callback_data="rate_book")],
            [InlineKeyboardButton(f"{EMOJI['help']} Помощь", callback_data="help")]
        ]
        await query.edit_message_text(f"{EMOJI['home']} Главное меню\n\nВыбери действие:",
                                      reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "mybooks":
        books = db.get_user_books(user_db_id)

        if not books:
            keyboard = [
                [InlineKeyboardButton(f"{EMOJI['plus']} Добавить книгу", callback_data="add_book"),
                 InlineKeyboardButton(f"{EMOJI['search']} Найти книгу", callback_data="search")],
                [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text(f"{EMOJI['mail']} У тебя пока нет книг.",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            return

        planned = []
        reading = []
        completed = []
        dropped = []

        for book in books:
            if book['status'] == 'planned':
                planned.append(book)
            elif book['status'] == 'reading':
                reading.append(book)
            elif book['status'] == 'completed':
                completed.append(book)
            elif book['status'] == 'dropped':
                dropped.append(book)

        message = f"{EMOJI['book']} Твои книги:\n"

        if reading:
            message += f"\n{EMOJI['read']} Читаю сейчас ({len(reading)}):"
            for i, book in enumerate(reading[:3], 1):
                prog = (book['current_page'] / book['total_pages']) * 100 if book['total_pages'] else 0
                short = book['title'][:15] + "..." if len(book['title']) > 15 else book['title']
                message += f"\n{i}. {short} - {prog:.0f}%"

        if planned:
            message += f"\n\n{EMOJI['calendar']} Запланировано ({len(planned)}):"
            for i, book in enumerate(planned[:3], 1):
                short = book['title'][:15] + "..." if len(book['title']) > 15 else book['title']
                message += f"\n{i}. {short}"

        if completed:
            message += f"\n\n{EMOJI['check']} Прочитано ({len(completed)}):"
            for i, book in enumerate(completed[:3], 1):
                short = book['title'][:15] + "..." if len(book['title']) > 15 else book['title']
                rating = f" {EMOJI['star']}{book['rating']}" if book['rating'] else ""
                message += f"\n{i}. {short}{rating}"

        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['search']} Найти книгу", callback_data="search"),
             InlineKeyboardButton(f"{EMOJI['plus']} Добавить книгу", callback_data="add_book")],
            [InlineKeyboardButton(f"{EMOJI['chart']} Статистика", callback_data="stats"),
             InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")]
        ]

        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "search":
        await show_search_menu(query)

    elif data == "add_book":
        popular = db.get_popular_books(limit=5)

        if not popular:
            keyboard = [
                [InlineKeyboardButton(f"{EMOJI['search']} Найти книгу", callback_data="search"),
                 InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text(f"{EMOJI['mail']} Нет популярных книг.",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            return

        keyboard_buttons = []
        for book in popular:
            short = book['title'][:15] + "..." if len(book['title']) > 15 else book['title']
            keyboard_buttons.append([
                InlineKeyboardButton(f"{EMOJI['read']} {short}", callback_data=f"add_{book['id']}")
            ])

        keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['search']} Найти другую", callback_data="search")])
        keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")])

        await query.edit_message_text(f"{EMOJI['book']} Выбери книгу для добавления:",
                                      reply_markup=InlineKeyboardMarkup(keyboard_buttons))

    elif data == "start_reading":
        planned_books = db.get_user_books(user_db_id, "planned")

        if not planned_books:
            keyboard = [
                [InlineKeyboardButton(f"{EMOJI['plus']} Добавить книгу", callback_data="add_book"),
                 InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")],
                [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text(f"{EMOJI['mail']} Нет запланированных книг.",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            return

        keyboard_buttons = []
        for book in planned_books[:5]:
            short = book['title'][:15] + "..." if len(book['title']) > 15 else book['title']
            keyboard_buttons.append([
                InlineKeyboardButton(f"{EMOJI['read']} {short}", callback_data=f"start_{book['book_id']}")
            ])

        keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['book']} Все книги", callback_data="mybooks")])
        keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")])

        await query.edit_message_text(f"{EMOJI['book']} Выбери книгу для чтения:",
                                      reply_markup=InlineKeyboardMarkup(keyboard_buttons))

    elif data == "stats":
        stats = db.get_user_stats(user_db_id)

        message = f"""{EMOJI['chart']} Твоя статистика:

{EMOJI['book']} Всего книг: {stats['total']}
{EMOJI['calendar']} Запланировано: {stats['planned']}
{EMOJI['read']} Читаю сейчас: {stats['reading']}
{EMOJI['check']} Прочитано: {stats['completed']}
{EMOJI['cross']} Брошено: {stats['dropped']}"""

        if stats['avg_rating'] > 0:
            message += f"\n{EMOJI['star']} Средняя оценка: {stats['avg_rating']:.1f}"

        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks"),
             InlineKeyboardButton(f"{EMOJI['star']} Оценить книгу", callback_data="rate_book")],
            [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")]
        ]

        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "rate_book":
        completed_books = db.get_user_books(user_db_id, "completed")

        if not completed_books:
            keyboard = [
                [InlineKeyboardButton(f"{EMOJI['read']} Начать читать", callback_data="start_reading"),
                 InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")],
                [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text(f"{EMOJI['mail']} Нет прочитанных книг для оценки.",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            return

        keyboard_buttons = []
        for book in completed_books[:3]:
            if book['rating']:
                short = book['title'][:10] + "..." if len(book['title']) > 10 else book['title']
                keyboard_buttons.append([
                    InlineKeyboardButton(f"{EMOJI['star']} {book['rating']}/5 - {short}", callback_data="no_action")
                ])
            else:
                short = book['title'][:15] + "..." if len(book['title']) > 15 else book['title']
                keyboard_buttons.append([
                    InlineKeyboardButton(f"{EMOJI['book']} {short}", callback_data=f"rateshow_{book['book_id']}")
                ])

        keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")])
        keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")])

        await query.edit_message_text(f"{EMOJI['star']} Выбери книгу для оценки:",
                                      reply_markup=InlineKeyboardMarkup(keyboard_buttons))

    elif data.startswith("rateshow_"):
        try:
            book_id = int(data.replace("rateshow_", ""))
            book = db.get_book(book_id)

            if not book:
                await query.edit_message_text(f"{EMOJI['cross']} Книга не найдена.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="rate_book")]
                ]))
                return

            keyboard_buttons = []
            row = []
            for r in range(1, 6):
                row.append(InlineKeyboardButton(f"{r}{EMOJI['star']}", callback_data=f"rate_{book_id}_{r}"))
            keyboard_buttons.append(row)

            keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="rate_book")])

            await query.edit_message_text(
                f"{EMOJI['star']} Оцени книгу:\n\n{book['title']}\n{EMOJI['user']} {book['author']}",
                reply_markup=InlineKeyboardMarkup(keyboard_buttons)
            )
        except:
            await query.edit_message_text(f"{EMOJI['cross']} Ошибка.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="rate_book")]
            ]))

    elif data.startswith("ratebook_"):
        try:
            book_id = int(data.replace("ratebook_", ""))
            book = db.get_book(book_id)

            if not book:
                await query.edit_message_text(f"{EMOJI['cross']} Книга не найдена.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="mybooks")]
                ]))
                return

            keyboard_buttons = []
            row = []
            for r in range(1, 6):
                row.append(InlineKeyboardButton(f"{r}{EMOJI['star']}", callback_data=f"rate_{book_id}_{r}"))
            keyboard_buttons.append(row)

            keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="mybooks")])

            await query.edit_message_text(
                f"{EMOJI['star']} Оцени прочитанную книгу:\n\n{book['title']}\n{EMOJI['user']} {book['author']}",
                reply_markup=InlineKeyboardMarkup(keyboard_buttons)
            )
        except:
            await query.edit_message_text(f"{EMOJI['cross']} Ошибка.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="mybooks")]
            ]))

    elif data == "help":
        help_text = f"""{EMOJI['book']} BookBot - помощник для учета книг

{EMOJI['read']} Как пользоваться:
1. Добавь книгу через "{EMOJI['plus']} Добавить книгу"
2. Начни чтение через "{EMOJI['read']} Начать читать"
3. Обновляй прогресс: /progress <id> <страница>
4. Закончив, оцени книгу

{EMOJI['list']} Команды:
/start - Главное меню
/help - Справка
/progress <ID> <страница> - Обновить прогресс
/add <ID> - Добавить книгу по ID
/addbook - Добавить новую книгу в каталог
/search <запрос> - Поиск книг
/stats - Статистика
/top <rating|popularity> [жанр] - Топ книги"""

        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks"),
             InlineKeyboardButton(f"{EMOJI['search']} Поиск", callback_data="search")],
            [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")]
        ]

        await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("search_"):
        genre = data.replace("search_", "")

        if genre == "input":
            await query.edit_message_text("📝 Введи название или автора:", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="search")]
            ]))
            return

        await do_search(query, "", genre)

    elif data.startswith("add_"):
        try:
            book_id = int(data.replace("add_", ""))
            book = db.get_book(book_id)

            if not book:
                await query.edit_message_text(f"{EMOJI['cross']} Книга не найдена.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="add_book")]
                ]))
                return

            if db.add_user_book(user_db_id, book_id, "planned"):
                keyboard = [
                    [InlineKeyboardButton(f"{EMOJI['read']} Начать читать", callback_data=f"start_{book_id}"),
                     InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")],
                    [InlineKeyboardButton(f"{EMOJI['plus']} Добавить еще", callback_data="add_book"),
                     InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")]
                ]

                await query.edit_message_text(
                    f"""{EMOJI['check']} Книга добавлена!

{book['title']}
{EMOJI['user']} {book['author']}
{EMOJI['list']} {book['total_pages']} стр.
{EMOJI['folder']} Статус: Запланировано""",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(
                    f"{EMOJI['cross']} Эта книга уже есть в твоём списке.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="add_book")]
                    ])
                )
        except:
            await query.edit_message_text(f"{EMOJI['cross']} Ошибка.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="add_book")]
            ]))

    elif data.startswith("start_"):
        try:
            book_id = int(data.replace("start_", ""))

            if not db.has_book(user_db_id, book_id):
                await query.edit_message_text(f"{EMOJI['cross']} У тебя нет этой книги.",
                                              reply_markup=InlineKeyboardMarkup([
                                                  [InlineKeyboardButton(f"{EMOJI['prev']} Назад",
                                                                        callback_data="start_reading")]
                                              ]))
                return

            if db.update_book_status(user_db_id, book_id, "reading"):
                book = db.get_book(book_id)

                keyboard = [
                    [InlineKeyboardButton(f"{EMOJI['chart']} Обновить прогресс", callback_data=f"progress_{book_id}"),
                     InlineKeyboardButton(f"{EMOJI['check']} Закончить", callback_data=f"finish_{book_id}")],
                    [InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks"),
                     InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")]
                ]

                await query.edit_message_text(
                    f"""{EMOJI['read']} Начинаем читать!

{book['title']}
{EMOJI['user']} {book['author']}
{EMOJI['list']} Всего страниц: {book['total_pages']}

Чтобы обновить прогресс:
/progress {book_id} <страница>""",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(f"{EMOJI['cross']} Ошибка.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="start_reading")]
                ]))
        except:
            await query.edit_message_text(f"{EMOJI['cross']} Ошибка.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="start_reading")]
            ]))

    elif data.startswith("rate_"):
        try:
            parts = data.replace("rate_", "").split("_")
            if len(parts) == 2:
                book_id = int(parts[0])
                rating = int(parts[1])

                if db.rate_book(user_db_id, book_id, rating):
                    book = db.get_book(book_id)
                    stats = db.get_book_stats(book_id)

                    keyboard = [
                        [InlineKeyboardButton(f"{EMOJI['star']} Оценить другую", callback_data="rate_book"),
                         InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")],
                        [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")]
                    ]

                    stars = f"{EMOJI['star']}" * rating
                    rating_text = f"{stars} ({rating}/5)"
                    avg_rating = f"{stats['avg_rating']:.1f}" if stats['avg_rating'] else "0.0"

                    await query.edit_message_text(
                        f"""{EMOJI['check']} Оценка поставлена!

{book['title']}
{rating_text}

{EMOJI['chart']} Общий рейтинг книги: {avg_rating}/5
({stats['rating_count']} оценок)""",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await query.edit_message_text(f"{EMOJI['cross']} Ошибка.", reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="rate_book")]
                    ]))
        except:
            await query.edit_message_text(f"{EMOJI['cross']} Ошибка.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="rate_book")]
            ]))

    elif data.startswith("progress_"):
        book_id = int(data.replace("progress_", ""))
        await query.edit_message_text(
            f"{EMOJI['chart']} Чтобы обновить прогресс:\n/progress {book_id} <страница>\n\nПример: /progress {book_id} 150",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="mybooks")]
            ])
        )

    elif data.startswith("finish_"):
        try:
            book_id = int(data.replace("finish_", ""))

            if not db.has_book(user_db_id, book_id):
                await query.edit_message_text(f"{EMOJI['cross']} У тебя нет этой книги.",
                                              reply_markup=InlineKeyboardMarkup([
                                                  [InlineKeyboardButton(f"{EMOJI['prev']} Назад",
                                                                        callback_data="mybooks")]
                                              ]))
                return

            if db.update_book_status(user_db_id, book_id, "completed"):
                book = db.get_book(book_id)

                keyboard = [
                    [InlineKeyboardButton(f"{EMOJI['star']} Оценить книгу", callback_data=f"ratebook_{book_id}"),
                     InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks")],
                    [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="main_menu")]
                ]

                await query.edit_message_text(
                    f"""{EMOJI['wow']} Поздравляю с прочтением!

{book['title']}
{EMOJI['user']} {book['author']}""",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(f"{EMOJI['cross']} Ошибка.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="mybooks")]
                ]))
        except:
            await query.edit_message_text(f"{EMOJI['cross']} Ошибка.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{EMOJI['prev']} Назад", callback_data="mybooks")]
            ]))

    elif data.startswith("top_"):
        criteria = data.replace("top_", "")
        await show_top_books(query, criteria)

    elif data == "no_action":
        pass


async def show_search_menu(upd):
    """
    Показывает меню поиска книг.

    :param upd: Объект Update или CallbackQuery
    :type upd: Update or CallbackQuery
    :returns: None
    """
    genres = db.get_all_genres()

    keyboard_buttons = []
    for i in range(0, min(len(genres), 6), 2):
        row = []
        row.append(InlineKeyboardButton(f"{EMOJI['folder']} {genres[i]}", callback_data=f"search_{genres[i]}"))
        if i + 1 < len(genres):
            row.append(
                InlineKeyboardButton(f"{EMOJI['folder']} {genres[i + 1]}", callback_data=f"search_{genres[i + 1]}"))
        keyboard_buttons.append(row)

    keyboard_buttons.append(
        [InlineKeyboardButton(f"{EMOJI['search']} Поиск по названию", callback_data="search_input")])
    keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['home']} Главное меню", callback_data="main_menu")])

    text = f"{EMOJI['search']} Выбери жанр или поиск:"

    if hasattr(upd, 'edit_message_text'):
        await upd.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    else:
        await upd.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard_buttons))


async def do_search(upd, query, genre):
    """
    Выполняет поиск книг.

    :param upd: Объект Update или CallbackQuery
    :type upd: Update or CallbackQuery
    :param query: Текстовый запрос
    :type query: str
    :param genre: Жанр для фильтрации
    :type genre: str
    :returns: None
    """
    books = db.search_books(query, genre, 10)

    if not books:
        if query:
            msg = f"{EMOJI['mail']} По запросу '{query}' ничего нет."
        else:
            msg = f"{EMOJI['mail']} В жанре '{genre}' ничего нет."

        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['search']} Новый поиск", callback_data="search"),
             InlineKeyboardButton(f"{EMOJI['home']} Главное меню", callback_data="main_menu")]
        ]

        if hasattr(upd, 'edit_message_text'):
            await upd.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await upd.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if query:
        title = f"{EMOJI['search']} Найдено по '{query}':"
    else:
        title = f"{EMOJI['search']} Книги в жанре '{genre}':"

    message = f"{title}\n"

    keyboard_buttons = []
    for i, book in enumerate(books, 1):
        stats = db.get_book_stats(book['id'])
        rating = f" {EMOJI['star']}{stats['avg_rating']:.1f}" if stats['avg_rating'] > 0 else ""

        message += f"\n{i}. {book['title']}"
        message += f"\n   {EMOJI['user']} {book['author']}{rating}"
        message += f"\n   {EMOJI['chart']} Добавили: {stats['total_added']} чел. | Читают сейчас: {stats['currently_reading']} чел. (ID: {book['id']})"

        short = book['title'][:12] + "..." if len(book['title']) > 12 else book['title']
        keyboard_buttons.append([
            InlineKeyboardButton(f"{EMOJI['plus']} Добавить '{short}'", callback_data=f"add_{book['id']}")
        ])

    keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['search']} Новый поиск", callback_data="search")])
    keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['home']} Главное меню", callback_data="main_menu")])

    if hasattr(upd, 'edit_message_text'):
        await upd.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    else:
        await upd.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard_buttons))


async def show_top_books(upd, criteria, filter_by=""):
    """
    Показывает топ книг по заданному критерию.

    :param upd: Объект Update или CallbackQuery
    :type upd: Update or CallbackQuery
    :param criteria: Критерий сортировки ("rating" или "popularity")
    :type criteria: str
    :param filter_by: Фильтр (жанр или автор)
    :type filter_by: str
    :returns: None
    """
    genres = db.get_all_genres()
    genre = filter_by if filter_by in genres else ""
    author = filter_by if not genre and filter_by else ""

    books = db.get_top_books(criteria, genre, author, 5)

    if not books:
        msg = f"{EMOJI['mail']} Нет книг по этому критерию."
        if genre:
            msg = f"{EMOJI['mail']} В жанре '{genre}' ничего нет."

        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['trophy']} Другой критерий", callback_data="top_books"),
             InlineKeyboardButton(f"{EMOJI['home']} Главное меню", callback_data="main_menu")]
        ]

        if hasattr(upd, 'edit_message_text'):
            await upd.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await upd.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if criteria == 'rating':
        title = f"{EMOJI['trophy']} Книги с лучшим рейтингом"
    else:
        title = f"{EMOJI['trophy']} Самые популярные книги"

    if genre:
        title += f" ({genre})"

    message = f"{title}:\n"

    keyboard_buttons = []
    for i, book in enumerate(books, 1):
        stats = db.get_book_stats(book['id'])

        if criteria == 'rating':
            rating = stats['avg_rating']
            count = stats['rating_count']
            line = f"{i}. {book['title']} - {EMOJI['star']} {rating:.1f}/5 ({count} оценок)"
        else:
            added = stats['total_added']
            line = f"{i}. {book['title']} - {EMOJI['user']} {added} читателей"

        message += f"\n{line}"
        message += f"\n   {EMOJI['user']} {book['author']} (ID: {book['id']})"

        short = book['title'][:12] + "..." if len(book['title']) > 12 else book['title']
        keyboard_buttons.append([
            InlineKeyboardButton(f"{EMOJI['plus']} Добавить '{short}'", callback_data=f"add_{book['id']}")
        ])

    keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['star']} По рейтингу", callback_data="top_rating"),
                             InlineKeyboardButton(f"{EMOJI['user']} По популярности", callback_data="top_popularity")])
    keyboard_buttons.append([InlineKeyboardButton(f"{EMOJI['search']} Поиск книг", callback_data="search"),
                             InlineKeyboardButton(f"{EMOJI['home']} Главное меню", callback_data="main_menu")])

    if hasattr(upd, 'edit_message_text'):
        await upd.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    else:
        await upd.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard_buttons))


async def error_handler(update: Update, context):
    """
    Глобальный обработчик ошибок.

    :param update: Объект обновления Telegram
    :type update: Update
    :param context: Контекст выполнения
    :type context: ContextTypes
    :returns: None
    """
    try:
        keyboard = [
            [InlineKeyboardButton(f"{EMOJI['book']} Мои книги", callback_data="mybooks"),
             InlineKeyboardButton(f"{EMOJI['home']} Главное меню", callback_data="main_menu")]
        ]

        await update.message.reply_text("Произошла ошибка. Попробуй еще раз.",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        pass


def main():
    """
    Основная функция запуска бота.

    :returns: None
    """
    print(" BookBot запускается...")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("progress", progress_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("addbook", addbook_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("top", top_command))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    app.add_error_handler(error_handler)

    print(" Бот запущен!")

    app.run_polling()


if __name__ == '__main__':
    main()
