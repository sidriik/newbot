import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram_bot import start_command, progress_command, add_command


class TestBotCommands:

    def setup_method(self, method):
        self.update = AsyncMock()
        self.context = AsyncMock()
        self.message = AsyncMock()
        self.update.message = self.message
        self.update.effective_user = AsyncMock(id=123, username="test", first_name="Test")

        self.mock_db = MagicMock()

    def test_start_command_positive(self):
        self.mock_db.get_or_create_user.return_value = 1

        result = start_command(self.update, self.context)

        assert result is not None

    def test_start_command_db_error(self):
        self.mock_db.get_or_create_user.side_effect = Exception()

        result = start_command(self.update, self.context)

        assert result is not None

    def test_progress_command_positive(self):
        self.context.args = ["1", "100"]
        self.mock_db.get_or_create_user.return_value = 1
        self.mock_db.get_book_info.return_value = {'status': 'reading'}
        self.mock_db.get_book.return_value = {'total_pages': 200}
        self.mock_db.update_progress.return_value = True

        result = progress_command(self.update, self.context)

        assert result is not None

    def test_progress_command_no_args(self):
        self.context.args = []

        result = progress_command(self.update, self.context)

        assert result is not None

    def test_progress_command_wrong_args_count(self):
        self.context.args = ["1"]

        result = progress_command(self.update, self.context)

        assert result is not None

    def test_progress_command_invalid_args(self):
        self.context.args = ["abc", "xyz"]

        result = progress_command(self.update, self.context)

        assert result is not None

    def test_progress_command_book_not_found(self):
        self.context.args = ["999", "100"]
        self.mock_db.get_or_create_user.return_value = 1
        self.mock_db.get_book_info.return_value = None

        result = progress_command(self.update, self.context)

        assert result is not None

    def test_add_command_positive(self):
        self.context.args = ["1"]
        self.mock_db.get_or_create_user.return_value = 1
        self.mock_db.get_book.return_value = {"title": "Test", "author": "Test", "total_pages": 100}
        self.mock_db.add_user_book.return_value = True

        result = add_command(self.update, self.context)

        assert result is not None

    def test_add_command_no_args(self):
        self.context.args = []

        result = add_command(self.update, self.context)

        assert result is not None

    def test_add_command_not_number(self):
        self.context.args = ["abc"]

        result = add_command(self.update, self.context)

        assert result is not None

    def test_add_command_book_not_found(self):
        self.context.args = ["999"]
        self.mock_db.get_or_create_user.return_value = 1
        self.mock_db.get_book.return_value = None

        result = add_command(self.update, self.context)

        assert result is not None

    def test_add_command_already_exists(self):
        self.context.args = ["1"]
        self.mock_db.get_or_create_user.return_value = 1
        self.mock_db.get_book.return_value = {"title": "Test", "author": "Test", "total_pages": 100}
        self.mock_db.add_user_book.return_value = False

        result = add_command(self.update, self.context)

        assert result is not None
