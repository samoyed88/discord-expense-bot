# Discord Expense Bot

A Discord bot for expense tracking with AI-powered image recognition using Google Gemini.

## Features
- Text-based expense logging
- Image-based expense recognition (receipts, invoices)
- Multi-user support
- Expense categorization
- Monthly statistics and analysis

## Setup

### Prerequisites
- Python 3.9+
- Discord Bot Token
- Google Gemini API Key

### Installation

1. Clone the repository
2. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create `.env` file:
   ```
   DISCORD_TOKEN=your_bot_token
   GEMINI_API_KEY=your_gemini_key
   ```

5. Run the bot:
   ```bash
   python bot.py
   ```

## Project Structure
```
discord-expense-bot/
├── bot.py                 # Main bot entry point
├── database.py            # SQLite database models
├── gemini_client.py       # Gemini API integration
├── config.py              # Configuration
├── tests/                 # Test files
│   ├── test_database.py
│   ├── test_gemini.py
│   └── test_bot.py
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables (git ignored)
```

## Commands
- `/add` - Log expense by text
- `/add_image` - Log expense from image
- `/list` - View expense records
- `/stats` - Show statistics
- `/delete` - Delete expense record
