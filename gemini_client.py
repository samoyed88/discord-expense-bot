import os
import base64
import json
import re
from typing import Optional, Dict
import google.generativeai as genai
from pathlib import Path


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini client with API key."""
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-3-flash-preview")

    def extract_from_receipt(self, image_path: str) -> Dict:
        """
        Extract expense information from receipt/invoice image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dict with keys: amount, date, description, category
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Read and encode image
        image_data = self._read_image(image_path)
        
        prompt = """
分析這張收據或發票圖片，請提取以下信息並以 JSON 格式返回：
- amount: 金額（數字，例如 100.50）
- date: 日期（格式 YYYY-MM-DD，如無法識別使用今天日期）
- description: 商品或服務描述（簡短）
- category: 自動判斷分類（從以下選擇：食物、交通、娛樂、購物、工作、健康、其他）

請只返回 JSON 對象，不要有其他文字。
示例格式：
{"amount": 100.50, "date": "2026-03-15", "description": "午餐", "category": "食物"}
"""

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

    def _parse_json_response(self, response_text: str) -> Dict:
        """Extract and parse JSON from response text."""
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
        if not json_match:
            raise ValueError(f"No JSON found in response: {response_text}")
        
        json_str = json_match.group(0)
        
        try:
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {str(e)}")
        
        # Validate required fields
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
        
        return result

    def validate_result(self, result: Dict) -> tuple[bool, str]:
        """
        Validate extracted result.
        
        Returns:
            (is_valid, error_message)
        """
        if not isinstance(result, dict):
            return False, "Result is not a dictionary"
        
        required_fields = ["amount", "date", "description", "category"]
        for field in required_fields:
            if field not in result:
                return False, f"Missing field: {field}"
        
        # Validate amount
        if not isinstance(result["amount"], (int, float)) or result["amount"] <= 0:
            return False, "Amount must be a positive number"
        
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
