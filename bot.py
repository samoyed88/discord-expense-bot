import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from datetime import datetime

from sheets import SheetsClient

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


# ==================== Modal: 填寫記帳資料 ====================

class ExpenseModal(discord.ui.Modal, title="記帳"):
    description = discord.ui.TextInput(
        label="內容",
        placeholder="例如：午餐、TOYOTA租車",
        required=True,
    )
    amount = discord.ui.TextInput(
        label="金額",
        placeholder="例如：1500",
        required=True,
    )
    date = discord.ui.TextInput(
        label="日期（選填，預設今天）",
        placeholder="例如：7/1",
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Validate amount
        try:
            amount = float(self.amount.value.replace(",", ""))
            if amount <= 0:
                await interaction.response.send_message("❌ 金額必須大於 0", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ 金額格式錯誤", ephemeral=True)
            return

        date_str = self.date.value.strip() if self.date.value else None

        # Show currency + card selection
        view = CurrencyCardView(
            description=self.description.value.strip(),
            amount=amount,
            date=date_str,
        )
        await interaction.response.send_message(
            f"**{self.description.value.strip()}** {amount:,.0f}\n請選擇幣別和卡號：",
            view=view,
            ephemeral=True,
        )


# ==================== View: 選幣別 + 卡號 ====================

class CurrencyCardView(discord.ui.View):
    def __init__(self, description: str, amount: float, date: str | None):
        super().__init__(timeout=60)
        self.description = description
        self.amount = amount
        self.date = date
        self.currency = None
        self.card = None

    @discord.ui.select(
        placeholder="選擇幣別",
        options=[
            discord.SelectOption(label="日幣", value="jpy", emoji="🇯🇵"),
            discord.SelectOption(label="台幣", value="twd", emoji="🇹🇼"),
        ],
        row=0,
    )
    async def currency_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.currency = select.values[0]
        select.disabled = True
        select.placeholder = "日幣" if self.currency == "jpy" else "台幣"
        await interaction.response.edit_message(view=self)
        await self._try_submit(interaction)

    @discord.ui.select(
        placeholder="選擇卡號",
        options=[
            discord.SelectOption(label="9491", value="9491"),
            discord.SelectOption(label="7133", value="7133"),
            discord.SelectOption(label="自訂（輸入後送出）", value="custom"),
        ],
        row=1,
    )
    async def card_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if select.values[0] == "custom":
            modal = CustomCardModal(parent_view=self)
            await interaction.response.send_modal(modal)
        else:
            self.card = select.values[0]
            select.disabled = True
            select.placeholder = self.card
            await interaction.response.edit_message(view=self)
            await self._try_submit(interaction)

    async def _try_submit(self, interaction: discord.Interaction):
        """When both currency and card are selected, write to Google Sheets."""
        if self.currency is None or self.card is None:
            return

        if not sheets:
            await interaction.followup.send("❌ Google Sheets 未設定", ephemeral=True)
            return

        try:
            jpy = self.amount if self.currency == "jpy" else None
            twd = self.amount if self.currency == "twd" else None

            sheets.append_expense(
                description=self.description,
                jpy=jpy,
                twd=twd,
                date=self.date,
                card=self.card,
            )

            currency_label = "日幣" if self.currency == "jpy" else "台幣"
            currency_symbol = "¥" if self.currency == "jpy" else "$"
            date_display = self.date or datetime.now().strftime("%-m/%-d")

            await interaction.followup.send(
                f"✅ **{self.description}** {currency_symbol}{self.amount:,.0f} {currency_label}（{date_display}）卡號 {self.card}",
            )
            self.stop()
        except Exception as e:
            await interaction.followup.send(f"❌ 寫入失敗：{str(e)}", ephemeral=True)


# ==================== Modal: 自訂卡號 ====================

class CustomCardModal(discord.ui.Modal, title="自訂卡號"):
    card_input = discord.ui.TextInput(
        label="卡號",
        placeholder="輸入卡號末四碼",
        required=True,
        max_length=20,
    )

    def __init__(self, parent_view: CurrencyCardView):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.card = self.card_input.value.strip()
        # Disable card select
        for child in self.parent_view.children:
            if isinstance(child, discord.ui.Select) and child.row == 1:
                child.disabled = True
                child.placeholder = self.parent_view.card
        await interaction.response.edit_message(view=self.parent_view)
        await self.parent_view._try_submit(interaction)


# ==================== Event: $ 觸發 ====================

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if EXPENSE_CHANNEL_ID and str(message.channel.id) != EXPENSE_CHANNEL_ID:
        return

    if message.content.strip() != "$":
        return

    # Send button to trigger the modal
    view = StartView()
    await message.reply("點擊下方按鈕開始記帳：", view=view)


class StartView(discord.ui.View):
    @discord.ui.button(label="開始記帳", style=discord.ButtonStyle.primary, emoji="💰")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ExpenseModal())


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
