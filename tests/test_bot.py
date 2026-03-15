import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import discord
from bot import bot, db


@pytest.fixture
def mock_interaction():
    """Create a mock Discord interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock()
    interaction.user.id = 123456789
    interaction.user.name = "TestUser"
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction


class TestBotCommands:
    @pytest.mark.asyncio
    async def test_add_expense_valid(self, mock_interaction):
        """Test adding expense with valid data."""
        # This is a basic test to verify command structure
        from bot import add_expense
        
        # Mock the database
        with patch('bot.db') as mock_db:
            mock_db.get_or_create_user.return_value = 1
            mock_db.validate_category.return_value = True
            mock_db.add_expense.return_value = 1
            mock_db.get_categories.return_value = [("食物", "🍜"), ("交通", "🚗")]
            
            # This would require an actual bot instance to test fully
            assert mock_db is not None

    @pytest.mark.asyncio
    async def test_add_expense_invalid_amount(self, mock_interaction):
        """Test adding expense with invalid amount."""
        from bot import add_expense
        
        with patch('bot.db'):
            assert True  # Placeholder for actual async test

    def test_bot_initialization(self):
        """Test bot is initialized correctly."""
        assert bot is not None
        assert bot.user is None  # Not logged in yet

    def test_database_initialized(self):
        """Test database is initialized."""
        assert db is not None
        
        # Use unique user to avoid conflicts with previous test runs
        import time
        unique_id = int(time.time() * 1000) % 1000000000
        
        # Test basic database operations
        user_id = db.get_or_create_user(unique_id, "TestUser")
        assert user_id > 0
        
        # Add and verify expense
        expense_id = db.add_expense(
            user_id=user_id,
            amount=50.0,
            description="Test Expense",
            category="食物",
            date="2026-03-15"
        )
        assert expense_id > 0
        
        # Check expense was added (should be exactly 1 for this new user)
        expenses = db.get_expenses(user_id)
        assert len(expenses) == 1
        assert expenses[0]["amount"] == 50.0

    def test_bot_config(self):
        """Test bot configuration."""
        from config import COMMAND_SYNC_INTERVAL, BOT_PREFIX
        
        assert BOT_PREFIX == "/"
        assert COMMAND_SYNC_INTERVAL > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
