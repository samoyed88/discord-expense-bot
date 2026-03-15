# Discord Expense Bot Configuration

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Discord Bot Token
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Database
DATABASE_NAME = os.getenv("DATABASE_NAME", "expenses.db")

# Bot configuration
BOT_PREFIX = "/"
COMMAND_SYNC_INTERVAL = 3600  # Sync commands every hour
