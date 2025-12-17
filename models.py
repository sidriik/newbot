"""
models.py - управление пользовательскими данными в оперативной памяти
"""

class UserManager:
    """
    Управление книгами пользователей в оперативной памяти.
    Быстро, но данные теряются при перезапуске бота.
    """
    
    def __init__(self):
        self.users = {}  # {user_id: {book_id: {'status': str, 'rating': int}}}
    
    def add_book(self, user_id, book_id, status='planned'):
        """Добавляет книгу пользователю."""
        try:
            allowed_status = ["planned", "reading", "completed", "dropped"]
            if status not in allowed_status:
                return False
            
            if user_id not in self.users:
                self.users[user_id] = {}
            
            self.users[user_id][book_id] = {
                'status': status,
                'rating': None
            }
            return True
        except Exception as e:
            print(f"[MODELS ERROR] add_book: {e}")
            return False
    
    def update_status(self, user_id, book_id, new_status):
        """Обновляет статус книги."""
        try:
            if user_id in self.users and book_id in self.users[user_id]:
                self.users[user_id][book_id]['status'] = new_status
                return True
            return False
        except Exception as e:
            print(f"[MODELS ERROR] update_status: {e}")
            return False
    
    def rate_book(self, user_id, book_id, rating):
        """Ставит оценку книге."""
        try:
            if rating < 1 or rating > 5:
                return False
            if user_id in self.users and book_id in self.users[user_id]:
                self.users[user_id][book_id]['rating'] = rating
                return True
            return False
        except Exception as e:
            print(f"[MODELS ERROR] rate_book: {e}")
            return False
    
    def get_user_books(self, user_id, status=None):
        """Получает книги пользователя."""
        try:
            if user_id not in self.users:
                return []
            
            books = []
            for book_id, data in self.users[user_id].items():
                if status is None or data['status'] == status:
                    books.append({
                        'book_id': book_id,
                        'status': data['status'],
                        'rating': data['rating']
                    })
            return books
        except Exception as e:
            print(f"[MODELS ERROR] get_user_books: {e}")
            return []
    
    def remove_book(self, user_id, book_id):
        """Удаляет книгу."""
        try:
            if user_id in self.users and book_id in self.users[user_id]:
                del self.users[user_id][book_id]
                if not self.users[user_id]:
                    del self.users[user_id]
                return True
            return False
        except Exception as e:
            print(f"[MODELS ERROR] remove_book: {e}")
            return False
    
    def has_book(self, user_id, book_id):
        """Проверяет, есть ли книга."""
        try:
            return user_id in self.users and book_id in self.users[user_id]
        except:
            return False
    
    def get_stats(self, user_id):
        """Статистика пользователя."""
        try:
            stats = {'total': 0, 'planned': 0, 'reading': 0, 
                     'completed': 0, 'dropped': 0, 'avg_rating': 0.0}
            
            if user_id not in self.users:
                return stats
            
            books = self.users[user_id]
            stats['total'] = len(books)
            
            total_rating = 0
            rated_count = 0
            
            for data in books.values():
                status = data['status']
                if status in stats:
                    stats[status] += 1
                
                if data['rating'] is not None:
                    total_rating += data['rating']
                    rated_count += 1
            
            if rated_count > 0:
                stats['avg_rating'] = round(total_rating / rated_count, 2)
            
            return stats
        except Exception as e:
            print(f"[MODELS ERROR] get_stats: {e}")
            return {'total': 0, 'planned': 0, 'reading': 0, 
                    'completed': 0, 'dropped': 0, 'avg_rating': 0.0}
    
    def clear_user(self, user_id):
        """Очищает все книги пользователя."""
        try:
            if user_id in self.users:
                del self.users[user_id]
                return True
            return False
        except:
            return False
