import os
import base64
import json
import re
from typing import Optional, Dict, List
import asyncio
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai
from pathlib import Path


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-3-flash-preview"):
        """Initialize Gemini client with API key.
        
        Args:
            api_key: Gemini API key (or use GEMINI_API_KEY env var)
            model_name: Model to use (default: gemini-3-flash-preview)
        """
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.executor = ThreadPoolExecutor(max_workers=2)  # Async API calls

    def extract_from_receipt(self, image_path: str, custom_prompt: Optional[str] = None) -> Dict | List[Dict]:
        """
        Extract expense information from receipt/invoice image (BLOCKING - use extract_from_receipt_async in async contexts).
        
        Args:
            image_path: Path to image file
            custom_prompt: Optional custom instruction to help AI
            
        Returns:
            Dict with keys: amount, date, description, category
            OR List[Dict] if multiple items detected
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Read and encode image
        image_data = self._read_image(image_path)
        
        prompt = """你是一個專業的收據解析助手。

分析這張收據或發票圖片。如果有多筆交易，請全部提取。

請嚴格按照以下格式返回 JSON（不要包含任何其他文字）：

如果只有一筆交易，返回單個 JSON 對象：
{"amount": 100.50, "date": "2026-03-15", "description": "午餐", "category": "食物"}

如果有多筆交易，返回 JSON 陣列：
[
  {"amount": 50.0, "date": "2026-03-15", "description": "米飯", "category": "食物"},
  {"amount": 30.0, "date": "2026-03-15", "description": "停車費", "category": "交通"}
]

每筆交易必須包含：
- amount: 金額（數字，例如 100.50，只取正數）
  * 若識別到符號，只提取數字部分
  * 必須是正數，不能是負數或零
- date: 日期（格式 YYYY-MM-DD，如無法識別使用今天日期）
- description: 商品或服務描述（簡短）
- category: 分類（必須從以下選擇：食物、交通、娛樂、購物、工作、健康、其他）

