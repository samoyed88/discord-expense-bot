# 🚀 快速開始 (5 分鐘)

## 1️⃣ 取得 Bot Token 和 API Key

### Discord Bot Token
1. 打開 https://discord.com/developers/applications
2. 點擊 "New Application"
3. 選擇 "Bot" 標籤 → "Add Bot"
4. 複製 TOKEN

### Gemini API Key  
1. 打開 https://ai.google.dev/
2. 點擊 "Get API Key"
3. 複製 API Key

## 2️⃣ 配置環境

```bash
cd /Users/ianho/discord-expense-bot
source venv/bin/activate
```

編輯 `.env`：
```env
DISCORD_TOKEN=你的token
GEMINI_API_KEY=你的key
```

## 3️⃣ 邀請 Bot 到伺服器

打開此 URL（用你的 Bot ID 替換）：
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=2048&scope=bot%20applications.commands
```

**找 Bot ID：** Developer Portal → Application → General Information → Application ID

## 4️⃣ 運行 Bot

```bash
python bot.py
```

你會看到：
```
✅ Bot logged in as YourBotName#1234
✅ Synced 6 command(s)
```

## 5️⃣ 在 Discord 中使用

在伺服器輸入任意命令：
- `/add amount:100 category:食物` - 文字記帳
- `/add_image` - 上傳收據
- `/list` - 查看記錄
- `/stats` - 統計
- `/categories` - 分類列表

---

**遇到問題？** 查看 README.md 的「常見問題」章節
