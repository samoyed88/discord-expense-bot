import os
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import io

from database import Database
from gemini_client import GeminiClient

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"
if not DISCORD_TOKEN and not TEST_MODE:
    raise ValueError("DISCORD_TOKEN environment variable not set")

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Initialize database and Gemini client
db = Database()
try:
    gemini = GeminiClient()
except ValueError:
    print("Warning: GEMINI_API_KEY not set. Image-based expense logging will not work.")
    gemini = None


@bot.event
async def on_ready():
    """Bot startup event."""
    print(f"✅ Bot logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")


# ==================== Commands ====================

@bot.tree.command(name="add", description="記錄支出（文字輸入）")
@app_commands.describe(
    amount="金額（例如：100.5）",
    category="分類：食物、交通、娛樂、購物、工作、健康、其他",
    description="描述（選擇）",
    date="日期 YYYY-MM-DD（選擇，默認今天）"
)
async def add_expense(
    interaction: discord.Interaction,
    amount: float,
    category: str,
    description: str = "",
    date: str = None
):
    """Add expense by text input."""
    await interaction.response.defer()
    
    try:
        # Validate amount
        if amount <= 0:
            await interaction.followup.send("❌ 金額必須大於0")
            return
        
        # Get or create user
        user_id = db.get_or_create_user(
            interaction.user.id,
            interaction.user.name
        )
        
        # Validate category
        if not db.validate_category(category):
            categories = db.get_categories()
            cat_list = ", ".join([f"{icon} {name}" for name, icon in categories])
            await interaction.followup.send(
                f"❌ 無效分類。有效分類：\n{cat_list}"
            )
            return
        
        # Set default date if not provided
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        else:
            # Validate date format
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                await interaction.followup.send("❌ 日期格式錯誤，請使用 YYYY-MM-DD")
                return
        
        # Check for duplicate (same date, description, and amount)
        desc = description or "N/A"
        duplicate = db.check_duplicate_expense(user_id, desc, date, amount)
        if duplicate:
            embed = discord.Embed(
                title="⚠️ 記錄已存在",
                color=discord.Color.orange(),
                description="相同日期和內容的記錄已存在，不會重複新增"
            )
            embed.add_field(name="金額", value=f"${duplicate['amount']}", inline=True)
            embed.add_field(name="日期", value=date, inline=True)
            embed.add_field(name="描述", value=desc, inline=False)
            embed.set_footer(text=f"現有記錄 ID: {duplicate['id']}")
            await interaction.followup.send(embed=embed)
            return
        
        # Add expense
        expense_id = db.add_expense(
            user_id=user_id,
            amount=amount,
            description=desc,
            category=category,
            date=date
        )
        
        # Format response
        categories_dict = {name: icon for name, icon in db.get_categories()}
        icon = categories_dict.get(category, "💰")
        
        embed = discord.Embed(
            title="✅ 記錄成功",
            color=discord.Color.green()
        )
        embed.add_field(name="金額", value=f"${amount}", inline=True)
        embed.add_field(name="分類", value=f"{icon} {category}", inline=True)
        embed.add_field(name="日期", value=date, inline=True)
        embed.add_field(name="描述", value=description or "無", inline=False)
        embed.set_footer(text=f"記錄 ID: {expense_id}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ 出錯：{str(e)}")


