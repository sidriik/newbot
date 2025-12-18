import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from database import Database

TOKEN = "8371793740:AAGyHz10Ro6JabxomkyjDGsjWhNaf3SUeMI"

db = Database()
user_states = {}


async def start_command(update: Update, context):
    user = update.effective_user
    
    user_id = db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    text = f"""Привет, {user.first_name}!

Я помогу тебе вести список книг.

Что ты хочешь сделать?"""
    
    buttons = [
        [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
        [InlineKeyboardButton("🔍 Найти книгу", callback_data="search")],
        [InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book")],
        [InlineKeyboardButton("📖 Начать читать", callback_data="start_reading")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
    ]
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    await update.message.reply_text(text, reply_markup=keyboard)


async def help_command(update: Update, context):
    help_text = """📚 BookBot - помощник для учета книг

Команды:
/start - Главное меню
/help - Справка
/add <ID> - Добавить книгу
/search <запрос> - Найти книгу
/stats - Статистика
/progress <ID> <страница> - Обновить прогресс"""
    
    await update.message.reply_text(help_text)


async def add_command(update: Update, context):
    if not context.args:
        await update.message.reply_text("Используй: /add <ID_книги>\nПример: /add 1")
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
            await update.message.reply_text("Эта книга уже есть в твоем списке.")
            return
        
        message = f"""✅ Книга добавлена!

{book['title']}
Автор: {book['author']}
Страниц: {book['total_pages']}"""
        
        buttons = [
            [InlineKeyboardButton("📖 Начать читать", callback_data=f"start_{book_id}"),
             InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")]
        ]
        
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(buttons))
        
    except ValueError:
        await update.message.reply_text("ID должен быть числом.")


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
        
        user_books = db.get_user_books(user_db_id)
        found = False
        for ub in user_books:
            if ub['book_id'] == book_id:
                found = True
                break
        
        if not found:
            await update.message.reply_text("У тебя нет этой книги.")
            return
        
        book = db.get_book(book_id)
        if not book:
            await update.message.reply_text("Книга не найдена.")
            return
        
        if page > book['total_pages']:
            await update.message.reply_text(f"В книге всего {book['total_pages']} страниц!")
            return
        
        ok = db.update_book_status(user_db_id, book_id, 'reading', page)
        
        if not ok:
            await update.message.reply_text("Ошибка обновления.")
            return
        
        progress = (page / book['total_pages']) * 100
        
        if progress >= 100:
            db.update_book_status(user_db_id, book_id, 'completed', page)
            message = f"""🎉 Поздравляю! Прочитал книгу!

{book['title']}
Автор: {book['author']}

Страниц: {page}/{book['total_pages']} (100%)"""
            
            buttons = [
                [InlineKeyboardButton("⭐ Оценить книгу", callback_data=f"ratebook_{book_id}"),
                 InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")]
            ]
        else:
            message = f"""📖 Прогресс обновлен!

{book['title']}
Автор: {book['author']}

Страница: {page} из {book['total_pages']}
Прогресс: {progress:.1f}%"""
            
            buttons = [
                [InlineKeyboardButton("📊 Еще обновить", callback_data=f"progress_{book_id}"),
                 InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")]
            ]
        
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(buttons))
        
    except ValueError:
        await update.message.reply_text("ID и страница должны быть числами.")


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

Всего книг: {stats['total']}
Запланировано: {stats['planned']}
Читаю сейчас: {stats['reading']}
Прочитано: {stats['completed']}
Брошено: {stats['dropped']}"""
    
    if stats['avg_rating'] > 0:
        message += f"\nСредняя оценка: {stats['avg_rating']:.1f}"
    
    await update.message.reply_text(message)


async def handle_text_message(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if len(text) >= 2:
        books = db.search_books(text, limit=5)
        
        if not books:
            await update.message.reply_text(f"По запросу '{text}' ничего не найдено.")
            return
        
        message = f"Найдено по запросу '{text}':\n"
        
        buttons = []
        for i, book in enumerate(books, 1):
            stats = db.get_book_stats(book['id'])
            rating = f" ⭐{stats['avg_rating']:.1f}" if stats['avg_rating'] > 0 else ""
            
            message += f"\n{i}. {book['title']}"
            message += f"\n   Автор: {book['author']}{rating} (ID: {book['id']})"
            
            short = book['title'][:12] + "..." if len(book['title']) > 12 else book['title']
            buttons.append([
                InlineKeyboardButton(f"➕ Добавить '{short}'", callback_data=f"add_{book['id']}")
            ])
        
        buttons.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="search")])
        
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(buttons))


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
    
    if data == "main_menu":
        buttons = [
            [InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")],
            [InlineKeyboardButton("🔍 Найти книгу", callback_data="search")],
            [InlineKeyboardButton("➕ Добавить книгу", callback_data="add_book")],
            [InlineKeyboardButton("📖 Начать читать", callback_data="start_reading")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
        ]
        await query.edit_message_text("📚 Главное меню", reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "mybooks":
        books = db.get_user_books(user_db_id)
        
        if not books:
            await query.edit_message_text("У тебя пока нет книг.")
            return
        
        planned = []
        reading = []
        completed = []
        
        for book in books:
            if book['status'] == 'planned':
                planned.append(book)
            elif book['status'] == 'reading':
                reading.append(book)
            elif book['status'] == 'completed':
                completed.append(book)
        
        message = "📚 Твои книги:\n"
        
        if reading:
            message += f"\n📖 Читаю сейчас ({len(reading)}):"
            for i, book in enumerate(reading[:3], 1):
                short = book['title'][:15] + "..." if len(book['title']) > 15 else book['title']
                progress = (book['current_page'] / book['total_pages']) * 100
                message += f"\n{i}. {short} - {progress:.0f}%"
        
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
        
        await query.edit_message_text(message)
    
    elif data == "search":
        await show_search_menu(query)
    
    elif data == "add_book":
        popular = db.search_books(limit=5)
        
        if not popular:
            await query.edit_message_text("Нет популярных книг.")
            return
        
        buttons = []
        for book in popular:
            buttons.append([
                InlineKeyboardButton(f"📖 {book['title'][:15]}...", callback_data=f"add_{book['id']}")
            ])
        
        buttons.append([InlineKeyboardButton("🔍 Найти другую", callback_data="search")])
        
        await query.edit_message_text("Выбери книгу для добавления:", reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "start_reading":
        planned = []
        user_books = db.get_user_books(user_db_id)
        for book in user_books:
            if book['status'] == 'planned':
                planned.append(book)
        
        if not planned:
            await query.edit_message_text("Нет запланированных книг.")
            return
        
        buttons = []
        for book in planned[:5]:
            buttons.append([
                InlineKeyboardButton(f"📖 {book['title'][:15]}...", callback_data=f"start_{book['book_id']}")
            ])
        
        await query.edit_message_text("Выбери книгу для чтения:", reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "stats":
        stats = db.get_user_stats(user_db_id)
        
        message = f"""📊 Твоя статистика:

Всего книг: {stats['total']}
Запланировано: {stats['planned']}
Читаю сейчас: {stats['reading']}
Прочитано: {stats['completed']}
Брошено: {stats['dropped']}"""
        
        if stats['avg_rating'] > 0:
            message += f"\nСредняя оценка: {stats['avg_rating']:.1f}"
        
        await query.edit_message_text(message)
    
    elif data.startswith("add_"):
        try:
            book_id = int(data.replace("add_", ""))
            book = db.get_book(book_id)
            
            if not book:
                await query.edit_message_text("Книга не найдена.")
                return
            
            if db.add_user_book(user_db_id, book_id, "planned"):
                buttons = [
                    [InlineKeyboardButton("📖 Начать читать", callback_data=f"start_{book_id}"),
                     InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")]
                ]
                
                await query.edit_message_text(
                    f"""✅ Книга добавлена!

{book['title']}
Автор: {book['author']}""",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            else:
                await query.edit_message_text("Эта книга уже есть в твоем списке.")
        except:
            await query.edit_message_text("Ошибка.")
    
    elif data.startswith("start_"):
        try:
            book_id = int(data.replace("start_", ""))
            
            user_books = db.get_user_books(user_db_id)
            has_book = False
            for book in user_books:
                if book['book_id'] == book_id:
                    has_book = True
                    break
            
            if not has_book:
                await query.edit_message_text("У тебя нет этой книги.")
                return
            
            if db.update_book_status(user_db_id, book_id, "reading"):
                book = db.get_book(book_id)
                
                await query.edit_message_text(
                    f"""📖 Начинаем читать!

{book['title']}
Автор: {book['author']}

Чтобы обновить прогресс:
/progress {book_id} <страница>"""
                )
            else:
                await query.edit_message_text("Ошибка.")
        except:
            await query.edit_message_text("Ошибка.")
    
    elif data.startswith("ratebook_"):
        try:
            book_id = int(data.replace("ratebook_", ""))
            book = db.get_book(book_id)
            
            if not book:
                await query.edit_message_text("Книга не найдена.")
                return
            
            buttons = []
            row = []
            for r in range(1, 6):
                row.append(InlineKeyboardButton(f"{r}⭐", callback_data=f"rate_{book_id}_{r}"))
            buttons.append(row)
            
            await query.edit_message_text(
                f"Оцени книгу:\n\n{book['title']}\nАвтор: {book['author']}",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except:
            await query.edit_message_text("Ошибка.")
    
    elif data.startswith("rate_"):
        try:
            parts = data.replace("rate_", "").split("_")
            if len(parts) == 2:
                book_id = int(parts[0])
                rating = int(parts[1])
                
                if db.rate_book(user_db_id, book_id, rating):
                    book = db.get_book(book_id)
                    stats = db.get_book_stats(book_id)
                    
                    stars = "⭐" * rating
                    
                    await query.edit_message_text(
                        f"""✅ Оценка поставлена!

{book['title']}
{stars} ({rating}/5)

Общий рейтинг книги: {stats['avg_rating']:.1f}/5
({stats['rating_count']} оценок)"""
                    )
                else:
                    await query.edit_message_text("Ошибка.")
        except:
            await query.edit_message_text("Ошибка.")
    
    elif data.startswith("progress_"):
        book_id = int(data.replace("progress_", ""))
        await query.edit_message_text(
            f"Чтобы обновить прогресс:\n/progress {book_id} <страница>\n\nПример: /progress {book_id} 150"
        )
    
    elif data.startswith("finish_"):
        try:
            book_id = int(data.replace("finish_", ""))
            
            user_books = db.get_user_books(user_db_id)
            has_book = False
            for book in user_books:
                if book['book_id'] == book_id:
                    has_book = True
                    break
            
            if not has_book:
                await query.edit_message_text("У тебя нет этой книги.")
                return
            
            if db.update_book_status(user_db_id, book_id, "completed"):
                book = db.get_book(book_id)
                
                buttons = [
                    [InlineKeyboardButton("⭐ Оценить книгу", callback_data=f"ratebook_{book_id}"),
                     InlineKeyboardButton("📚 Мои книги", callback_data="mybooks")]
                ]
                
                await query.edit_message_text(
                    f"""🎉 Поздравляю с прочтением!

{book['title']}
Автор: {book['author']}""",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            else:
                await query.edit_message_text("Ошибка.")
        except:
            await query.edit_message_text("Ошибка.")


async def show_search_menu(upd):
    genres = db.get_all_genres()
    
    buttons = []
    for i in range(0, min(len(genres), 6), 2):
        row = []
        row.append(InlineKeyboardButton(f"📂 {genres[i]}", callback_data=f"search_{genres[i]}"))
        if i + 1 < len(genres):
            row.append(InlineKeyboardButton(f"📂 {genres[i+1]}", callback_data=f"search_{genres[i+1]}"))
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("🔍 Поиск по названию", callback_data="search_input")])
    
    if hasattr(upd, 'edit_message_text'):
        await upd.edit_message_text("Выбери жанр:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await upd.message.reply_text("Выбери жанр:", reply_markup=InlineKeyboardMarkup(buttons))


async def do_search(upd, query, genre):
    books = db.search_books(query, genre, 10)
    
    if not books:
        if hasattr(upd, 'edit_message_text'):
            await upd.edit_message_text("Ничего не найдено.")
        else:
            await upd.message.reply_text("Ничего не найдено.")
        return
    
    message = f"Найдено:\n"
    
    buttons = []
    for i, book in enumerate(books, 1):
        stats = db.get_book_stats(book['id'])
        rating = f" ⭐{stats['avg_rating']:.1f}" if stats['avg_rating'] > 0 else ""
        
        message += f"\n{i}. {book['title']}"
        message += f"\n   Автор: {book['author']}{rating} (ID: {book['id']})"
        
        short = book['title'][:12] + "..." if len(book['title']) > 12 else book['title']
        buttons.append([
            InlineKeyboardButton(f"➕ Добавить '{short}'", callback_data=f"add_{book['id']}")
        ])
    
    buttons.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="search")])
    
    if hasattr(upd, 'edit_message_text'):
        await upd.edit_message_text(message, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await upd.message.reply_text(message, reply_markup=InlineKeyboardMarkup(buttons))


def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("progress", progress_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    print("Бот запущен!")
    app.run_polling()


if __name__ == '__main__':
    main()
