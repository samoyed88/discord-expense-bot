import pytest
import os
import json
from unittest.mock import patch, MagicMock
from gemini_client import GeminiClient


@pytest.fixture
def gemini_client():
    """Create GeminiClient with mocked API."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-12345"}):
        client = GeminiClient()
        return client


class TestGeminiClient:
    def test_init_with_api_key(self):
        """Test initialization with API key."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            client = GeminiClient()
            assert client is not None

    def test_init_without_api_key(self):
        """Test initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                GeminiClient()

    def test_parse_json_response_valid(self, gemini_client):
        """Test parsing valid JSON response."""
        response = '''
        Here's the extracted data:
        {
            "amount": 100.50,
            "date": "2026-03-15",
            "description": "午餐",
            "category": "食物"
        }
        Some additional text here.
        '''
        
        result = gemini_client._parse_json_response(response)
        
        assert result["amount"] == 100.50
        assert result["date"] == "2026-03-15"
        assert result["description"] == "午餐"
        assert result["category"] == "食物"

    def test_parse_json_response_invalid_json(self, gemini_client):
        """Test parsing invalid JSON."""
        response = "This is not valid JSON at all"
        
        with pytest.raises(ValueError, match="No valid JSON found"):
            gemini_client._parse_json_response(response)

    def test_parse_json_response_missing_field(self, gemini_client):
        """Test parsing JSON with missing required field."""
        response = '{"amount": 100.50, "date": "2026-03-15"}'
        
        with pytest.raises(ValueError, match="Missing required field"):
            gemini_client._parse_json_response(response)

    def test_parse_json_response_invalid_amount(self, gemini_client):
        """Test parsing with invalid amount."""
        response = '''
        {
            "amount": "not-a-number",
            "date": "2026-03-15",
            "description": "午餐",
            "category": "食物"
        }
        '''
        
        with pytest.raises(ValueError, match="Invalid amount"):
            gemini_client._parse_json_response(response)

    def test_parse_json_response_invalid_category(self, gemini_client):
        """Test parsing with invalid category (should default to 其他)."""
        response = '''
        {
            "amount": 100.50,
            "date": "2026-03-15",
            "description": "午餐",
            "category": "無效分類"
        }
        '''
        
        result = gemini_client._parse_json_response(response)
        assert result["category"] == "其他"

    def test_validate_result_valid(self, gemini_client):
        """Test validation of valid result."""
        result = {
            "amount": 100.50,
            "date": "2026-03-15",
            "description": "午餐",
            "category": "食物"
        }
        
        is_valid, error = gemini_client.validate_result(result)
        assert is_valid is True
        assert error == ""

    def test_validate_result_missing_field(self, gemini_client):
        """Test validation with missing field."""
        result = {
            "amount": 100.50,
            "date": "2026-03-15"
        }
        
        is_valid, error = gemini_client.validate_result(result)
        assert is_valid is False
        assert "Missing field" in error

    def test_validate_result_invalid_amount(self, gemini_client):
        """Test validation with invalid amount."""
        result = {
            "amount": -100,
            "date": "2026-03-15",
            "description": "午餐",
            "category": "食物"
        }
        
        is_valid, error = gemini_client.validate_result(result)
        assert is_valid is False
        assert "negative" in error.lower() or "positive" in error.lower()

    def test_validate_result_invalid_date(self, gemini_client):
        """Test validation with invalid date."""
        result = {
            "amount": 100.50,
            "date": "2026/03/15",
            "description": "午餐",
            "category": "食物"
        }
        
        is_valid, error = gemini_client.validate_result(result)
        assert is_valid is False
        assert "date format" in error

    def test_validate_result_invalid_category(self, gemini_client):
        """Test validation with invalid category."""
        result = {
            "amount": 100.50,
            "date": "2026-03-15",
            "description": "午餐",
            "category": "無效分類"
        }
        
        is_valid, error = gemini_client.validate_result(result)
        assert is_valid is False
        assert "Invalid category" in error

    def test_parse_expense_text(self, gemini_client):
        """Test parsing expense from text."""
        with patch.object(gemini_client.model, 'generate_content') as mock_generate:
            mock_response = MagicMock()
            mock_response.text = '''
            {
                "amount": 100.50,
                "date": "2026-03-15",
                "description": "午餐",
                "category": "食物"
            }
            '''
            mock_generate.return_value = mock_response
            
            result = gemini_client.parse_expense_text("午餐花了100元")
            
            assert result["amount"] == 100.50
            assert result["category"] == "食物"
            mock_generate.assert_called_once()

    def test_extract_from_receipt_file_not_found(self, gemini_client):
        """Test extraction with non-existent file."""
        with pytest.raises(FileNotFoundError):
            gemini_client.extract_from_receipt("/path/to/nonexistent/image.jpg")

    def test_extract_from_receipt(self, gemini_client):
        """Test extraction from receipt image."""
        # Create a temporary test image
        import tempfile
        from PIL import Image
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create a simple test image
            img = Image.new('RGB', (100, 100), color='white')
            img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            with patch.object(gemini_client.model, 'generate_content') as mock_generate:
                mock_response = MagicMock()
                mock_response.text = '''
                {
                    "amount": 150.00,
                    "date": "2026-03-15",
                    "description": "晚餐",
                    "category": "食物"
                }
                '''
                mock_generate.return_value = mock_response
                
                result = gemini_client.extract_from_receipt(tmp_path)
                
                assert result["amount"] == 150.00
                assert result["description"] == "晚餐"
                mock_generate.assert_called_once()
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestMultipleExpenses:
    """Test multiple expense extraction from single image."""
    
    def test_parse_multiple_expenses(self, gemini_client):
        """Test parsing multiple expenses from response."""
        response = '''
        [
            {
                "amount": 50.0,
                "date": "2026-03-15",
                "description": "項目1",
                "category": "食物"
            },
            {
                "amount": 30.0,
                "date": "2026-03-15",
                "description": "項目2",
                "category": "交通"
            }
        ]
        '''
        
        result = gemini_client._parse_json_response(response)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["amount"] == 50.0
        assert result[1]["amount"] == 30.0

    def test_validate_multiple_expenses(self, gemini_client):
        """Test validation of multiple expenses."""
        results = [
            {
                "amount": 100.50,
                "date": "2026-03-15",
                "description": "午餐",
                "category": "食物"
            },
            {
                "amount": 50.0,
                "date": "2026-03-15",
                "description": "車費",
                "category": "交通"
            }
        ]
        
        is_valid, error = gemini_client.validate_result(results)
        assert is_valid is True
        assert error == ""

    def test_validate_multiple_with_invalid(self, gemini_client):
        """Test validation fails for invalid item in list."""
        results = [
            {
                "amount": 100.50,
                "date": "2026-03-15",
                "description": "午餐",
                "category": "食物"
            },
            {
                "amount": -50.0,
                "date": "2026-03-15",
                "description": "車費",
                "category": "交通"
            }
        ]
        
        is_valid, error = gemini_client.validate_result(results)
        assert is_valid is False
        assert "negative" in error.lower() or "positive" in error.lower()
