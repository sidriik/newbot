import pytest
import sqlite3
from database import Database


def test_database_creation():
    """Тест создания базы данных"""
    db = Database(":memory:")
    conn = db.get_connection()
    cur = conn.cursor()

    # Создаем таблицу книг
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL
        )
    """
    )

    # Добавляем книгу
    cur.execute(
        """
        INSERT INTO books (title, author)
        VALUES (?, ?)
    """,
        ("Тестовая книга", "Тестовый автор"),
    )

    conn.commit()

    # Проверяем
    cur.execute("SELECT COUNT(*) FROM books")
    count = cur.fetchone()[0]
    assert count == 1

    cur.execute("SELECT title FROM books WHERE id = 1")
    title = cur.fetchone()[0]
    assert title == "Тестовая книга"

    conn.close()


def test_add_duplicate_book_error():
    """Тест на ошибку дублирования"""
    db = sqlite3.connect(":memory:")
    cur = db.cursor()

    # Таблица с уникальным ограничением
    cur.execute(
        """
        CREATE TABLE user_books (
            user_id INTEGER,
            book_id INTEGER,
            UNIQUE(user_id, book_id)
        )
    """
    )

    # Добавляем первую запись
    cur.execute("INSERT INTO user_books (user_id, book_id) VALUES (1, 1)")

    # Пробуем добавить вторую такую же - должна быть ошибка
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO user_books (user_id, book_id) VALUES (1, 1)")

    db.close()


def test_search_books_simple():
    """Простой тест поиска"""
    db = Database(":memory:")
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE books (
            id INTEGER PRIMARY KEY,
            title TEXT,
            author TEXT
        )
    """
    )

    # Добавляем книги
    cur.execute(
        "INSERT INTO books (title, author) VALUES (?, ?)",
        ("Мастер и Маргарита", "Булгаков"),
    )
    cur.execute(
        "INSERT INTO books (title, author) VALUES (?, ?)", ("Война и мир", "Толстой")
    )

    conn.commit()

    # Ищем книгу
    search_query = "Маргарит"
    cur.execute(
        """
        SELECT * FROM books WHERE title LIKE ?
    """,
        (f"%{search_query}%",),
    )

    results = cur.fetchall()
    assert len(results) == 1
    assert results[0][1] == "Мастер и Маргарита"

    conn.close()


def test_error_handling():
    """Тест обработки ошибок"""
    db = Database(":memory:")
    conn = db.get_connection()
    cur = conn.cursor()

    # Создаем тестовую таблицу
    cur.execute(
        """
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            value TEXT NOT NULL
        )
    """
    )

    # Ошибка: таблицы не существует
    with pytest.raises(sqlite3.OperationalError):
        cur.execute("SELECT * FROM несуществующая_таблица")

    # Ошибка: неправильный тип данных
    with pytest.raises(sqlite3.Error):
        cur.execute("INSERT INTO test_table (id) VALUES (?)", ("не число",))

    # Добавляем запись
    cur.execute("INSERT INTO test_table (id, value) VALUES (?, ?)", (1, "первое"))
    conn.commit()

    # Ошибка: дублирование ID
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO test_table (id, value) VALUES (?, ?)", (1, "второе"))
        conn.commit()

    conn.close()


def test_database_connection():
    """Тест соединения с базой"""
    db = Database(":memory:")
    conn = db.get_connection()

    # Проверяем, что соединение работает
    assert conn is not None
    assert isinstance(conn, sqlite3.Connection)

    # Закрываем соединение
    conn.close()

    # После закрытия должно быть исключение
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_insert_and_retrieve():
    """Тест вставки и получения данных"""
    db = Database(":memory:")
    conn = db.get_connection()
    cur = conn.cursor()

    # Создаем таблицу
    cur.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER
        )
    """
    )

    # Вставляем данные
    cur.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("Анна", 25))
    cur.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("Иван", 30))

    conn.commit()

    # Получаем данные
    cur.execute("SELECT name FROM users WHERE age > ?", (26,))
    result = cur.fetchone()
    assert result[0] == "Иван"

    conn.close()


def test_delete_data():
    """Тест удаления данных"""
    db = Database(":memory:")
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    """
    )

    cur.execute("INSERT INTO items (name) VALUES (?)", ("тест1",))
    cur.execute("INSERT INTO items (name) VALUES (?)", ("тест2",))

    conn.commit()

    # Удаляем один элемент
    cur.execute("DELETE FROM items WHERE name = ?", ("тест1",))
    conn.commit()

    # Проверяем, что остался один элемент
    cur.execute("SELECT COUNT(*) FROM items")
    count = cur.fetchone()[0]
    assert count == 1

    conn.close()
