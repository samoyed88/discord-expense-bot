import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Tuple
from dataclasses import dataclass

DATABASE_NAME = "expenses.db"


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
