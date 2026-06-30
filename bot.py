import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from datetime import datetime

from sheets import SheetsClient, parse_expense_message

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
EXPENSE_CHANNEL_ID = os.getenv("EXPENSE_CHANNEL_ID")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Google Sheets client
try:
    sheets = SheetsClient()
    print("✅ Google Sheets connected")
except Exception as e:
    print(f"❌ Google Sheets failed: {e}")
    sheets = None


@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    # Only process in the designated channel (if configured)
    if EXPENSE_CHANNEL_ID and str(message.channel.id) != EXPENSE_CHANNEL_ID:
        return

    parsed = parse_expense_message(message.content)
    if not parsed:
        return

    if not sheets:
        await message.reply("❌ Google Sheets 未設定")
        return

    try:
        sheets.append_expense(
            description=parsed["description"],
            jpy=parsed["jpy"],
            twd=parsed["twd"],
            date=parsed["date"],
        )

        amount_str = (
            f"¥{parsed['jpy']:,.0f} 日幣"
            if parsed["jpy"]
            else f"${parsed['twd']:,.0f} 台幣"
        )
        date_str = parsed["date"] or datetime.now().strftime("%-m/%-d")
        await message.reply(
            f"✅ **{parsed['description']}** {amount_str}（{date_str}）"
        )
    except Exception as e:
        await message.reply(f"❌ 寫入失敗：{str(e)}")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
