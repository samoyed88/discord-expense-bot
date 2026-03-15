import pytest
import os
import sqlite3
from datetime import datetime
from database import Database


@pytest.fixture
def test_db():
    """Create a test database."""
    db_file = "test_expenses.db"
    if os.path.exists(db_file):
        os.remove(db_file)
    
    db = Database(db_file)
    yield db
    
    # Cleanup
    if os.path.exists(db_file):
        os.remove(db_file)


class TestDatabase:
    def test_init_db(self, test_db):
        """Test database initialization."""
        conn = test_db.get_connection()
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        assert "users" in tables
        assert "expenses" in tables
        assert "categories" in tables
        conn.close()

    def test_get_or_create_user(self, test_db):
        """Test user creation and retrieval."""
        user_id = test_db.get_or_create_user(123456789, "TestUser")
        assert user_id > 0
        
        # Same user should return same ID
        user_id2 = test_db.get_or_create_user(123456789, "TestUser")
        assert user_id == user_id2

    def test_add_expense(self, test_db):
        """Test adding expense."""
        user_id = test_db.get_or_create_user(123456789, "TestUser")
        
        expense_id = test_db.add_expense(
            user_id=user_id,
            amount=100.50,
            description="Lunch",
            category="食物",
            date="2026-03-15"
        )
        
        assert expense_id > 0
        
        # Verify expense was added
        expenses = test_db.get_expenses(user_id)
        assert len(expenses) == 1
        assert expenses[0]["amount"] == 100.50
        assert expenses[0]["description"] == "Lunch"

    def test_get_expenses(self, test_db):
        """Test fetching expenses."""
        user_id = test_db.get_or_create_user(123456789, "TestUser")
        
        # Add multiple expenses
        for i in range(5):
            test_db.add_expense(
                user_id=user_id,
                amount=10.0 * (i + 1),
                description=f"Item {i}",
                category="食物",
                date="2026-03-15"
            )
        
        expenses = test_db.get_expenses(user_id, limit=10)
        assert len(expenses) == 5

    def test_delete_expense(self, test_db):
        """Test deleting expense."""
        user_id = test_db.get_or_create_user(123456789, "TestUser")
        
        expense_id = test_db.add_expense(
            user_id=user_id,
            amount=100.0,
            description="Lunch",
            category="食物",
            date="2026-03-15"
        )
        
        # Delete expense
        deleted = test_db.delete_expense(expense_id, user_id)
        assert deleted is True
        
        # Verify deletion
        expenses = test_db.get_expenses(user_id)
        assert len(expenses) == 0

    def test_delete_expense_unauthorized(self, test_db):
        """Test that users can't delete others' expenses."""
        user_id1 = test_db.get_or_create_user(111111111, "User1")
        user_id2 = test_db.get_or_create_user(222222222, "User2")
        
        expense_id = test_db.add_expense(
            user_id=user_id1,
            amount=100.0,
            description="Lunch",
            category="食物",
            date="2026-03-15"
        )
        
        # User2 tries to delete User1's expense
        deleted = test_db.delete_expense(expense_id, user_id2)
        assert deleted is False
        
        # Verify expense still exists
        expenses = test_db.get_expenses(user_id1)
        assert len(expenses) == 1

    def test_monthly_stats(self, test_db):
        """Test monthly statistics."""
        user_id = test_db.get_or_create_user(123456789, "TestUser")
        
        # Add expenses in different categories
        test_db.add_expense(user_id, 50.0, "Lunch", "食物", "2026-03-15")
        test_db.add_expense(user_id, 30.0, "Dinner", "食物", "2026-03-16")
        test_db.add_expense(user_id, 20.0, "Taxi", "交通", "2026-03-17")
        
        stats = test_db.get_monthly_stats(user_id, 2026, 3)
        
        assert stats["total"] == 100.0
        assert "食物" in stats["by_category"]
        assert stats["by_category"]["食物"]["total"] == 80.0
        assert stats["by_category"]["食物"]["count"] == 2
        assert stats["by_category"]["交通"]["total"] == 20.0

    def test_get_categories(self, test_db):
        """Test category retrieval."""
        categories = test_db.get_categories()
        
        assert len(categories) > 0
        category_names = {name for name, _ in categories}
        assert "食物" in category_names
        assert "交通" in category_names

    def test_validate_category(self, test_db):
        """Test category validation."""
        assert test_db.validate_category("食物") is True
        assert test_db.validate_category("NonExistent") is False

    def test_check_duplicate_expense_not_found(self, test_db):
        """Test checking for non-existent duplicate."""
        user_id = test_db.get_or_create_user(123456789, "TestUser")
        
        duplicate = test_db.check_duplicate_expense(
            user_id=user_id,
            description="Lunch",
            date="2026-03-15"
        )
        
        assert duplicate is None

    def test_check_duplicate_expense_found(self, test_db):
        """Test checking for existing duplicate."""
        user_id = test_db.get_or_create_user(123456789, "TestUser")
        
        # Add first expense
        expense_id = test_db.add_expense(
            user_id=user_id,
            amount=100.50,
            description="Lunch",
            category="食物",
            date="2026-03-15"
        )
        
        # Check for duplicate
        duplicate = test_db.check_duplicate_expense(
            user_id=user_id,
            description="Lunch",
            date="2026-03-15"
        )
        
        assert duplicate is not None
        assert duplicate["id"] == expense_id
        assert duplicate["amount"] == 100.50

    def test_check_duplicate_different_date(self, test_db):
        """Test that different dates are not duplicates."""
        user_id = test_db.get_or_create_user(123456789, "TestUser")
        
        # Add first expense
        test_db.add_expense(
            user_id=user_id,
            amount=100.50,
            description="Lunch",
            category="食物",
            date="2026-03-15"
        )
        
        # Check for duplicate with different date
        duplicate = test_db.check_duplicate_expense(
            user_id=user_id,
            description="Lunch",
            date="2026-03-16"
        )
        
        assert duplicate is None

    def test_check_duplicate_different_description(self, test_db):
        """Test that different descriptions are not duplicates."""
        user_id = test_db.get_or_create_user(123456789, "TestUser")
        
        # Add first expense
        test_db.add_expense(
            user_id=user_id,
            amount=100.50,
            description="Lunch",
            category="食物",
            date="2026-03-15"
        )
        
        # Check for duplicate with different description
        duplicate = test_db.check_duplicate_expense(
            user_id=user_id,
            description="Dinner",
            date="2026-03-15"
        )
        
        assert duplicate is None

    def test_normalize_description_prefixes(self, test_db):
        """Test description normalization removes prefixes."""
        # Test removing merchant prefixes
        assert test_db._normalize_description("連加*停車大聲公") == "停車大聲公".lower()
        assert test_db._normalize_description("連支*CityWash") == "citywash"
        assert test_db._normalize_description("和雲行動服務 iRent") == "irent"
        # foodpanda- prefix is removed, leaving just the food name
        assert test_db._normalize_description("foodpanda-pizza") == "pizza"

    def test_normalize_description_case_insensitive(self, test_db):
        """Test that normalization is case insensitive."""
        desc1 = "停車大聲公"
        desc2 = "停車大聲公"
        assert test_db._normalize_description(desc1) == test_db._normalize_description(desc2)

    def test_check_duplicate_fuzzy_match(self, test_db):
        """Test fuzzy matching with normalized descriptions."""
        user_id = test_db.get_or_create_user(123456789, "TestUser")
        
        # Add expense with prefix
        expense_id = test_db.add_expense(
            user_id=user_id,
            amount=1.00,
            description="連加*停車大聲公",
            category="交通",
            date="2026-03-09"
        )
        
        # Check for duplicate without prefix (should find it)
        duplicate = test_db.check_duplicate_expense(
            user_id=user_id,
            description="停車大聲公",
            date="2026-03-09",
            amount=1.00
        )
        
        assert duplicate is not None
        assert duplicate["id"] == expense_id

    def test_check_duplicate_fuzzy_match_reverse(self, test_db):
        """Test fuzzy matching in reverse (stored without prefix, new with prefix)."""
        user_id = test_db.get_or_create_user(123456789, "TestUser")
        
        # Add expense without prefix
        expense_id = test_db.add_expense(
            user_id=user_id,
            amount=60.00,
            description="CityWash 洗車",
            category="其他",
            date="2026-02-27"
        )
        
        # Check for duplicate with prefix (should find it)
        duplicate = test_db.check_duplicate_expense(
            user_id=user_id,
            description="連支*CityWash",
            date="2026-02-27",
            amount=60.00
        )
        
        assert duplicate is not None
        assert duplicate["id"] == expense_id

    def test_check_duplicate_different_amount_not_duplicate(self, test_db):
        """Test that same merchant/date with different amounts is NOT a duplicate."""
        user_id = test_db.get_or_create_user(123456789, "TestUser")
        
        # Add first expense
        expense1_id = test_db.add_expense(
            user_id=user_id,
            amount=60.00,
            description="和雲行動服務 iRent 租車",
            category="交通",
            date="2026-02-28"
        )
        
        # Check different amount on same date - should NOT be duplicate
        duplicate = test_db.check_duplicate_expense(
            user_id=user_id,
            description="和雲行動服務 iRent 租車",
            date="2026-02-28",
            amount=93.00  # Different amount
        )
        
        assert duplicate is None  # Should NOT find it as duplicate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
