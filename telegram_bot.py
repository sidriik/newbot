#!/usr/bin/env python3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from database import Database

TOKEN = "8371793740:AAGyHz10Ro6JabxomkyjDGsjWhNaf3SUeMI"

db = Database()

# Состояния для пошагового добавления книги
ADD_BOOK_STATES = {}


# ========== КОМАНДЫ ==========

async def start_command(update: Update, context):
    user = update.effective_user
    
    user_id = db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    text = f"""👋 Привет, {user.first_name}!

Я — BookBot, помогу вести список книг.

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
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def help_command(update: Update, context):
    help_text = """📚 BookBot - помощник для учета книг

📋 Команды:
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
        [InlineKeyboardButton("📚 Главное меню", callback_data="main_menu"),
         InlineKeyboardButton("🔍 Поиск книг", callback_data="search")]
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
        
        user_db_id = db.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        
        book_info = db.get_book_info(user_db_id, book_id)
        if not book_info:
            await update.message.reply_text("У тебя нет этой книги.")
            return
        
        if book_info['status'] != 'reading':
            await update.message.reply_text("Эту книгу ты сейчас не читаешь.")
            return
        
        book = db.get_book(book_id)
        if not book:
            await update.message.reply_text("Книга не найдена.")
            return
        
        if page > book['total_pages']:
            await update.message.reply_text(f"В книге всего {book['total_pages']} страниц!")
            return
        
        ok = db.update_progress(user_db_id, book_id, page)
        if not ok:
            await update.message.reply_text("Ошибка обновления.")
            return
        
        progress = (page / book['total_pages']) * 100
        
        if progress >= 100:
            db.update_book_status(user_db_id, book_id, 'completed')
            message = f"""🎉 Поздравляю! Прочитал книгу!

{book['title']}
👤 {book['author']}

Страниц: {page}/{book['total_pages']} (100%)"""
            keyboard = [[
                InlineKeyboardButton("⭐ Оценить книгу", callback_data=f"ratebook_{book_id}"),
                InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")
            ]]
        else:
            message = f"""📖 Прогресс обновлен!

{book['title']}
👤 {book['author']}

Страница: {page} из {book['total_pages']}
Прогресс: {progress:.1f}%"""
            keyboard = [[
                InlineKeyboardButton("📊 Еще обновить", callback_data=f"progress_{book_id}"),
                InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")
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
        
        user_db_id = db.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        
        book = db.get_book(book_id)
        if not book:
            await update.message.reply_text(f"Книга {book_id} не найдена.")
            return
        
        ok = db.add_user_book(user_db_id, book_id, 'planned')
        
        if not ok:
            await update.message.reply_text("Эта книга уже есть.")
            return
        
        message = f"""✅ Книга добавлена!

{book['title']}
👤 {book['author']}
📄 {book['total_pages']} стр.
📂 Статус: Запланировано"""
        
        keyboard = [
            [InlineKeyboardButton("📖 Начать читать", callback_data=f"start_{book_id}"),
             InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton("➕ Добавить еще", callback_data="add_book")]
        ]
        
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except ValueError:
        await update.message.reply_text("ID должен быть числом.")
    except Exception as e:
        await update.message.reply_text("Ошибка.")
        print(f"Ошибка /add: {e}")


async def addbook_command(update: Update, context):
    """Добавить новую книгу в общий каталог (упрощенная версия)."""
    user_id = update.effective_user.id
    
    # Если есть аргументы - пробуем добавить сразу
    if context.args and len(context.args) >= 4:
        try:
            # Простой парсинг - объединяем аргументы
            args = context.args
            
            # Первые 4 аргумента обязательные
            if len(args) < 4:
                await update.message.reply_text(
                    "❌ Недостаточно аргументов! Нужно: название, автор, страницы, жанр\n\n"
                    "Пример: /addbook Мастер_и_Маргарита Михаил_Булгаков 480 Классика\n\n"
                    "Или используйте /addbook без аргументов для пошагового добавления"
                )
                return
            
            # Извлекаем аргументы
            title = args[0].replace('_', ' ').strip()
            author = args[1].replace('_', ' ').strip()
            
            try:
                pages = int(args[2])
                if pages <= 0:
                    await update.message.reply_text("❌ Количество страниц должно быть положительным числом!")
                    return
            except ValueError:
                await update.message.reply_text("❌ Количество страниц должно быть числом!")
                return
            
            genre = args[3].replace('_', ' ').strip()
            
            # Описание (необязательное)
            description = ""
            if len(args) > 4:
                desc_parts = args[4:]
                description = " ".join(desc_parts).replace('_', ' ').strip()
            
            # Проверяем, что название и автор не пустые
            if not title or not author:
                await update.message.reply_text("❌ Название и автор не могут быть пустыми!")
                return
            
            # Используем метод из Database для добавления книги
            success, book_id, message = db.add_book_to_catalog_simple(title, author, pages, genre, description)
            
            if not success:
                # Если книга уже существует, показываем ID
                if "уже есть" in message.lower():
                    await update.message.reply_text(
                        f"{message}\n\n"
                        f"Добавить себе: /add {book_id}"
                    )
                else:
                    await update.message.reply_text(message)
                return
            
            # Показываем результат (БЕЗ EMOJI в начале, чтобы избежать ошибки кодировки)
            response = f"""Книга добавлена в каталог!

📖 ID: {book_id}
📚 Название: {title}
👤 Автор: {author}
📄 Страниц: {pages}
📂 Жанр: {genre}"""
            
            if description:
                response += f"\n📝 Описание: {description}"
            
            response += f"\n\n💡 Добавить себе: /add {book_id}"
            
            await update.message.reply_text(response)
            
            print(f"Добавлена новая книга: '{title}' - '{author}' (ID: {book_id})")
            
            return
            
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {str(e)}")
            print(f"Ошибка в /addbook (прямой вызов): {e}")
            return
    
    # Если нет аргументов - начинаем пошаговое добавление
    ADD_BOOK_STATES[user_id] = {'step': 1}
    
    await update.message.reply_text(
        "📚 Добавление новой книги в каталог\n\n"
        "Давайте добавим книгу по шагам!\n\n"
        "1️⃣ Отправьте название книги:\n"
        "(например: Мастер и Маргарита)"
    )


async def search_command(update: Update, context):
    if not context.args:
        await show_search_menu(update)
        return
    
    query = " ".join(context.args)
    await do_search(update, query, "")


async def stats_command(update: Update, context):
    user = update.effective_user
    
    user_db_id = db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    stats = db.get_user_stats(user_db_id)
    
    message = f"""📊 Твоя статистика:

📚 Всего книг: {stats['total']}
📅 Запланировано: {stats['planned']}
📖 Читаю сейчас: {stats['reading']}
✅ Прочитано: {stats['completed']}
❌ Брошено: {stats['dropped']}"""
    
    if stats['avg_rating'] > 0:
        message += f"\n⭐ Средняя оценка: {stats['avg_rating']:.1f}"
    
    keyboard = [
        [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
         InlineKeyboardButton("⭐ Оценить книгу", callback_data="rate_book")]
    ]
    
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


async def top_command(update: Update, context):
    if not context.args:
        keyboard = [
            [InlineKeyboardButton("⭐ По рейтингу", callback_data="top_rating"),
             InlineKeyboardButton("👥 По популярности", callback_data="top_popularity")],
            [InlineKeyboardButton("🔍 Поиск книг", callback_data="search")]
        ]
        await update.message.reply_text("🏆 Выбери критерий:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    criteria = context.args[0].lower()
    filter_by = context.args[1] if len(context.args) > 1 else ""
    
    if criteria not in ['rating', 'popularity']:
        await update.message.reply_text("Используй: /top rating  или  /top popularity")
        return
    
    await show_top_books(update, criteria, filter_by)


# ========== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ==========

async def handle_text_message(update: Update, context):
    """Обработка текстовых сообщений."""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Проверяем, находится ли пользователь в процессе добавления книги
    if user_id in ADD_BOOK_STATES:
        state = ADD_BOOK_STATES[user_id]
        step = state.get('step', 0)
        
        if step == 1:  # Ждем название
            state['title'] = text
            state['step'] = 2
            ADD_BOOK_STATES[user_id] = state
            
            await update.message.reply_text(
                f"Название: {text}\n\n"
                "2️⃣ Отправьте автора книги:\n"
                "(например: Михаил Булгаков)"
            )
            
        elif step == 2:  # Ждем автора
            state['author'] = text
            state['step'] = 3
            ADD_BOOK_STATES[user_id] = state
            
            await update.message.reply_text(
                f"Автор: {text}\n\n"
                "3️⃣ Отправьте количество страниц (только число):\n"
                "(например: 480)"
            )
            
        elif step == 3:  # Ждем количество страниц
            try:
                pages = int(text)
                if pages <= 0:
                    await update.message.reply_text("❌ Количество страниц должно быть положительным числом! Попробуйте снова:")
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
                await update.message.reply_text("❌ Количество страниц должно быть числом! Попробуйте снова:")
                
        elif step == 4:  # Ждем жанр
            state['genre'] = text
            state['step'] = 5
            ADD_BOOK_STATES[user_id] = state
            
            await update.message.reply_text(
                f"Жанр: {text}\n\n"
                "5️⃣ Отправьте описание книги (можно пропустить, отправив '-'):\n"
                "(например: Роман о писателе и его возлюбленной)"
            )
            
        elif step == 5:  # Ждем описание
            description = "" if text == "-" else text
            
            # Получаем все данные
            title = state['title']
            author = state['author']
            pages = state['pages']
            genre = state['genre']
            
            # Удаляем состояние
            del ADD_BOOK_STATES[user_id]
            
            # Добавляем книгу в базу
            success, book_id, message = db.add_book_to_catalog_simple(title, author, pages, genre, description)
            
            if not success:
                # Если книга уже существует
                if "уже есть" in message.lower():
                    await update.message.reply_text(
                        f"{message}\n\n"
                        f"Добавить себе: /add {book_id}"
                    )
                else:
                    await update.message.reply_text(f"Ошибка при добавлении книги: {message}")
                return
            
            # Показываем результат (БЕЗ EMOJI в начале)
            response = f"""Книга добавлена в каталог!

📖 ID: {book_id}
📚 Название: {title}
👤 Автор: {author}
📄 Страниц: {pages}
📂 Жанр: {genre}"""
            
            if description:
                response += f"\n📝 Описание: {description}"
            
            response += f"\n\n💡 Добавить себе: /add {book_id}"
            
            await update.message.reply_text(response)
            
            print(f"Добавлена новая книга (пошагово): '{title}' - '{author}' (ID: {book_id})")
        
        return
    
    # Если это не пошаговое добавление книги, делаем обычный поиск
    if len(text) >= 2:
        books = db.search_books_by_text(text)
        
        if not books:
            keyboard = [
                [InlineKeyboardButton("🔍 Попробовать другой", callback_data="search"),
                 InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
            
            await update.message.reply_text(f"По запросу '{text}' ничего не найдено.", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        message = f"🔍 Найдено по запросу '{text}':\n"
        
        keyboard_buttons = []
        for i, book in enumerate(books, 1):
            stats = db.get_book_stats(book['id'])
            rating = f" ⭐{stats['avg_rating']:.1f}" if stats['avg_rating'] > 0 else ""
            
            message += f"\n{i}. {book['title']}"
            message += f"\n   👤 {book['author']}{rating} (ID: {book['id']})"
            
            short = book['title'][:12] + "..." if len(book['title']) > 12 else book['title']
            keyboard_buttons.append([
                InlineKeyboardButton(f"➕ Добавить '{short}'", callback_data=f"add_{book['id']}")
            ])
        
        keyboard_buttons.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="search")])
        keyboard_buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
        
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard_buttons))


# ========== КНОПКИ ==========

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    data = query.data
    
    user_db_id = db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    # Главное меню
    if data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton("🔍 Найти книгу", callback_data="search")],
            [InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book")],
            [InlineKeyboardButton("📖 Начать читать", callback_data="start_reading")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("⭐ Оценить книгу", callback_data="rate_book")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        await query.edit_message_text("📚 Главное меню\n\nВыбери действие:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Мои книги
    elif data == "mybooks":
        books = db.get_user_books(user_db_id)
        
        if not books:
            keyboard = [
                [InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book"),
                 InlineKeyboardButton("🔍 Найти книгу", callback_data="search")],
                [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text("📭 У тебя пока нет книг.", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        # Группируем по статусу
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
        
        message = "📚 Твои книги:\n"
        
        if reading:
            message += f"\n📖 Читаю сейчас ({len(reading)}):"
            for i, book in enumerate(reading[:3], 1):
                prog = (book['current_page'] / book['total_pages']) * 100 if book['total_pages'] else 0
                short = book['title'][:15] + "..." if len(book['title']) > 15 else book['title']
                message += f"\n{i}. {short} - {prog:.0f}%"
        
        if planned:
            message += f"\n\n📅 Запланировано ({len(planned)}):"
            for i, book in enumerate(planned[:3], 1):
                short = book['title'][:15] + "..." if len(book['title']) > 15 else book['title']
                message += f"\n{i}. {short}"
        
        if completed:
            message += f"\n\n✅ Прочитано ({len(completed)}):"
            for i, book in enumerate(completed[:3], 1):
                short = book['title'][:15] + "..." if len(book['title']) > 15 else book['title']
                rating = f" ⭐{book['rating']}" if book['rating'] else ""
                message += f"\n{i}. {short}{rating}"
        
        keyboard = [
            [InlineKeyboardButton("🔍 Найти книгу", callback_data="search"),
             InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats"),
             InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Поиск
    elif data == "search":
        await show_search_menu(query)
    
    # Добавить книгу (показываем популярные)
    elif data == "add_book":
        popular = db.get_popular_books(limit=5)
        
        if not popular:
            keyboard = [
                [InlineKeyboardButton("🔍 Найти книгу", callback_data="search"),
                 InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text("Нет популярных книг.", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        keyboard_buttons = []
        for book in popular:
            short = book['title'][:15] + "..." if len(book['title']) > 15 else book['title']
            keyboard_buttons.append([
                InlineKeyboardButton(f"📖 {short}", callback_data=f"add_{book['id']}")
            ])
        
        keyboard_buttons.append([InlineKeyboardButton("🔍 Найти другую", callback_data="search")])
        keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        await query.edit_message_text("📚 Выбери книгу для добавления:", reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    
    # Начать читать
    elif data == "start_reading":
        planned_books = db.get_user_books(user_db_id, "planned")
        
        if not planned_books:
            keyboard = [
                [InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book"),
                 InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
                [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text("📭 Нет запланированных книг.", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        keyboard_buttons = []
        for book in planned_books[:5]:
            short = book['title'][:15] + "..." if len(book['title']) > 15 else book['title']
            keyboard_buttons.append([
                InlineKeyboardButton(f"📖 {short}", callback_data=f"start_{book['book_id']}")
            ])
        
        keyboard_buttons.append([InlineKeyboardButton("📚 Все книги", callback_data="mybooks")])
        keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        await query.edit_message_text("📚 Выбери книгу для чтения:", reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    
    # Статистика
    elif data == "stats":
        stats = db.get_user_stats(user_db_id)
        
        message = f"""📊 Твоя статистика:

📚 Всего книг: {stats['total']}
📅 Запланировано: {stats['planned']}
📖 Читаю сейчас: {stats['reading']}
✅ Прочитано: {stats['completed']}
❌ Брошено: {stats['dropped']}"""
        
        if stats['avg_rating'] > 0:
            message += f"\n⭐ Средняя оценка: {stats['avg_rating']:.1f}"
        
        keyboard = [
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
             InlineKeyboardButton("⭐ Оценить книгу", callback_data="rate_book")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Оценить книгу (из меню)
    elif data == "rate_book":
        completed_books = db.get_user_books(user_db_id, "completed")
        
        if not completed_books:
            keyboard = [
                [InlineKeyboardButton("📖 Начать читать", callback_data="start_reading"),
                 InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
                [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text("📭 Нет прочитанных книг для оценки.", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        # Кнопки для оценки
        keyboard_buttons = []
        for book in completed_books[:3]:
            if book['rating']:
                short = book['title'][:10] + "..." if len(book['title']) > 10 else book['title']
                keyboard_buttons.append([
                    InlineKeyboardButton(f"⭐ {book['rating']}/5 - {short}", callback_data="no_action")
                ])
            else:
                short = book['title'][:15] + "..." if len(book['title']) > 15 else book['title']
                keyboard_buttons.append([
                    InlineKeyboardButton(f"📖 {short}", callback_data=f"rateshow_{book['book_id']}")
                ])
        
        keyboard_buttons.append([InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")])
        keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        await query.edit_message_text("⭐ Выбери книгу для оценки:", reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    
    # Показать оценки для конкретной книги
    elif data.startswith("rateshow_"):
        try:
            book_id = int(data.replace("rateshow_", ""))
            book = db.get_book(book_id)
            
            if not book:
                await query.edit_message_text("❌ Книга не найдена.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="rate_book")]
                ]))
                return
            
            keyboard_buttons = []
            row = []
            for r in range(1, 6):
                row.append(InlineKeyboardButton(f"{r}⭐", callback_data=f"rate_{book_id}_{r}"))
            keyboard_buttons.append(row)
            
            keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="rate_book")])
            
            await query.edit_message_text(
                f"⭐ Оцени книгу:\n\n{book['title']}\n👤 {book['author']}",
                reply_markup=InlineKeyboardMarkup(keyboard_buttons)
            )
        except:
            await query.edit_message_text("❌ Ошибка.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="rate_book")]
            ]))
    
    # Оценить книгу после прочтения
    elif data.startswith("ratebook_"):
        try:
            book_id = int(data.replace("ratebook_", ""))
            book = db.get_book(book_id)
            
            if not book:
                await query.edit_message_text("❌ Книга не найдена.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="mybooks")]
                ]))
                return
            
            keyboard_buttons = []
            row = []
            for r in range(1, 6):
                row.append(InlineKeyboardButton(f"{r}⭐", callback_data=f"rate_{book_id}_{r}"))
            keyboard_buttons.append(row)
            
            keyboard_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="mybooks")])
            
            await query.edit_message_text(
                f"⭐ Оцени прочитанную книгу:\n\n{book['title']}\n👤 {book['author']}",
                reply_markup=InlineKeyboardMarkup(keyboard_buttons)
            )
        except:
            await query.edit_message_text("❌ Ошибка.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="mybooks")]
            ]))
    
    # Помощь
    elif data == "help":
        help_text = """📚 BookBot - помощник для учета книг

📖 Как пользоваться:
1. Добавь книгу через "➕ Добавить книгу"
2. Начни чтение через "📖 Начать читать"
3. Обновляй прогресс: /progress <id> <страница>
4. Закончив, оцени книгу

📋 Команды:
/start - Главное меню
/progress <id> <страница> - Обновить прогресс
/search <запрос> - Поиск книг
/add <id> - Добавить книгу
/addbook - Добавить новую книгу в каталог"""
        
        keyboard = [
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
             InlineKeyboardButton("🔍 Поиск", callback_data="search")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Поиск по жанру
    elif data.startswith("search_"):
        genre = data.replace("search_", "")
        
        if genre == "input":
            await query.edit_message_text("📝 Введи название или автора:", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="search")]
            ]))
            return
        
        await do_search(query, "", genre)
    
    # Добавить конкретную книгу
    elif data.startswith("add_"):
        try:
            book_id = int(data.replace("add_", ""))
            book = db.get_book(book_id)
            
            if not book:
                await query.edit_message_text("❌ Книга не найдена.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="add_book")]
                ]))
                return
            
            if db.add_user_book(user_db_id, book_id, "planned"):
                keyboard = [
                    [InlineKeyboardButton("📖 Начать читать", callback_data=f"start_{book_id}"),
                     InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
                    [InlineKeyboardButton("➕ Добавить еще", callback_data="add_book"),
                     InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                ]
                
                await query.edit_message_text(
                    f"""✅ Книга добавлена!

{book['title']}
👤 {book['author']}
📄 {book['total_pages']} стр.
📂 Статус: Запланировано""",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(
                    "❌ Эта книга уже есть в твоём списке.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="add_book")]
                    ])
                )
        except:
            await query.edit_message_text("❌ Ошибка.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="add_book")]
            ]))
    
    # Начать читать конкретную книгу
    elif data.startswith("start_"):
        try:
            book_id = int(data.replace("start_", ""))
            
            if not db.has_book(user_db_id, book_id):
                await query.edit_message_text("❌ У тебя нет этой книги.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="start_reading")]
                ]))
                return
            
            if db.update_book_status(user_db_id, book_id, "reading"):
                book = db.get_book(book_id)
                
                keyboard = [
                    [InlineKeyboardButton("📊 Обновить прогресс", callback_data=f"progress_{book_id}"),
                     InlineKeyboardButton("✅ Закончить", callback_data=f"finish_{book_id}")],
                    [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
                     InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                ]
                
                await query.edit_message_text(
                    f"""📖 Начинаем читать!

{book['title']}
👤 {book['author']}
📄 Всего страниц: {book['total_pages']}

Чтобы обновить прогресс:
/progress {book_id} <страница>""",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text("❌ Ошибка.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="start_reading")]
                ]))
        except:
            await query.edit_message_text("❌ Ошибка.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="start_reading")]
            ]))
    
    # Оценить книгу (поставить оценку)
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
                        [InlineKeyboardButton("⭐ Оценить другую", callback_data="rate_book"),
                         InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
                        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                    ]
                    
                    stars = "⭐" * rating
                    rating_text = f"{stars} ({rating}/5)"
                    avg_rating = f"{stats['avg_rating']:.1f}" if stats['avg_rating'] else "0.0"
                    
                    await query.edit_message_text(
                        f"""✅ Оценка поставлена!

{book['title']}
{rating_text}

📊 Общий рейтинг книги: {avg_rating}/5
({stats['rating_count']} оценок)""",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await query.edit_message_text("❌ Ошибка.", reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="rate_book")]
                    ]))
        except:
            await query.edit_message_text("❌ Ошибка.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="rate_book")]
            ]))
    
    # Обновить прогресс
    elif data.startswith("progress_"):
        book_id = int(data.replace("progress_", ""))
        await query.edit_message_text(
            f"📊 Чтобы обновить прогресс:\n/progress {book_id} <страница>\n\nПример: /progress {book_id} 150",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="mybooks")]
            ])
        )
    
    # Закончить чтение
    elif data.startswith("finish_"):
        try:
            book_id = int(data.replace("finish_", ""))
            
            if not db.has_book(user_db_id, book_id):
                await query.edit_message_text("❌ У тебя нет этой книги.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="mybooks")]
                ]))
                return
            
            if db.update_book_status(user_db_id, book_id, "completed"):
                book = db.get_book(book_id)
                
                keyboard = [
                    [InlineKeyboardButton("⭐ Оценить книгу", callback_data=f"ratebook_{book_id}"),
                     InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                ]
                
                await query.edit_message_text(
                    f"""🎉 Поздравляю с прочтением!

{book['title']}
👤 {book['author']}""",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text("❌ Ошибка.", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="mybooks")]
                ]))
        except:
            await query.edit_message_text("❌ Ошибка.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="mybooks")]
            ]))
    
    # Топ книги
    elif data.startswith("top_"):
        criteria = data.replace("top_", "")
        await show_top_books(query, criteria)
    
    # Ничего
    elif data == "no_action":
        pass


