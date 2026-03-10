"""
LLM Extraction Module - Trích xuất thông tin có cấu trúc từ OCR text
"""
import json
from typing import Dict, Optional
from pydantic import BaseModel, Field


class ExtractedInfo(BaseModel):
    """Schema cho thông tin sản phẩm"""
    product_name: str = Field(description="Tên sản phẩm")
    price: Optional[float] = Field(default=None, description="Giá tiền")
    currency: str = Field(default="VND", description="Đơn vị tiền tệ")
    expiry_date: Optional[str] = Field(default=None, description="Hạn sử dụng (YYYY-MM-DD)")
    category: Optional[str] = Field(default=None, description="Danh mục sản phẩm")
    confidence: float = Field(default=0.0, description="Độ tin cậy của extraction")


class LLMExtractor:
    """
    Wrapper cho LLM extraction
    """

    def __init__(self, api_key: Optional[str] = None, provider: str = "gemini"):
        self.provider = provider
        self.api_key = api_key

        if provider == "gemini":
            self._init_gemini()
        elif provider == "ollama":
            self._init_ollama()

    def _init_gemini(self):
        """Khởi tạo Google Gemini client"""
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        except ImportError:
            print("Cần cài đặt: pip install google-generativeai")
            self.client = None

    def _init_ollama(self):
        """Khởi tạo Ollama (local LLM)"""
        self.ollama_url = "http://localhost:11434"

    def extract(self, ocr_text: str, detected_object: str = "") -> ExtractedInfo:
        """
        Extract thông tin từ OCR text

        Args:
            ocr_text: Raw text từ OCR
            detected_object: Tên vật thể từ YOLO

        Returns:
            ExtractedInfo object
        """
        if self.provider == "gemini":
            return self._extract_gemini(ocr_text, detected_object)
        elif self.provider == "ollama":
            return self._extract_ollama(ocr_text, detected_object)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _extract_gemini(self, ocr_text: str, detected_object: str) -> ExtractedInfo:
        """Extraction dùng Google Gemini"""
        prompt = f"""
        Extract structured product information from this OCR text.
        Return ONLY valid JSON with these fields: product_name, price, currency, expiry_date, category, confidence.

        Context:
        - Detected object category: {detected_object}
        - OCR text: {ocr_text}

        Rules:
        - Price should be a number (no commas or currency symbols)
        - Expiry date in YYYY-MM-DD format
        - Confidence between 0.0 and 1.0
        - If field cannot be determined, set to null

        Example output:
        {{
            "product_name": "Sữa tươi Vinamilk 180ml",
            "price": 15000,
            "currency": "VND",
            "expiry_date": "2026-12-20",
            "category": "dairy",
            "confidence": 0.92
        }}
        """

        if self.client is None:
            # Fallback: mock extraction
            return self._mock_extract(ocr_text, detected_object)

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        try:
            # Extract JSON from response
            json_str = response.text.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:-3]
            data = json.loads(json_str)
            return ExtractedInfo(**data)
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error parsing LLM response: {e}")
            return self._mock_extract(ocr_text, detected_object)

    def _extract_ollama(self, ocr_text: str, detected_object: str) -> ExtractedInfo:
        """Extraction dùng Ollama (local LLM)"""
        import requests

        prompt = f"""Extract product info from OCR text. Return JSON only.
        OCR: {ocr_text}
        Object: {detected_object}
        """

        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
        )

        data = response.json()
        return ExtractedInfo(**json.loads(data['response']))

    def _mock_extract(self, ocr_text: str, detected_object: str) -> ExtractedInfo:
        """Mock extraction khi không có API key"""
        import re

        # Simple regex extraction (fallback)
        price_match = re.search(r'(\d+[,\d]*\s*[VNĐ₫]?)', ocr_text)
        price = None
        if price_match:
            price_str = price_match.group(1).replace(',', '').replace(' ', '')
            price_str = re.sub(r'[VNĐ₫]', '', price_str)
            try:
                price = float(price_str)
            except ValueError:
                pass

        return ExtractedInfo(
            product_name=detected_object or "Unknown Product",
            price=price,
            confidence=0.5  # Low confidence for mock
        )


# Demo usage
if __name__ == '__main__':
    # Test với mock extraction
    extractor = LLMExtractor()

    test_ocr = "Sữa tươi Vinamilk 180ml\n15,000đ\nHSD: 20/12/2026"
    result = extractor.extract(test_ocr, "sữa")

    print("Extracted Info:")
    print(f"  Product: {result.product_name}")
    print(f"  Price: {result.price} {result.currency}")
    print(f"  Expiry: {result.expiry_date}")
    print(f"  Confidence: {result.confidence}")
