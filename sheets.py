"""Google Sheets integration for expense tracking."""

import os
import re
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


class SheetsClient:
    """Google Sheets client for the 久留米 expense tracker."""

    def __init__(
        self,
        credentials_file: Optional[str] = None,
        spreadsheet_id: Optional[str] = None,
    ):
        credentials_file = credentials_file or os.getenv("GOOGLE_CREDENTIALS_FILE")
        spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SPREADSHEET_ID")

        if not credentials_file:
            raise ValueError("GOOGLE_CREDENTIALS_FILE not set")
        if not spreadsheet_id:
            raise ValueError("GOOGLE_SPREADSHEET_ID not set")

        creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        self.gc = gspread.authorize(creds)
        self.spreadsheet_id = spreadsheet_id
        self._sheet = None

    @property
    def sheet(self) -> gspread.Worksheet:
        """Get the first worksheet (lazy load)."""
        if self._sheet is None:
            self._sheet = self.gc.open_by_key(self.spreadsheet_id).sheet1
        return self._sheet

    def append_expense(
        self,
        description: str,
        jpy: Optional[float] = None,
        twd: Optional[float] = None,
        date: Optional[str] = None,
    ) -> int:
        """Append an expense row to the sheet.

        Columns: B=日期, C=日幣, D=台幣, E=內容
        Row 1 = header, Row 2 = sum, data starts at row 3.

        Returns the row number that was written.
        """
        if date is None:
            date = datetime.now().strftime("%-m/%-d")

        # Normalize date to M/D format (match the sheet style)
        date = self._normalize_date(date)

        row = [
            "",  # A: empty
            date,  # B: 日期
            jpy if jpy else "",  # C: 日幣
            twd if twd else "",  # D: 台幣
            description,  # E: 內容
        ]

        self.sheet.append_row(row, value_input_option="USER_ENTERED")

        # Return the row number (last row)
        return self.sheet.row_count

    def get_all_expenses(self) -> list[dict]:
        """Get all expense rows (starting from row 3)."""
        rows = self.sheet.get_all_values()
        expenses = []
        for i, row in enumerate(rows[2:], start=3):  # skip header + sum row
            if not any(row[1:5]):  # skip empty rows
                continue
            expenses.append(
                {
                    "row": i,
                    "date": row[1] if len(row) > 1 else "",
                    "jpy": row[2] if len(row) > 2 else "",
                    "twd": row[3] if len(row) > 3 else "",
                    "description": row[4] if len(row) > 4 else "",
                }
            )
        return expenses

    def _normalize_date(self, date_str: str) -> str:
        """Convert various date formats to M/D."""
        # Already M/D format
        if re.match(r"^\d{1,2}/\d{1,2}$", date_str):
            return date_str

        # YYYY-MM-DD format
        m = re.match(r"^\d{4}-(\d{1,2})-(\d{1,2})$", date_str)
        if m:
            return f"{int(m.group(1))}/{int(m.group(2))}"

        # MM-DD format
        m = re.match(r"^(\d{1,2})-(\d{1,2})$", date_str)
        if m:
            return f"{int(m.group(1))}/{int(m.group(2))}"

        return date_str


def parse_expense_message(text: str) -> Optional[dict]:
    """Parse a quick expense message.

    Supported formats:
        午餐 1500 日幣
        威訊eSIM 728 台幣
        TOYOTA租車 27,500 日幣
        午餐 1500      (defaults to 日幣)
        6/28 午餐 1500 日幣   (with date prefix)

    Returns dict with keys: description, jpy, twd, date (or None if not parseable)
    """
    text = text.strip()
    if not text:
        return None

    # Optional date prefix: "6/28 " or "6-28 " or "2026-06-28 "
    date = None
    date_match = re.match(
        r"^(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2})\s+", text
    )
    if date_match:
        date = date_match.group(1)
        text = text[date_match.end():]

    # Core pattern: description + amount + optional currency
    # "午餐 1500 日幣" or "午餐 1500"
    pattern = r"^(.+?)\s+(\d[\d,]*(?:\.\d+)?)\s*(日幣|台幣|jpy|twd|yen|ntd|日圓|台幣|円)?$"
    m = re.match(pattern, text, re.IGNORECASE)
    if not m:
        return None

    description = m.group(1).strip()
    amount = float(m.group(2).replace(",", ""))
    currency = (m.group(3) or "日幣").lower()

    # Map currency aliases
    is_jpy = currency in ("日幣", "jpy", "yen", "日圓", "円")

    result = {
        "description": description,
        "jpy": amount if is_jpy else None,
        "twd": amount if not is_jpy else None,
        "date": date,
    }
    return result