# ========== ПОМОЩНИКИ ==========

async def show_search_menu(upd):
    genres = db.get_all_genres()
    
    keyboard_buttons = []
    for i in range(0, min(len(genres), 6), 2):
        row = []
        row.append(InlineKeyboardButton(f"📂 {genres[i]}", callback_data=f"search_{genres[i]}"))
        if i + 1 < len(genres):
            row.append(InlineKeyboardButton(f"📂 {genres[i+1]}", callback_data=f"search_{genres[i+1]}"))
        keyboard_buttons.append(row)
    
    keyboard_buttons.append([InlineKeyboardButton("🔍 Поиск по названию", callback_data="search_input")])
    keyboard_buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    
    text = "🔍 Выбери жанр или поиск:"
    
    if hasattr(upd, 'edit_message_text'):
        await upd.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    else:
        await upd.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard_buttons))


async def do_search(upd, query, genre):
    books = db.search_books(query, genre, 10)
    
    if not books:
        if query:
            msg = f"📭 По запросу '{query}' ничего нет."
        else:
            msg = f"📭 В жанре '{genre}' ничего нет."
        
        keyboard = [
            [InlineKeyboardButton("🔍 Новый поиск", callback_data="search"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        if hasattr(upd, 'edit_message_text'):
            await upd.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await upd.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    if query:
        title = f"🔍 Найдено по '{query}':"
    else:
        title = f"🔍 Книги в жанре '{genre}':"
    
    message = f"{title}\n"
    
    keyboard_buttons = []
    for i, book in enumerate(books, 1):
        stats = db.get_book_stats(book['id'])
        rating = f" ⭐{stats['avg_rating']:.1f}" if stats['avg_rating'] > 0 else ""
        
        message += f"\n{i}. {book['title']}"
        message += f"\n   👤 {book['author']}{rating}"
        message += f"\n   📊 Добавили: {stats['total_added']} чел. | Читают сейчас: {stats['currently_reading']} чел. (ID: {book['id']})"
        
        short = book['title'][:12] + "..." if len(book['title']) > 12 else book['title']
        keyboard_buttons.append([
            InlineKeyboardButton(f"➕ Добавить '{short}'", callback_data=f"add_{book['id']}")
        ])
    
    keyboard_buttons.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="search")])
    keyboard_buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    
    if hasattr(upd, 'edit_message_text'):
        await upd.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    else:
        await upd.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard_buttons))


