"""
LLM Extraction Module - Trích xuất thông tin có cấu trúc từ OCR text
"""
import json
import os
from typing import Dict, List, Optional

import requests
from pydantic import BaseModel, Field


class ExtractedInfo(BaseModel):
    """Schema cho thông tin sản phẩm"""
    product_name: Optional[str] = Field(default=None, description="Tên sản phẩm")
    price: Optional[float] = Field(default=None, description="Giá tiền")
    currency: str = Field(default="VND", description="Đơn vị tiền tệ")
    category: Optional[str] = Field(default=None, description="Danh mục sản phẩm")
    ocr_text_normalized: Optional[str] = Field(default=None, description="OCR text đã được chuẩn hóa với dấu")
    confidence: float = Field(default=0.0, description="Độ tin cậy của extraction")


class LLMExtractor:
    """
    Wrapper cho LLM extraction
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "alibaba",
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("ALIBABA_API_KEY")
        self.model = model or os.getenv("LLM_MODEL")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.timeout_seconds = timeout_seconds or int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

        if self.provider == "gemini":
            self.model = self.model or "gemini-2.0-flash"
            self._init_gemini()
        elif self.provider == "ollama":
            self.model = self.model or "llama3.2"
            self._init_ollama()
        elif self.provider in {"alibaba", "dashscope"}:
            self.model = self.model or "qwen3.5-plus"
            self.base_url = (self.base_url or "https://coding-intl.dashscope.aliyuncs.com/v1").rstrip("/")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

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

    def extract(
        self,
        ocr_text: str,
        detected_object: str = "",
        image_base64: Optional[str] = None,
        image_mime_type: str = "image/png",
    ) -> ExtractedInfo:
        """
        Extract thông tin từ OCR text

        Args:
            ocr_text: Raw text từ OCR
            detected_object: Tên vật thể từ YOLO
            image_base64: Optional cropped image for multimodal models
            image_mime_type: MIME type for the provided base64 image

        Returns:
            ExtractedInfo object
        """
        if self.provider == "gemini":
            return self._extract_gemini(ocr_text, detected_object)
        if self.provider == "ollama":
            return self._extract_ollama(ocr_text, detected_object)
        if self.provider in {"alibaba", "dashscope"}:
            return self._extract_alibaba(
                ocr_text=ocr_text,
                detected_object=detected_object,
                image_base64=image_base64,
                image_mime_type=image_mime_type,
            )
        raise ValueError(f"Unsupported provider: {self.provider}")

    def _build_prompt(self, ocr_text: str, detected_object: str) -> str:
        return f"""
        Extract structured product information from this OCR text.
        Return ONLY valid JSON with these fields: product_name, price, currency, category, ocr_text_normalized, confidence.

        Context:
        - Detected object category: {detected_object}
        - OCR text: {ocr_text}

        Rules:
        - Price should be a number without currency symbols
        - Vietnamese thousand separators "." and "," should be normalized to a number
        - Confidence between 0.0 and 1.0
        - Category must be exactly one of: dairy, snack, beverage, bakery, condiment, personal_care, household, other
        - If field cannot be determined, set it to null
        - If an image is provided, use it together with OCR text
        - Product name should be normalized to proper Vietnamese spelling with diacritics when possible
        - Add a field `ocr_text_normalized` with cleaned Vietnamese text from the price tag or label
        - Ignore expiry dates, lot codes, and unrelated numbers if they appear

        Example output:
        {{
            "product_name": "Sữa tươi Vinamilk 180ml",
            "price": 15000,
            "currency": "VND",
            "category": "dairy",
            "ocr_text_normalized": "Sting vàng lon 320ml, giá 15.000 đồng",
            "confidence": 0.92
        }}
        """

    def _extract_gemini(self, ocr_text: str, detected_object: str) -> ExtractedInfo:
        """Extraction dùng Google Gemini"""
        prompt = self._build_prompt(ocr_text, detected_object)

        if self.client is None:
            return self._mock_extract(ocr_text, detected_object)

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )

        try:
            data = self._normalize_payload(json.loads(self._extract_json_text(response.text)))
            return ExtractedInfo(**data)
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")
            return self._mock_extract(ocr_text, detected_object)

    def _extract_ollama(self, ocr_text: str, detected_object: str) -> ExtractedInfo:
        """Extraction dùng Ollama (local LLM)"""
        prompt = self._build_prompt(ocr_text, detected_object)

        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        data = response.json()
        return ExtractedInfo(**self._normalize_payload(json.loads(data['response'])))

    def _extract_alibaba(
        self,
        ocr_text: str,
        detected_object: str,
        image_base64: Optional[str] = None,
        image_mime_type: str = "image/png",
    ) -> ExtractedInfo:
        prompt = self._build_prompt(ocr_text, detected_object)

        if not self.api_key:
            print("Alibaba provider requires LLM_API_KEY or ALIBABA_API_KEY")
            return self._mock_extract(ocr_text, detected_object)

        user_content = [{"type": "text", "text": prompt}]
        if image_base64:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image_mime_type};base64,{image_base64}"
                    },
                }
            )

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a precise retail product extraction assistant. Output JSON only.",
                    },
                    {
                        "role": "user",
                        "content": user_content,
                    },
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]

        try:
            data = self._normalize_payload(json.loads(self._extract_json_text(content)))
            return ExtractedInfo(**data)
        except Exception as e:
            print(f"Error parsing Alibaba response: {e}")
            return self._mock_extract(ocr_text, detected_object)

    def select_best_candidate(
        self,
        scene_image_base64: Optional[str],
        candidates: List[Dict],
        scene_image_mime_type: str = "image/png",
    ) -> Optional[Dict]:
        if self.provider in {"alibaba", "dashscope"} and scene_image_base64:
            return self._select_best_candidate_alibaba(
                scene_image_base64=scene_image_base64,
                candidates=candidates,
                scene_image_mime_type=scene_image_mime_type,
            )
        return self._select_best_candidate_fallback(candidates)

    def _select_best_candidate_alibaba(
        self,
        scene_image_base64: str,
        candidates: List[Dict],
        scene_image_mime_type: str = "image/png",
    ) -> Optional[Dict]:
        if not self.api_key:
            return self._select_best_candidate_fallback(candidates)

        viable_candidates = [candidate for candidate in candidates if candidate.get("result")]
        if not viable_candidates:
            return None

        ranked_candidates = self._prepare_selection_candidates(viable_candidates)

        user_content = [
            {
                "type": "text",
                "text": self._build_selection_prompt(ranked_candidates),
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{scene_image_mime_type};base64,{scene_image_base64}"
                },
            },
        ]

        for candidate in ranked_candidates:
            candidate_result = candidate["result"]
            user_content.append(
                {
                    "type": "text",
                    "text": (
                        f"Candidate #{candidate['candidate_id']} | detection_idx={candidate.get('detection_idx')}\n"
                        f"- role_hint={self._candidate_role_hint(candidate)}\n"
                        f"- detected_object={candidate.get('detected_object')}\n"
                        f"- product_name={candidate_result.get('product_name')}\n"
                        f"- price={candidate_result.get('price')}\n"
                        f"- category={candidate_result.get('category')}\n"
                        f"- ocr_text_normalized={candidate_result.get('ocr_text_normalized')}\n"
                        f"- raw_ocr_text={candidate.get('ocr_text')}"
                    ),
                }
            )
            if candidate.get("image_base64"):
                user_content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                f"data:{candidate.get('image_mime_type', 'image/png')};base64,"
                                f"{candidate['image_base64']}"
                            )
                        },
                    }
                )

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a precise Vietnamese retail assistant. "
                            "Choose the single correct price tag for the main product in the full scene image. "
                            "Product naming must come primarily from the visible product package in the full scene image, "
                            "not from noisy price-tag OCR. Use the selected price tag mainly for the price. "
                            "If package text and price-tag OCR disagree, trust the package text. "
                            "Classify the final product into exactly one fixed retail category. "
                            "Normalize Vietnamese text with proper diacritics and output JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": user_content,
                    },
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        return self._normalize_payload(
            json.loads(self._extract_json_text(content)),
            selection_mode=True,
        )

    def _build_selection_prompt(self, candidates: List[Dict]) -> str:
        return f"""
        You are given:
        - One full scene image that may contain multiple products and multiple price tags
        - {len(candidates)} candidate price-tag crops with OCR and extracted info

        Your task:
        - First identify the main product name from the visible product package in the full scene image
        - Then choose the ONE candidate price tag that belongs to that product
        - Match by brand, flavor, packaging, size, color, and nearby product context
        - Prefer the product/package text in the scene image over price-tag OCR when deciding the final product_name
        - Use the selected price tag mainly for price and secondary confirmation
        - If package text and price-tag OCR disagree, trust the package text
        - Do not replace a clearly visible package word with a different Vietnamese word just because the tag OCR is noisy
        - Example: if the package clearly shows "PHỐ", keep "Phố", not "Phở"
        - If another candidate or the full scene image shows the product name more clearly than the selected price tag, use that clearer wording for product_name
        - If several candidates describe the same product, choose the clearest candidate with a readable price
        - Normalize Vietnamese text with proper diacritics when you are reasonably confident
        - Classify the final product into exactly one of: dairy, snack, beverage, bakery, condiment, personal_care, household, other

        Return ONLY JSON:
        {{
            "selected_candidate_id": number or null,
            "selected_detection_idx": number or null,
            "product_name": string or null,
            "product_name_source": string or null,
            "price": number or null,
            "currency": "VND",
            "category": string or null,
            "ocr_text_normalized": string or null,
            "reason": string,
            "confidence": number
        }}
        """

    def _prepare_selection_candidates(self, candidates: List[Dict]) -> List[Dict]:
        price_ranked = sorted(
            candidates,
            key=lambda candidate: (
                candidate["result"].get("price") is not None,
                candidate["result"].get("product_name") is not None,
                len(candidate.get("ocr_text") or ""),
            ),
            reverse=True,
        )
        context_ranked = sorted(
            candidates,
            key=lambda candidate: (
                len(candidate.get("ocr_text") or ""),
                candidate["result"].get("product_name") is not None,
                candidate["result"].get("price") is None,
            ),
            reverse=True,
        )

        combined: List[Dict] = []
        seen_ids = set()
        for bucket in (price_ranked[:6], context_ranked[:4]):
            for candidate in bucket:
                candidate_id = candidate.get("candidate_id")
                if candidate_id in seen_ids:
                    continue
                combined.append(candidate)
                seen_ids.add(candidate_id)
                if len(combined) >= 8:
                    return combined
        return combined

    def _candidate_role_hint(self, candidate: Dict) -> str:
        result = candidate.get("result") or {}
        raw_text_length = len(candidate.get("ocr_text") or "")
        if result.get("price") is not None:
            return "likely_price_tag"
        if raw_text_length >= 20 or result.get("product_name"):
            return "likely_product_text_or_context"
        return "unclear"

    def _select_best_candidate_fallback(self, candidates: List[Dict]) -> Optional[Dict]:
        viable_candidates = [candidate for candidate in candidates if candidate.get("result")]
        if not viable_candidates:
            return None

        best_candidate = sorted(
            viable_candidates,
            key=lambda candidate: (
                candidate["result"].get("price") is not None,
                candidate["result"].get("product_name") is not None,
                len(candidate.get("ocr_text") or ""),
            ),
            reverse=True,
        )[0]

        best_result = best_candidate["result"]
        return self._normalize_payload(
            {
                "selected_candidate_id": best_candidate["candidate_id"],
                "selected_detection_idx": best_candidate.get("detection_idx"),
                "product_name": best_result.get("product_name"),
                "product_name_source": f"candidate_{best_candidate['candidate_id']}",
                "price": best_result.get("price"),
                "currency": best_result.get("currency", "VND"),
                "category": best_result.get("category"),
                "ocr_text_normalized": best_result.get("ocr_text_normalized"),
                "reason": "Fallback selection based on the most complete candidate.",
                "confidence": best_result.get("confidence", 0.35),
            },
            selection_mode=True,
        )

    def _extract_json_text(self, content) -> str:
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            text = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") in {None, "text", "output_text"}
            ).strip()
        else:
            raise ValueError(f"Unsupported response content type: {type(content)!r}")

        if text.startswith('```json'):
            text = text[7:]
        if text.endswith('```'):
            text = text[:-3]
        return text.strip()

    def _normalize_payload(self, payload: Dict, selection_mode: bool = False) -> Dict:
        normalized = dict(payload or {})

        text_keys = ["reason", "currency", "category"]
        if selection_mode:
            text_keys.extend(["product_name", "product_name_source", "ocr_text_normalized"])
        else:
            text_keys.extend(["product_name", "ocr_text_normalized"])

        for key in text_keys:
            if key in normalized:
                normalized[key] = self._normalize_text(normalized.get(key))

        if not normalized.get("currency"):
            normalized["currency"] = "VND"
        else:
            normalized["currency"] = normalized["currency"].upper()

        if "price" in normalized:
            normalized["price"] = self._normalize_price(normalized.get("price"))

        if "confidence" in normalized:
            normalized["confidence"] = self._normalize_confidence(normalized.get("confidence"))

        if "category" in normalized:
            normalized["category"] = self._normalize_category(normalized.get("category"))

        if selection_mode:
            if "selected_candidate_id" in normalized:
                normalized["selected_candidate_id"] = self._normalize_integer(
                    normalized.get("selected_candidate_id")
                )
            if "selected_detection_idx" in normalized:
                normalized["selected_detection_idx"] = self._normalize_integer(
                    normalized.get("selected_detection_idx")
                )

        return normalized

    def _normalize_text(self, value):
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        cleaned = " ".join(value.split()).strip()
        return cleaned or None

    def _normalize_price(self, value):
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            try:
                return float(int(value))
            except (TypeError, ValueError):
                return None

        text = str(value).strip()
        if not text:
            return None

        digits_only = "".join(ch for ch in text if ch.isdigit())
        if not digits_only:
            return None

        try:
            return float(int(digits_only))
        except ValueError:
            return None

    def _normalize_integer(self, value):
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _normalize_confidence(self, value):
        if value is None:
            return 0.0
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, numeric))

    def _normalize_category(self, value):
        normalized = self._normalize_text(value)
        if not normalized:
            return None

        slug = normalized.lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "drink": "beverage",
            "drinks": "beverage",
            "beverages": "beverage",
            "water": "beverage",
            "coffee": "beverage",
            "tea": "beverage",
            "candy": "snack",
            "chips": "snack",
            "confectionery": "snack",
            "bread": "bakery",
            "pastry": "bakery",
            "seasoning": "condiment",
            "sauce": "condiment",
            "personalcare": "personal_care",
            "personal-care": "personal_care",
            "hygiene": "personal_care",
            "care": "personal_care",
            "household_goods": "household",
            "homecare": "household",
            "cleaning": "household",
            "cleaner": "household",
            "unknown": "other",
        }
        slug = aliases.get(slug, slug)
        allowed = {
            "dairy",
            "snack",
            "beverage",
            "bakery",
            "condiment",
            "personal_care",
            "household",
            "other",
        }
        return slug if slug in allowed else "other"

    def _mock_extract(self, ocr_text: str, detected_object: str) -> ExtractedInfo:
        """Mock extraction khi không có API key"""
        import re

        price_match = re.search(r'(\d+[.,\d]*\s*[VNĐ₫]?)', ocr_text)
        price = None
        if price_match:
            price_str = price_match.group(1).replace(',', '').replace('.', '').replace(' ', '')
            price_str = re.sub(r'[VNĐ₫]', '', price_str)
            try:
                price = float(price_str)
            except ValueError:
                pass

        return ExtractedInfo(
            product_name=detected_object or "Unknown Product",
            price=price,
            confidence=0.5,
        )


# Demo usage
if __name__ == '__main__':
    extractor = LLMExtractor(provider=os.getenv("LLM_PROVIDER", "alibaba"))

    test_ocr = "Sữa tươi Vinamilk 180ml\n15,000đ\nHSD: 20/12/2026"
    result = extractor.extract(test_ocr, "sữa")

    print("Extracted Info:")
    print(f"  Product: {result.product_name}")
    print(f"  Price: {result.price} {result.currency}")
    print(f"  Confidence: {result.confidence}")
