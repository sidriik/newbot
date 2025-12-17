"""
models.py - управление данными пользователей в оперативной памяти
Быстрое хранение статусов чтения и оценок
"""

class UserManager:
    """Класс для управления книгами пользователей в памяти"""
    
    def __init__(self):
        # user_id: {book_id: {'status': str, 'rating': int, 'current_page': int}}
        self.users = {}
    
    def add_book(self, user_id, book_id, status='planned'):
        """Добавляет книгу пользователю"""
        try:
            if user_id not in self.users:
                self.users[user_id] = {}
            
            self.users[user_id][book_id] = {
                'status': status,
                'rating': None,
                'current_page': 0
            }
            return True
        except:
            return False
    
    def update_book_status(self, user_id, book_id, new_status):
        """Обновляет статус чтения книги"""
        if user_id in self.users and book_id in self.users[user_id]:
            allowed_status = ["planned", "reading", "completed", "dropped"]
            if new_status in allowed_status:
                self.users[user_id][book_id]['status'] = new_status
                return True
        return False
    
    def update_progress(self, user_id, book_id, current_page):
        """Обновляет текущую страницу"""
        if user_id in self.users and book_id in self.users[user_id]:
            self.users[user_id][book_id]['current_page'] = current_page
            return True
        return False
    
    def rate_book(self, user_id, book_id, rating):
        """Ставит оценку книге"""
        if user_id in self.users and book_id in self.users[user_id]:
            if 1 <= rating <= 5:
                self.users[user_id][book_id]['rating'] = rating
                return True
        return False
    
    def get_user_books(self, user_id, status=None):
        """Получает книги пользователя с фильтром по статусу"""
        if user_id not in self.users:
            return []
        
        books = []
        for book_id, data in self.users[user_id].items():
            if status is None or data['status'] == status:
                books.append({
                    'book_id': book_id,
                    'status': data['status'],
                    'rating': data['rating'],
                    'current_page': data['current_page']
                })
        return books
    
    def remove_book(self, user_id, book_id):
        """Удаляет книгу"""
        if user_id in self.users and book_id in self.users[user_id]:
            del self.users[user_id][book_id]
            return True
        return False
    
    def has_book(self, user_id, book_id):
        """Проверяет, есть ли книга у пользователя"""
        return user_id in self.users and book_id in self.users[user_id]
    
    def get_book_info(self, user_id, book_id):
        """Получает информацию о конкретной книге пользователя"""
        if self.has_book(user_id, book_id):
            return self.users[user_id][book_id]
        return None
    
    def get_stats(self, user_id):
        """Статистика пользователя"""
        if user_id not in self.users:
            return {
                'total': 0, 'planned': 0, 'reading': 0,
                'completed': 0, 'dropped': 0, 'avg_rating': 0.0,
                'total_pages': 0
            }
        
        books = self.users[user_id]
        stats = {
            'total': len(books), 'planned': 0, 'reading': 0,
            'completed': 0, 'dropped': 0, 'avg_rating': 0.0,
            'total_pages': 0
        }
        
        total_rating = 0
        rated_count = 0
        
        for data in books.values():
            status = data['status']
            if status in stats:
                stats[status] += 1
            
            if data['rating'] is not None:
                total_rating += data['rating']
                rated_count += 1
            
            if data['current_page']:
                stats['total_pages'] += data['current_page']
        
        if rated_count > 0:
            stats['avg_rating'] = round(total_rating / rated_count, 2)
        
        return stats