@bot.tree.command(name="add_image", description="記錄支出（圖片識別）")
@app_commands.describe(
    image="上傳收據或發票圖片",
    prompt="額外提示詞（可選，幫助AI識別）"
)
async def add_image_expense(
    interaction: discord.Interaction,
    image: discord.Attachment,
    prompt: str = None
):
    """Add expense from receipt/invoice image."""
    await interaction.response.defer()
    
    if not gemini:
        await interaction.followup.send("❌ AI 服務未配置（缺少 GEMINI_API_KEY）")
        return
    
    try:
        # Validate image type
        valid_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        if image.content_type not in valid_types:
            await interaction.followup.send(f"❌ 不支持的圖片格式：{image.content_type}")
            return
        
        # Download image
        image_data = await image.read()
        temp_path = f"/tmp/{image.filename}"
        with open(temp_path, "wb") as f:
            f.write(image_data)
        
        try:
            # Send progress indicator
            await interaction.followup.send("🔄 正在識別圖片中的支出項目，請稍候...")
            
            # Extract info from image (using async to avoid blocking Discord)
            result = await gemini.extract_from_receipt_async(temp_path, custom_prompt=prompt)
            
            # Validate extraction
            is_valid, error = gemini.validate_result(result)
            if not is_valid:
                await interaction.followup.send(f"❌ 識別失敗：{error}")
                return
            
            # Get or create user
            user_id = db.get_or_create_user(
                interaction.user.id,
                interaction.user.name
            )
            
            # Handle both single dict and list of dicts
            results = result if isinstance(result, list) else [result]
            
            # Add expenses to database with deduplication
            expense_ids = []
            duplicates = []
            for item in results:
                # Check for duplicate
                duplicate = db.check_duplicate_expense(
                    user_id,
                    item["description"],
                    item["date"],
                    item["amount"]
                )
                if duplicate:
                    duplicates.append({
                        "item": item,
                        "existing_id": duplicate["id"],
                        "existing_amount": duplicate["amount"]
                    })
                else:
                    expense_id = db.add_expense(
                        user_id=user_id,
                        amount=item["amount"],
                        description=item["description"],
                        category=item["category"],
                        date=item["date"]
                    )
                    expense_ids.append(expense_id)
            
            # Format response
            categories_dict = {name: icon for name, icon in db.get_categories()}
            
            if len(results) == 1:
                # Single item - simple format
                result_item = results[0]
                icon = categories_dict.get(result_item["category"], "💰")
                
                if duplicates and len(duplicates) == 1:
                    # Duplicate case
                    embed = discord.Embed(
                        title="⚠️ 記錄已存在",
                        color=discord.Color.orange(),
                        description="相同日期和內容的記錄已存在，不會重複新增"
                    )
                    embed.add_field(name="金額", value=f"${result_item['amount']}", inline=True)
                    embed.add_field(name="分類", value=f"{icon} {result_item['category']}", inline=True)
                    embed.add_field(name="日期", value=result_item["date"], inline=True)
                    embed.add_field(name="描述", value=result_item["description"], inline=False)
                    embed.set_footer(text=f"現有記錄 ID: {duplicates[0]['existing_id']}")
                else:
                    # New record
                    embed = discord.Embed(
                        title="✅ AI識別成功",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="金額", value=f"${result_item['amount']}", inline=True)
                    embed.add_field(name="分類", value=f"{icon} {result_item['category']}", inline=True)
                    embed.add_field(name="日期", value=result_item["date"], inline=True)
                    embed.add_field(name="描述", value=result_item["description"], inline=False)
                    embed.set_footer(text=f"記錄 ID: {expense_ids[0]}")
                
                await interaction.followup.send(embed=embed)
            else:
                # Multiple items - use table format or split into multiple embeds
                total_amount = 0
                added_count = len(expense_ids)
                duplicated_count = len(duplicates)
                
                for item in results:
                    total_amount += item["amount"]
                
                # Create summary message if there are duplicates
                if duplicates:
                    summary_msg = f"✅ 新增 {added_count} 筆 | ⚠️ 重複 {duplicated_count} 筆"
                else:
                    summary_msg = f"✅ AI識別成功（{len(results)} 筆）"
                
                # Discord limit: max 25 fields per embed
                # If > 25 items, split into multiple embeds
                if len(results) > 25:
                    # Format as text table for large number of items
                    table_text = "```\n序號  | 狀態  | 金額    | 分類   | 日期       | 描述\n"
                    table_text += "-" * 70 + "\n"
                    
                    for i, result_item in enumerate(results, 1):
                        amount_str = f"${result_item['amount']:.2f}"
                        desc_short = result_item["description"][:10] + ("..." if len(result_item["description"]) > 10 else "")
                        
                        # Check if this item is duplicated
                        is_dup = any(dup["item"]["description"] == result_item["description"] and 
                                    dup["item"]["date"] == result_item["date"] for dup in duplicates)
                        status = "重複" if is_dup else "新增"
                        
                        table_text += f"{i:4} | {status:4} | {amount_str:7} | {result_item['category']:6} | {result_item['date']} | {desc_short}\n"
                    
                    table_text += "```"
                    
                    embed = discord.Embed(
                        title=summary_msg,
                        color=discord.Color.green() if not duplicates else discord.Color.orange(),
                        description=table_text
                    )
                    
                    footer_text = f"合計: ${total_amount:.2f}"
                    if expense_ids:
                        footer_text += f" | 新增 IDs: {', '.join(map(str, expense_ids))}"
                    embed.set_footer(text=footer_text)
                    
                    await interaction.followup.send(embed=embed)
                else:
                    # Multiple items (≤25) - detailed format with fields
                    color = discord.Color.orange() if duplicates else discord.Color.green()
                    embed = discord.Embed(
                        title=summary_msg,
                        color=color
                    )
                    
                    for i, result_item in enumerate(results, 1):
                        icon = categories_dict.get(result_item["category"], "💰")
                        
                        # Check if this item is duplicated
                        is_dup = any(dup["item"]["description"] == result_item["description"] and 
                                    dup["item"]["date"] == result_item["date"] for dup in duplicates)
                        
                        status_icon = "⚠️" if is_dup else "✅"
                        value = f"${result_item['amount']} | {result_item['date']}\n_{result_item['description']}_"
                        embed.add_field(
                            name=f"{status_icon} {i}. {icon} {result_item['category']}",
                            value=value,
                            inline=False
                        )
                    
                    footer_text = f"合計: ${total_amount:.2f}"
                    if expense_ids:
                        footer_text += f" | 新增 IDs: {', '.join(map(str, expense_ids))}"
                    embed.set_footer(text=footer_text)
                    
                    await interaction.followup.send(embed=embed)
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        await interaction.followup.send(f"❌ 出錯：{str(e)}")