重要說明：
1. 只返回 JSON，不要包含任何其他文字
2. 確保 JSON 格式正確（可用 JSON 驗證器驗證）
3. 每個金額都必須是正數
4. 如果有多筆交易但無法區分，仍然提取為多筆
"""
        
        if custom_prompt:
            prompt += f"\n用戶額外提示：{custom_prompt}\n"
        
        # Add strict instruction at the end
        prompt += "\n\n重要：只返回有效的 JSON，不要有其他文字！"
        
        try:
            response = self.model.generate_content([
                prompt,
                image_data
            ])
            
            # Parse JSON from response
            result = self._parse_json_response(response.text)
            return result
        except Exception as e:
            raise Exception(f"Failed to process image with Gemini: {str(e)}")
    
    async def extract_from_receipt_async(self, image_path: str, custom_prompt: Optional[str] = None) -> Dict | List[Dict]:
        """
        Extract expense information from receipt/invoice image (ASYNC - non-blocking).
        
        Use this in Discord bot commands to avoid blocking the event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.extract_from_receipt,
            image_path,
            custom_prompt
        )

    def parse_expense_text(self, text: str) -> Dict:
        """
        Parse expense information from natural language text.
        
        Args:
            text: User input text (e.g., "午餐花了100元")
            
        Returns:
            Dict with keys: amount, date, description, category
        """
        prompt = f"""
用戶輸入了以下支出信息（可能不完整）："{text}"

請幫我提取支出信息並以 JSON 格式返回：
- amount: 金額（數字，例如 100.50）
- date: 日期（格式 YYYY-MM-DD，如無法識別使用今天日期）
- description: 商品或服務描述
- category: 自動判斷分類（從以下選擇：食物、交通、娛樂、購物、工作、健康、其他）

如果信息不完整，請根據上下文合理推斷。
請只返回 JSON 對象，不要有其他文字。
示例格式：
{{"amount": 100.50, "date": "2026-03-15", "description": "午餐", "category": "食物"}}
"""

        try:
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            return result
        except Exception as e:
            raise Exception(f"Failed to parse text with Gemini: {str(e)}")

    def _read_image(self, image_path: str) -> Dict:
        """Read and encode image file."""
        with open(image_path, "rb") as image_file:
            image_data = base64.standard_b64encode(image_file.read()).decode("utf-8")
        
        # Determine MIME type
        ext = Path(image_path).suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        mime_type = mime_types.get(ext, "image/jpeg")
        
        return {
            "mime_type": mime_type,
            "data": image_data
        }

    def _parse_json_response(self, response_text: str) -> Dict | List[Dict]:
        """Extract and parse JSON from response text."""
        # Clean up the response - remove common text before/after JSON
        response_text = response_text.strip()
        
        # Try multiple strategies to extract JSON
        json_str = None
        
        # Strategy 1: Look for JSON array [...]
        array_match = re.search(r'\[\s*\{.*?\}\s*(?:,\s*\{.*?\}\s*)*\]', response_text, re.DOTALL)
        if array_match:
            json_str = array_match.group(0)
        
        # Strategy 2: Look for JSON object {...}
        if not json_str:
            # Find the first { and match it with the last }
            start_idx = response_text.find('{')
            if start_idx != -1:
                # Count braces to find matching }
                brace_count = 0
                for i in range(start_idx, len(response_text)):
                    if response_text[i] == '{':
                        brace_count += 1
                    elif response_text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = response_text[start_idx:i+1]
                            break
        
        # Strategy 3: Check if response starts with [ (array)
        if not json_str:
            start_idx = response_text.find('[')
            if start_idx != -1:
                # Count brackets to find matching ]
                bracket_count = 0
                for i in range(start_idx, len(response_text)):
                    if response_text[i] == '[':
                        bracket_count += 1
                    elif response_text[i] == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            json_str = response_text[start_idx:i+1]
                            break
        
        if not json_str:
            raise ValueError(f"No valid JSON found in response: {response_text[:200]}")
        
        try:
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            # If JSON parsing fails, provide more detailed error
            raise ValueError(f"Invalid JSON in response: {str(e)}\nJSON: {json_str[:200]}")
        
        # Handle both single dict and list of dicts
        if isinstance(result, list):
            # Validate each item
            for item in result:
                self._validate_single_result(item)
        else:
            # Single dict
            self._validate_single_result(result)
        
        return result
    
    def _validate_single_result(self, result: Dict) -> None:
        """Validate a single expense result."""
        if not isinstance(result, dict):
            raise ValueError("Result item is not a dictionary")
        
        required_fields = ["amount", "date", "description", "category"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate amount is number
        try:
            result["amount"] = float(result["amount"])
        except (ValueError, TypeError):
            raise ValueError(f"Invalid amount: {result['amount']}")
        
        # Validate category
        valid_categories = ["食物", "交通", "娛樂", "購物", "工作", "健康", "其他"]
        if result["category"] not in valid_categories:
            result["category"] = "其他"  # Default to others

    def validate_result(self, result: Dict | List[Dict]) -> tuple[bool, str]:
        """
        Validate extracted result.
        
        Returns:
            (is_valid, error_message)
        """
        if isinstance(result, list):
            # Validate each item in list
            if not result:
                return False, "Empty result list"
            
            for i, item in enumerate(result):
                is_valid, error = self._validate_single_dict(item)
                if not is_valid:
                    return False, f"Item {i+1}: {error}"
            return True, ""
        else:
            # Single dict
            return self._validate_single_dict(result)
    
    def _validate_single_dict(self, result: Dict) -> tuple[bool, str]:
        """Validate a single expense dict."""
        if not isinstance(result, dict):
            return False, "Result is not a dictionary"
        
        required_fields = ["amount", "date", "description", "category"]
        for field in required_fields:
            if field not in result:
                return False, f"Missing field: {field}"
        
        # Validate and normalize amount
        try:
            amount = float(result["amount"])
            # 金額必須是正數，如果是負數則取絕對值（可能是 AI 錯誤）
            if amount < 0:
                # 嘗試自動修正：如果金額為負，可能是識別錯誤
                # 但我們還是返回錯誤，讓用戶知道
                return False, f"Amount is negative: {amount} (should be positive)"
            if amount == 0:
                return False, "Amount cannot be zero"
            result["amount"] = amount
        except (ValueError, TypeError):
            return False, f"Invalid amount format: {result['amount']}"
        
        # Validate date format
        from datetime import datetime
        try:
            datetime.strptime(result["date"], "%Y-%m-%d")
        except ValueError:
            return False, "Invalid date format (should be YYYY-MM-DD)"
        
        # Validate category
        valid_categories = ["食物", "交通", "娛樂", "購物", "工作", "健康", "其他"]
        if result["category"] not in valid_categories:
            return False, f"Invalid category: {result['category']}"
        
        return True, ""