async def show_top_books(upd, criteria, filter_by=""):
    genres = db.get_all_genres()
    genre = filter_by if filter_by in genres else ""
    author = filter_by if not genre and filter_by else ""
    
    books = db.get_top_books(criteria, genre, author, 5)
    
    if not books:
        msg = "📭 Нет книг по этому критерию."
        if genre:
            msg = f"📭 В жанре '{genre}' ничего нет."
        
        keyboard = [
            [InlineKeyboardButton("🏆 Другой критерий", callback_data="top_books"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        if hasattr(upd, 'edit_message_text'):
            await upd.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await upd.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    if criteria == 'rating':
        title = "🏆 Книги с лучшим рейтингом"
    else:
        title = "🏆 Самые популярные книги"
    
    if genre:
        title += f" ({genre})"
    
    message = f"{title}:\n"
    
    keyboard_buttons = []
    for i, book in enumerate(books, 1):
        stats = db.get_book_stats(book['id'])
        
        if criteria == 'rating':
            rating = stats['avg_rating']
            count = stats['rating_count']
            line = f"{i}. {book['title']} - ⭐ {rating:.1f}/5 ({count} оценок)"
        else:
            added = stats['total_added']
            line = f"{i}. {book['title']} - 👥 {added} читателей"
        
        message += f"\n{line}"
        message += f"\n   👤 {book['author']} (ID: {book['id']})"
        
        short = book['title'][:12] + "..." if len(book['title']) > 12 else book['title']
        keyboard_buttons.append([
            InlineKeyboardButton(f"➕ Добавить '{short}'", callback_data=f"add_{book['id']}")
        ])
    
    keyboard_buttons.append([InlineKeyboardButton("⭐ По рейтингу", callback_data="top_rating"),
                           InlineKeyboardButton("👥 По популярности", callback_data="top_popularity")])
    keyboard_buttons.append([InlineKeyboardButton("🔍 Поиск книг", callback_data="search"),
                           InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    
    if hasattr(upd, 'edit_message_text'):
        await upd.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard_buttons))
    else:
        await upd.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard_buttons))


async def error_handler(update: Update, context):
    try:
        keyboard = [
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await update.message.reply_text("Произошла ошибка. Попробуй еще раз.", reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        pass


# ========== ЗАПУСК ==========

def main():
    print("=" * 40)
    print(" BookBot запускается...")
    print("=" * 40)
    
    app = Application.builder().token(TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("progress", progress_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("addbook", addbook_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("top", top_command))
    
    # Кнопки
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Текст (заменяем старый обработчик на новый)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Ошибки
    app.add_error_handler(error_handler)
    
    print(" Бот запущен!")
    print(" Ожидание сообщений...")
    print(" Для остановки: Ctrl+C")
    print("-" * 40)
    
    app.run_polling()


if __name__ == '__main__':
    main()
