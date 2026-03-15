# 故障排除和性能優化指南

## 🔧 常見問題解決

### 1. 金額驗證失敗（負數或零）

**症狀：** `❌ 識別失敗：Amount is negative: -50.0` 或 `Amount cannot be zero`

**原因：**
- Gemini AI 誤識別金額符號（如減號）
- 收據品質不佳導致識別錯誤
- 圖片傾斜或模糊

**解決方案：**

✅ **上傳更清晰的圖片**
```
確保：
- 正面拍攝（不要傾斜）
- 足夠光線，避免陰影
- 金額數字清晰可見
- 解析度至少 1080p
```

✅ **使用提示詞指導 AI**
```
/add_image [圖片] prompt:這是收據，請識別金額部分，確保是正數
```

✅ **檢查圖片內容**
- 確認圖片確實包含正確的金額
- 避免包含負數或折扣符號

---

### 2. Discord Heartbeat 被阻塞

**症狀：**
```
WARNING discord.gateway Shard ID None heartbeat blocked for more than 10 seconds
```

**原因：** 同步 API 調用在事件循環中阻塞了 Discord

**解決方案：** ✅ 已修復！
- Bot 現在使用異步 `extract_from_receipt_async()`
- 不會阻塞 Discord 事件循環
- 更新到最新版本自動解決

---

### 3. JSON 解析失敗

**症狀：** `❌ 識別失敗：No JSON found in response`

**原因：**
- 圖片品質太低
- 收據/發票內容不清楚
- Gemini 無法識別

**解決方案：**
```
✅ 重新上傳更清晰的圖片
✅ 使用提示詞幫助 AI：
   /add_image [圖片] prompt:請仔細識別每個項目的金額
```

---

### 4. 無法邀請 Bot 到伺服器

**症狀：** 邀請連結無效或被拒絕

**解決方案：**
1. 確認 Bot ID 正確（Discord Developer Portal）
2. 檢查 OAuth2 權限設置
3. 確保勾選了：
   - ✅ `bot` scope
   - ✅ `applications.commands` scope
   - ✅ Send Messages
   - ✅ Embed Links

---

### 5. 多筆交易只識別為單筆

**症狀：** 收據有多個項目，但只返回一筆

**原因：**
- 項目之間間距太小
- 圖片品質不佳
- 模型設置問題

**解決方案：**
```
使用提示詞告訴 AI：
/add_image [圖片] prompt:這張收據有3個不同的商品，請分別識別每個項目的金額
```

---

## ⚡ 性能優化

### 1. 快速識別（推薦用於即時記帳）

```python
# bot.py
gemini = GeminiClient(model_name="gemini-1.5-flash")
```

**優點：**
- ⚡ 最快（3-8 秒）
- 💰 成本最低
- ✅ 穩定可靠

**缺點：**
- 複雜收據準確度稍低

---

### 2. 高準確度（推薦用於重要記錄）

```python
# bot.py
gemini = GeminiClient(model_name="gemini-1.5-pro")
```

**優點：**
- 🎯 最高準確度
- 複雜收據識別能力強

**缺點：**
- 🐢 較慢（10-20 秒）
- 💸 成本較高

---

### 3. 混合策略（最靈活）

```python
# bot.py - 初始化兩個客戶端
gemini_fast = GeminiClient(model_name="gemini-1.5-flash")
gemini_accurate = GeminiClient(model_name="gemini-1.5-pro")

# 在命令中根據需要選擇
async def add_image_expense(interaction, image, prompt=None, mode="fast"):
    if mode == "fast":
        result = await gemini_fast.extract_from_receipt_async(temp_path, prompt)
    else:
        result = await gemini_accurate.extract_from_receipt_async(temp_path, prompt)
```

---

## 📊 響應時間參考

| 模型 | 平均時間 | 準確度 | 成本 |
|------|---------|--------|------|
| gemini-1.5-flash | 3-8 秒 | ⭐⭐⭐⭐ | $ |
| gemini-1.5-pro | 10-20 秒 | ⭐⭐⭐⭐⭐ | $$ |
| gemini-2.0-flash | 5-12 秒 | ⭐⭐⭐⭐ | $ |

---

## 🔐 API 配額和限制

### 免費層配額

Google Gemini API 免費層限制：
- **每分鐘請求數**：15 RPM（Requests Per Minute）
- **每天請求數**：500 RPD
- **令牌限制**：32K 輸入，8K 輸出（gemini-1.5-flash）

### 超過配額時

**症狀：** `429 Too Many Requests` 或 `RATE_LIMIT_EXCEEDED`

**解決方案：**
1. 購買付費配額（$1 起）
2. 實現速率限制器：
```python
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests=15, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    async def acquire(self):
        now = datetime.now()
        # 清除過期請求
        self.requests = [t for t in self.requests if t > now - timedelta(seconds=self.time_window)]
        
        if len(self.requests) >= self.max_requests:
            wait_time = self.time_window - (now - self.requests[0]).total_seconds()
            await asyncio.sleep(wait_time)
        
        self.requests.append(now)

# 在 bot.py 中使用
limiter = RateLimiter()
# 在每個 API 調用前：
await limiter.acquire()
result = await gemini.extract_from_receipt_async(...)
```

---

## 🧪 測試

### 運行所有測試
```bash
source venv/bin/activate
TEST_MODE=true python -m pytest tests/ -v
```

### 運行特定測試
```bash
# 只測試 Gemini 功能
pytest tests/test_gemini.py -v

# 只測試多筆交易
pytest tests/test_gemini.py::TestMultipleExpenses -v

# 只測試數據庫
pytest tests/test_database.py -v
```

---

## 📈 監控和日誌

### 啟用詳細日誌
```python
# bot.py 開頭添加
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看 Gemini API 日誌
logging.getLogger("google.generativeai").setLevel(logging.DEBUG)
```

### 常用日誌查看
```bash
# 查看實時日誌
tail -f bot_output.log

# 查看錯誤
grep ERROR bot_output.log

# 統計 API 調用
grep "generate_content" bot_output.log | wc -l
```

---

## 💡 最佳實踐

### 1. 圖片質量
- ✅ 清晰的照片（解析度 ≥ 1080p）
- ✅ 好光線，避免陰影和眩光
- ❌ 模糊或倾斜的照片

### 2. 提示詞使用
```
好例子：
- "這是超市收據，有 5 個商品"
- "請逐個識別每行的金額和商品名"
- "注意小數點和貨幣符號"

不好例子：
- "幫我識別"（太模糊）
- "快點識別"（無法幫助 AI）
```

### 3. 批量處理
```python
# 優化：一次處理多張圖片
async def batch_add_images(interaction, images):
    for image in images:
        result = await gemini.extract_from_receipt_async(...)
        # 處理結果
        await asyncio.sleep(1)  # 避免速率限制
```

---

## 🆘 聯繫支援

如果遇到以下問題，請檢查：

| 問題 | 檢查項目 |
|------|---------|
| API 密鑰錯誤 | 確認 `.env` 文件中的 `GEMINI_API_KEY` 正確 |
| Bot 不回應 | 檢查 `DISCORD_TOKEN` 和伺服器權限 |
| 識別失敗 | 上傳更清晰的圖片或使用提示詞 |
| 超時 | 切換到 gemini-1.5-flash 或增加耐心等待 |

---

**更新時間：** 2026-03-15
**Bot 版本：** 1.2.0 (含異步支持和多筆識別)
