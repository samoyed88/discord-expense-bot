import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple
from dataclasses import dataclass

# Cross-platform database path
DATABASE_NAME = str(Path(__file__).parent / "expenses.db")


@dataclass
class Category:
    id: int
    name: str
    icon: str = "💰"


@dataclass
class Expense:
    id: int
    user_id: int
    amount: float
    description: str
    category: str
    date: str
    created_at: str


@dataclass
class User:
    id: int
    discord_id: int
    username: str
    created_at: str


class Database:
    def __init__(self, db_name=DATABASE_NAME):
        self.db_name = db_name
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id INTEGER UNIQUE NOT NULL,
                username TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Create categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                icon TEXT DEFAULT '💰'
            )
        """)

        # Create expenses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (category) REFERENCES categories(name)
            )
        """)

        # Insert default categories
        default_categories = [
            ("食物", "🍜"),
            ("交通", "🚗"),
            ("娛樂", "🎬"),
            ("購物", "🛍️"),
            ("工作", "💼"),
            ("健康", "🏥"),
            ("其他", "📝"),
        ]

        for name, icon in default_categories:
            try:
                cursor.execute(
                    "INSERT INTO categories (name, icon) VALUES (?, ?)", (name, icon)
                )
            except sqlite3.IntegrityError:
                pass

        conn.commit()
        conn.close()

    def get_or_create_user(self, discord_id: int, username: str) -> int:
        """Get or create user, return user_id."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE discord_id = ?", (discord_id,))
        result = cursor.fetchone()

        if result:
            user_id = result[0]
        else:
            cursor.execute(
                "INSERT INTO users (discord_id, username, created_at) VALUES (?, ?, ?)",
                (discord_id, username, datetime.now().isoformat()),
            )
            user_id = cursor.lastrowid
            conn.commit()

        conn.close()
        return user_id

    def _normalize_description(self, desc: str) -> str:
        """Normalize description for deduplication.
        
        Remove common prefixes/suffixes and truncate to core text.
        Examples:
        - "連加*停車大聲公" -> "停車大聲公"
        - "連支*CityWash" -> "CityWash"
        - "和雲行動服務 iRent..." -> "iRent"
        """
        # Remove common merchant prefixes
        prefixes = [
            "連加*", "連支*", "和雲行動服務", "foodpanda-",
            "富邦momo-EC", "MOMO-EC", "樂購蝦皮", "PCHOME",
            "全家便利商店", "統一超商", "全國電子", "藍新*"
        ]
        
        normalized = desc.strip()
        
        # Remove known prefixes
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
                break
        
        # Remove common suffixes (store names, addresses)
        # Keep only first meaningful part before hyphens/ellipsis
        if " " in normalized:
            # Take first part before space/dash
            parts = normalized.split(" ")[0].split("-")[0]
            if parts:
                normalized = parts
        elif "-" in normalized:
            normalized = normalized.split("-")[0].strip()
        
        # Remove trailing ellipsis or truncate long descriptions
        normalized = normalized.replace("...", "").strip()
        
        # Truncate to first 30 chars (core name)
        if len(normalized) > 30:
            normalized = normalized[:30].strip()
        
        return normalized.lower()

    def check_duplicate_expense(
        self, user_id: int, description: str, date: str, amount: float = None
    ) -> Optional[dict]:
        """Check if expense with same user_id, description, date, and amount exists.
        
        Uses normalized description for fuzzy matching to handle
        variations like "連加*停車大聲公" vs "停車大聲公"
        
        Only considers it a duplicate if:
        1. Same user AND same date AND exact description AND same amount (if amount provided), OR
        2. Same user AND same date AND fuzzy description match AND same amount
        
        This prevents different-amount transactions on same day/merchant
        from being incorrectly marked as duplicates.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Normalize the input description
        normalized_desc = self._normalize_description(description)

        # First try: exact match on original description
        cursor.execute(
            """
            SELECT id, amount, category, created_at
            FROM expenses
            WHERE user_id = ? AND description = ? AND date = ?
            LIMIT 1
            """,
            (user_id, description, date),
        )
        result = cursor.fetchone()
        
        # If found with exact match, check amount if provided
        if result and amount is not None:
            # If amount doesn't match, this is not a duplicate
            if abs(result[1] - amount) >= 0.01:
                result = None
        
        # Second try: fuzzy match on normalized descriptions with amount check
        if not result:
            cursor.execute(
                """
                SELECT id, amount, category, created_at, description
                FROM expenses
                WHERE user_id = ? AND date = ?
                """,
                (user_id, date),
            )
            all_expenses = cursor.fetchall()
            
            for row in all_expenses:
                stored_desc = self._normalize_description(row[4])
                # Fuzzy match: same normalized description AND same amount
                if (stored_desc == normalized_desc and 
                    stored_desc and  # Ensure not empty
                    amount is not None and 
                    abs(row[1] - amount) < 0.01):  # Same amount (float comparison)
                    result = row
                    break
        
        conn.close()
        
        if result:
            return {
                "id": result[0],
                "amount": result[1],
                "category": result[2],
                "created_at": result[3],
            }
        return None

    def add_expense(
        self, user_id: int, amount: float, description: str, category: str, date: str
    ) -> int:
        """Add expense record, return expense_id."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO expenses (user_id, amount, description, category, date, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, amount, description, category, date, datetime.now().isoformat()),
        )
        expense_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return expense_id

    def get_expenses(
        self, user_id: int, limit: int = 10
    ) -> List[dict]:
        """Get recent expenses for user."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, amount, description, category, date, created_at
            FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC, created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        results = cursor.fetchall()
        conn.close()
        return [dict(row) for row in results]

    def delete_expense(self, expense_id: int, user_id: int) -> bool:
        """Delete expense (only by owner)."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id)
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def get_monthly_stats(self, user_id: int, year: int, month: int) -> dict:
        """Get monthly statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Total by category
        cursor.execute(
            """
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM expenses
            WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
            GROUP BY category
            """,
            (user_id, str(year), f"{month:02d}"),
        )
        categories = {row[0]: {"total": row[1], "count": row[2]} for row in cursor.fetchall()}

        # Total amount
        cursor.execute(
            """
            SELECT SUM(amount) as total
            FROM expenses
            WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
            """,
            (user_id, str(year), f"{month:02d}"),
        )
        total = cursor.fetchone()[0] or 0

        conn.close()
        return {"total": total, "by_category": categories}

    def get_categories(self) -> List[Tuple[str, str]]:
        """Get all categories."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name, icon FROM categories ORDER BY name")
        results = cursor.fetchall()
        conn.close()
        return results

    def validate_category(self, category: str) -> bool:
        """Check if category exists."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM categories WHERE name = ?", (category,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