@bot.tree.command(name="list", description="查看最近的支出記錄")
@app_commands.describe(limit="顯示筆數（默認10）")
async def list_expenses(
    interaction: discord.Interaction,
    limit: int = 10
):
    """List recent expenses."""
    await interaction.response.defer()
    
    try:
        # Get user
        user_id = db.get_or_create_user(
            interaction.user.id,
            interaction.user.name
        )
        
        # Get expenses
        expenses = db.get_expenses(user_id, limit=limit)
        
        if not expenses:
            await interaction.followup.send("📭 還沒有記錄")
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"💰 支出記錄（最近 {len(expenses)} 筆）",
            color=discord.Color.blue()
        )
        
        categories_dict = {name: icon for name, icon in db.get_categories()}
        total = 0
        
        for expense in expenses:
            icon = categories_dict.get(expense["category"], "💰")
            value = f"${expense['amount']} | {expense['date']}\n_{expense['description']}_"
            embed.add_field(
                name=f"{icon} {expense['category']}",
                value=value,
                inline=False
            )
            total += expense['amount']
        
        embed.set_footer(text=f"合計: ${total:.2f}")
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ 出錯：{str(e)}")


@bot.tree.command(name="stats", description="查看月度統計")
@app_commands.describe(
    year="年份（默認當年）",
    month="月份 1-12（默認當月）"
)
async def stats_expenses(
    interaction: discord.Interaction,
    year: int = None,
    month: int = None
):
    """Show monthly statistics."""
    await interaction.response.defer()
    
    try:
        # Get current date if not provided
        now = datetime.now()
        year = year or now.year
        month = month or now.month
        
        # Validate month
        if not (1 <= month <= 12):
            await interaction.followup.send("❌ 月份必須在 1-12 之間")
            return
        
        # Get user
        user_id = db.get_or_create_user(
            interaction.user.id,
            interaction.user.name
        )
        
        # Get stats
        stats = db.get_monthly_stats(user_id, year, month)
        
        if stats["total"] == 0:
            await interaction.followup.send(f"📭 {year}年{month}月 沒有記錄")
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"📊 {year}年{month}月 統計",
            color=discord.Color.purple()
        )
        
        categories_dict = {name: icon for name, icon in db.get_categories()}
        
        # Sort by total amount descending
        sorted_categories = sorted(
            stats["by_category"].items(),
            key=lambda x: x[1]["total"],
            reverse=True
        )
        
        for category, data in sorted_categories:
            icon = categories_dict.get(category, "💰")
            value = f"${data['total']:.2f} ({data['count']} 筆)\n"
            avg = data['total'] / data['count']
            value += f"平均：${avg:.2f}"
            embed.add_field(
                name=f"{icon} {category}",
                value=value,
                inline=False
            )
        
        embed.set_footer(text=f"總計: ${stats['total']:.2f}")
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ 出錯：{str(e)}")


@bot.tree.command(name="delete", description="刪除記錄")
@app_commands.describe(expense_id="記錄ID")
async def delete_expense(
    interaction: discord.Interaction,
    expense_id: int
):
    """Delete an expense record."""
    await interaction.response.defer()
    
    try:
        # Get user
        user_id = db.get_or_create_user(
            interaction.user.id,
            interaction.user.name
        )
        
        # Delete expense
        deleted = db.delete_expense(expense_id, user_id)
        
        if deleted:
            embed = discord.Embed(
                title="✅ 刪除成功",
                description=f"記錄 ID {expense_id} 已刪除",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ 記錄不存在或無權限刪除")
        
    except Exception as e:
        await interaction.followup.send(f"❌ 出錯：{str(e)}")


@bot.tree.command(name="categories", description="查看所有分類")
async def show_categories(interaction: discord.Interaction):
    """Show all available categories."""
    await interaction.response.defer()
    
    try:
        categories = db.get_categories()
        
        embed = discord.Embed(
            title="📂 可用分類",
            color=discord.Color.gold(),
            description="在 /add 命令中使用分類名稱"
        )
        
        cat_text = "\n".join([f"{icon} {name}" for name, icon in categories])
        embed.add_field(name="分類列表", value=cat_text, inline=False)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ 出錯：{str(e)}")


# ==================== Run bot ====================

def main():
    """Start the bot."""
    if not DISCORD_TOKEN:
        print("❌ Error: DISCORD_TOKEN not configured")
        return
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
