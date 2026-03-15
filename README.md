# Discord Expense Bot 🤖💰

一個具有 AI 動力圖片識別的 Discord 記帳機器人，使用 Google Gemini 自動識別收據和發票。

## ✨ 功能特色

- 📝 **文字記帳** - 快速記錄支出（金額、分類、日期、描述）
- 📸 **AI 圖片識別** - 上傳收據/發票，自動提取金額、日期、分類
- 👥 **多用戶隔離** - 每個用戶只能看/編輯自己的記錄
- 📂 **分類管理** - 食物、交通、娛樂、購物、工作、健康等預設分類
- 📊 **月度統計** - 按分類統計支出，自動計算平均值
- 🔒 **完全隔離** - Discord 多伺服器支持，用戶數據完全隔離

## 🛠️ 技術棧

| 項目 | 詳情 |
|------|------|
| **模型** | gemini-3-flash-preview（最新版） |
| **框架** | discord.py 2.7.1 |
| **數據庫** | SQLite3 |
| **非阻塞** | ✅ 異步 API 調用 |
| **功能** | 文字記帳、圖片識別（含多筆）、月度統計 |

## 📋 快速開始

### 前置需求

1. **Python 3.9 以上版本**
2. **Discord 伺服器**（你是伺服器管理員）
3. **Discord Bot Token** - [取得方式](#獲取-discord-bot-token)
4. **Google Gemini API Key** - [取得方式](#獲取-gemini-api-key)

### 📦 安裝步驟

#### 1. 複製專案
```bash
git clone <repository-url>
cd discord-expense-bot
```

#### 2. 建立虛擬環境
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

#### 3. 安裝依賴
```bash
pip install -r requirements.txt
```

#### 4. 設定環境變數
```bash
cp .env.example .env
```

編輯 `.env` 檔案，填入你的令牌：
```env
DISCORD_TOKEN=你的_discord_bot_token
GEMINI_API_KEY=你的_gemini_api_密鑰
```

#### 5. 運行機器人
```bash
python bot.py
```

你應該會看到類似的輸出：
```
✅ Bot logged in as YourBotName#1234
✅ Synced 6 command(s)
```

---

## 🔐 設定你的 Discord Bot

### 獲取 Discord Bot Token

1. **打開 Discord Developer Portal**
   - 訪問 https://discord.com/developers/applications
   - 使用你的 Discord 帳號登入

2. **建立新 Application**
   - 點擊 "New Application"
   - 輸入名稱（例如：Expense Bot）
   - 點擊 "Create"

3. **建立 Bot**
   - 在左邊菜單選擇 "Bot"
   - 點擊 "Add Bot"
   - 在 TOKEN 區域點擊 "Copy"（複製 Token）
   - 粘貼到 `.env` 的 `DISCORD_TOKEN`

4. **設定 Bot 權限**
   - 在 Bot 頁面向下滑動到 "INTENT" 部分
   - 啟用以下 Intents:
     - ✅ Message Content Intent
     - ✅ Server Members Intent（選擇）

### 獲取 Gemini API Key

1. **打開 Google AI Studio**
   - 訪問 https://ai.google.dev/

2. **建立 API Key**
   - 點擊 "Get API Key"
   - 選擇 "Create API key in new project"
   - 複製生成的 API Key
   - 粘貼到 `.env` 的 `GEMINI_API_KEY`

### 邀請 Bot 到你的 Discord 伺服器

#### 方法 1：自動邀請連結

在 Discord Developer Portal:
1. 選擇你的 Application
2. 左邊菜單選擇 "OAuth2" → "URL Generator"
3. **選擇 Scopes**:
   - ✅ `bot`
   - ✅ `applications.commands`

4. **選擇 Permissions**:
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Read Message History
   - ✅ Use Application Commands
   - ✅ Read Messages/View Channels

5. **複製生成的 URL**
   - 生成的 URL 會自動調整所需權限
   - 複製該 URL 到瀏覽器
   - 選擇要邀請的伺服器
   - 點擊 "Authorize"

#### 方法 2：手動邀請

使用以下格式構建邀請 URL（用你的 Bot ID 替換 `YOUR_BOT_ID`）：

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=2048&scope=bot%20applications.commands
```

找到你的 Bot ID：
- Discord Developer Portal → Application → General Information → Application ID（就是你的 Bot ID）

---

## 📖 使用指南

### 可用命令

| 命令 | 參數 | 說明 | 範例 |
|------|------|------|------|
| `/add` | amount, category, description?, date? | 文字記帳 | `/add amount:100.5 category:食物 description:午餐` |
| `/add_image` | image, prompt? | 圖片識別記帳（支持多筆） | 上傳收據圖片 |
| `/list` | limit? | 查看最近記錄 | `/list limit:20` |
| `/stats` | year?, month? | 月度統計 | `/stats year:2026 month:3` |
| `/delete` | expense_id | 刪除記錄 | `/delete expense_id:5` |
| `/categories` | - | 查看分類列表 | `/categories` |

### 使用範例

#### 📝 文字記帳
```
/add amount:150.5 category:食物 description:晚餐 date:2026-03-15
```
Bot 會回應：
```
✅ 記錄成功
金額: $150.5
分類: 🍜 食物
日期: 2026-03-15
描述: 晚餐
記錄 ID: 42
```

## ⚠️ Discord Embed 限制

### Embed 字段限制
- **最多 25 個字段** - Discord API 限制
- 超過 25 筆交易時，Bot 自動使用表格格式

### 當前限制和解決方案

| 交易筆數 | 格式 | 優點 |
|---------|------|------|
| 1 筆 | 詳細格式（4 個字段） | 清晰易讀 |
| 2-25 筆 | 詳細格式（每筆一個字段） | 分類清楚 |
| >25 筆 | 表格格式（markdown 代碼塊） | 支持無限交易 |

### 表格格式特點

```
✅ 優點：
- 支持無限數量的交易
- 紧凑且易於閱讀
- 包含所有重要信息

❌ 限制：
- 描述會被截斷（最多 10 字符）
- 表格寬度固定
```

---

### 多筆交易識別
當上傳的收據/發票包含多筆交易時，Bot 會自動識別所有項目：

**單筆交易回應：**
```
✅ AI識別成功
金額: $150.5
分類: 🍜 食物
日期: 2026-03-15
描述: 晚餐
記錄 ID: 42
```

**多筆交易回應：**

*少於等於 25 筆（詳細格式）：*
```
✅ AI識別成功（3 筆）
1. 🍜 食物
$50.0 | 2026-03-15
_項目1: 米飯_

2. 🚗 交通
$30.0 | 2026-03-15
_停車費_

3. 🛍️ 購物
$20.0 | 2026-03-15
_飲料_

合計: $100.0 | 記錄 IDs: 42, 43, 44
```

*超過 25 筆（表格格式）：*
```
✅ AI識別成功（50 筆）

序號  | 金額    | 分類   | 日期       | 描述
----|---------|--------|----------|----------
1  | $50.00 | 食物   | 2026-03-15 | 米飯
2  | $30.00 | 交通   | 2026-03-15 | 停車費
... （省略）
50 | $10.00 | 其他   | 2026-03-15 | 雜項

合計: $2000.0 | 記錄 IDs: 42, 43, 44, ..., 91
```

### 自定義提示詞
在 `/add_image` 命令中添加 `prompt` 參數，幫助 AI 更準確地識別：

```
/add_image [圖片] prompt:這是一張超市購物收據，請識別所有商品和金額
```

**提示詞使用案例：**
- `prompt:請識別所有單品的價格，總共有5個商品`
- `prompt:這是餐廳菜單，請識別每道菜的價格`
- `prompt:請特別注意小數點和幣種轉換`

---
1. 在 Discord 輸入 `/add_image`
2. 上傳收據/發票圖片
3. （可選）在 prompt 欄位添加額外說明，例如：「這張收據有多個項目」
4. Bot 會自動識別：
   - 💰 金額
   - 📅 日期
   - 📂 分類
   - 📝 描述
   
**重要：若圖片包含多筆交易，Bot 會自動識別所有項目並一次性記錄！**

使用提示詞幫助識別：
```
/add_image [圖片] prompt:請仔細識別每個項目的金額，有多筆購物記錄
```

#### 📊 查看統計
```
/stats month:3
```
Bot 會顯示該月份的：
- 分類別支出總額
- 每個分類的筆數和平均值
- 月度總支出

---

## 🧪 測試

執行所有測試：
```bash
TEST_MODE=true python -m pytest tests/ -v
```

測試結果：
```
✅ 9 個數據庫測試
✅ 15 個 AI/Gemini 測試
✅ 5 個 Bot 命令測試
────────────────────
✅ 總計 29 個測試 - 100% 通過
```

## 📁 項目結構

```
discord-expense-bot/
├── bot.py                 # 🤖 Discord Bot 主程式 (6個命令)
├── database.py            # 💾 SQLite 數據層 (9個操作)
├── gemini_client.py       # 🧠 Gemini AI 集成 (圖片+文本識別)
├── config.py              # ⚙️ 中央配置文件
├── requirements.txt       # 📦 Python 依賴
├── .env.example           # 📋 環境變數模板
├── README.md              # 📖 本文件
├── tests/                 # 🧪 完整測試套件
│   ├── test_database.py   # 數據層測試 (9 個)
│   ├── test_gemini.py     # AI 測試 (15 個)
│   └── test_bot.py        # Bot 測試 (5 個)
└── venv/                  # 🐍 Python 虛擬環境
```

## 📊 數據存儲

所有數據存儲在本機 SQLite 數據庫 `expenses.db`：

### 資料表

**users** - 用戶映射
```
id | discord_id | username | created_at
```

**expenses** - 支出記錄
```
id | user_id | amount | description | category | date | created_at
```

**categories** - 分類定義
```
id | name | icon
```

## 🔄 Git Commit 歷史

專案採用清晰的 Git 版本控制，每個功能模組都有對應的 commit：

```
235972a ✨ 實現Discord Bot框架和命令系統
861291e 🧠 實現Gemini AI集成：圖片和文本識別
6270236 💾 實現數據層：SQLite數據庫模型和操作
1d82928 🚀 初始化項目：配置git、虛擬環境和依賴
```

## ⚙️ 配置說明

### 環境變數 (`.env`)

| 變數 | 必須 | 說明 | 範例 |
|------|------|------|------|
| `DISCORD_TOKEN` | ✅ | Discord Bot Token | `MTA4MzMwNDA4NzYx...` |
| `GEMINI_API_KEY` | ✅ | Google Gemini API Key | `AIzaSyB...` |
| `DATABASE_NAME` | ❌ | 數據庫檔案名 | `expenses.db` |

### Gemini API 模型選擇

當前使用 **gemini-3-flash-preview**（推薦最新版本）

**支持的模型：**
```python
# 最新版本（推薦）
model_name = "gemini-3-flash-preview"   # 最新、最強大

# 備選穩定版本（如遇問題）
model_name = "gemini-2.0-flash"         # 較舊但穩定
```

修改 bot.py 初始化代碼來切換模型：
```python
gemini = GeminiClient(model_name="gemini-2.0-flash")  # 使用 2.0 版本
```

⚠️ **注意：** gemini-1.5-flash 已被下架，請勿使用

## 🐛 常見問題

### Q: Bot 顯示 "Synced 0 command(s)"
**A:** 檢查以下內容：
- 確認 `DISCORD_TOKEN` 正確
- 確認 Bot 有 "applications.commands" 範圍
- 重啟 Bot

### Q: `/add_image` 命令不工作
**A:** 確保：
- 設定了 `GEMINI_API_KEY`
- 上傳的是有效的圖片格式（JPG, PNG, GIF, WebP）
- 圖片清晰可見

### Q: 無法將 Bot 邀請到伺服器
**A:**
- 確認使用了正確的 OAuth2 邀請連結
- 確認你是伺服器管理員
- 檢查伺服器是否達到 Bot 上限

### Q: 如何備份我的數據？
**A:** 複製 `expenses.db` 檔案：
```bash
cp expenses.db expenses.db.backup
```

## 📞 支持

有問題或建議？歡迎提交 Issue 或聯繫開發者。

## 📄 授權

此專案使用 MIT 授權。詳見 LICENSE 檔案。

## 🎯 未來計劃

- [ ] 多帳本支持（共享群組記帳）
- [ ] 圖表可視化（柱狀圖、圓餅圖）
- [ ] Excel/PDF 匯出功能
- [ ] 定期支出提醒
- [ ] Docker 部署配置
- [ ] Web 儀表板
- [ ] 預算限制提醒

---

**祝你使用愉快！** 🎉
