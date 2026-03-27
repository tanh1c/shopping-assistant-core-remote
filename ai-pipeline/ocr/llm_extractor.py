import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import requests

try:
    from .config import settings
    from .interfaces import BaseLLMExtractor
except ImportError:
    from config import settings
    from interfaces import BaseLLMExtractor

logger = logging.getLogger("LLMExtractor")


class OCRLLMExtractor(BaseLLMExtractor):

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self._provider = (provider or settings.LLM_PROVIDER).lower()
        self._model = model or settings.LLM_MODEL
        self._api_key = api_key or settings.LLM_API_KEY
        self._base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self._timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
        self._ollama_client = None

        if self._provider == "ollama":
            try:
                from ollama import AsyncClient
            except ImportError as exc:
                raise ImportError(
                    "Ollama provider requires the `ollama` package to be installed."
                ) from exc

            self._ollama_client = AsyncClient(host=settings.OLLAMA_HOST)
        elif self._provider in {"alibaba", "dashscope"}:
            if not self._api_key:
                logger.warning("Alibaba provider selected but no API key was configured.")
        else:
            raise ValueError(f"Unsupported OCR LLM provider: {self._provider}")

    async def extract_info(self, raw_text: str, image_path: Optional[Path] = None) -> Optional[Dict]:
        """
        Args:
            raw_text: Raw OCR output string.
            image_path: Optional image path for multimodal API models.
        Returns:
            Dict with item_name, price, and normalized price-tag text, or None on failure.
        """
        if self._provider == "ollama":
            return await self._extract_ollama(raw_text)
        if self._provider in {"alibaba", "dashscope"}:
            return await asyncio.to_thread(self._extract_alibaba, raw_text, image_path)
        raise ValueError(f"Unsupported OCR LLM provider: {self._provider}")

    def _build_prompt(self, raw_text: str) -> str:
        return f"""You extract information from Vietnamese supermarket price tags.

Rules:
- "name": product name in Vietnamese with proper diacritics if available
- "price": integer number only (remove dots, commas, currency symbols)
- "category": choose exactly one of: dairy, snack, beverage, bakery, condiment, personal_care, household, other
- "price_tag_text_normalized": cleaned Vietnamese text from the price tag with proper diacritics when possible

Common Vietnamese keywords:
- "GIÁ", "GIA BAN", "PRICE"

Price format rules in Vietnam:
- Prices often use "." or "," as thousand separators
- Currency symbols like "đ", "VND", "VNĐ" may appear nearby
- The output price must be an integer with no separators or currency symbols
- If OCR text is missing Vietnamese accents, restore them when you are reasonably confident
- Do not hallucinate a product if the tag is unrelated or unreadable
- Ignore expiration dates or lot codes if they appear; they are not needed

If an image is provided, use it together with the OCR text.
Return ONLY JSON:
{{
  "name": string or null,
  "price": number or null,
  "category": string or null,
  "price_tag_text_normalized": string or null
}}

OCR TEXT:
{raw_text}
"""

    async def _extract_ollama(self, raw_text: str) -> Optional[Dict]:
        prompt = self._build_prompt(raw_text)

        try:
            logger.info(f"Requesting extraction from Ollama model {self._model}...")
            response = await self._ollama_client.generate(
                model=self._model,
                prompt=prompt,
                format="json",
                options={
                    "temperature": 0.0,
                    "num_ctx": 1024,
                },
            )
            result = self._normalize_payload(json.loads(response["response"]))
            logger.info(f"Extraction result: {result}")
            return result
        except Exception as exc:
            logger.error(f"Ollama extraction failed: {exc}")
            return None

    def _extract_alibaba(self, raw_text: str, image_path: Optional[Path] = None) -> Optional[Dict]:
        if not self._api_key:
            logger.error("Missing API key for Alibaba DashScope provider.")
            return None

        prompt = self._build_prompt(raw_text)
        user_content = [{"type": "text", "text": prompt}]

        if image_path is not None and image_path.exists():
            mime_type = self._guess_mime_type(image_path)
            image_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_base64}",
                    },
                }
            )

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise information extraction assistant. Output JSON only.",
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        try:
            logger.info(
                "Requesting extraction from Alibaba provider | model=%s | image=%s",
                self._model,
                bool(image_path and image_path.exists()),
            )
            response = requests.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = self._normalize_payload(json.loads(self._extract_text_content(content)))
            logger.info(f"Extraction result: {result}")
            return result
        except Exception as exc:
            logger.error(f"Alibaba extraction failed: {exc}")
            return None

    async def select_best_candidate(self, scene_image_path: Path, candidates: List[Dict]) -> Optional[Dict]:
        if self._provider in {"alibaba", "dashscope"}:
            return await asyncio.to_thread(self._select_best_candidate_alibaba, scene_image_path, candidates)
        return self._select_best_candidate_fallback(candidates)

    def _select_best_candidate_alibaba(self, scene_image_path: Path, candidates: List[Dict]) -> Optional[Dict]:
        if not self._api_key:
            return self._select_best_candidate_fallback(candidates)

        viable_candidates = [candidate for candidate in candidates if candidate.get("result")]
        if not viable_candidates:
            return None

        ranked_candidates = self._prepare_selection_candidates(viable_candidates)

        user_content = [
            {
                "type": "text",
                "text": self._build_selection_prompt(scene_image_path, ranked_candidates),
            }
        ]

        if scene_image_path.exists():
            user_content.append(self._image_content(scene_image_path))

        for candidate in ranked_candidates:
            candidate_result = candidate["result"]
            user_content.append(
                {
                    "type": "text",
                    "text": (
                        f"Candidate #{candidate['candidate_id']} | file={candidate['crop_name']}\n"
                        f"- role_hint={self._candidate_role_hint(candidate)}\n"
                        f"- extracted_name={candidate_result.get('name')}\n"
                        f"- extracted_price={candidate_result.get('price')}\n"
                        f"- extracted_category={candidate_result.get('category')}\n"
                        f"- normalized_tag_text={candidate_result.get('price_tag_text_normalized')}\n"
                        f"- raw_ocr_text={candidate_result.get('raw_ocr_text')}"
                    ),
                }
            )
            crop_path = Path(candidate["crop_path"])
            if crop_path.exists():
                user_content.append(self._image_content(crop_path))

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a precise Vietnamese retail assistant. "
                        "Choose the single correct price tag for the main product in the scene. "
                        "Product naming must come primarily from the visible product package in the full scene image, "
                        "not from noisy price-tag OCR. Use the selected price tag mainly for the price. "
                        "If package text and price-tag OCR disagree, trust the package text. "
                        "Normalize Vietnamese text with proper diacritics. Output JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        try:
            logger.info(
                "Selecting best candidate | scene=%s | candidates=%s",
                scene_image_path.name,
                len(ranked_candidates),
            )
            response = requests.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            selection = self._normalize_payload(
                json.loads(self._extract_text_content(content)),
                selection_mode=True,
            )
            logger.info(f"Selection result: {selection}")
            return selection
        except Exception as exc:
            logger.error(f"Alibaba candidate selection failed: {exc}")
            return self._select_best_candidate_fallback(candidates)

    def _build_selection_prompt(self, scene_image_path: Path, candidates: List[Dict]) -> str:
        return f"""You are given:
1. One full scene image named {scene_image_path.name}
2. Several candidate price-tag crops detected from that scene
3. OCR and extracted info for each candidate

Your task:
- First identify the main product name from the visible product package in the full scene image
- Then choose the ONE candidate price tag that belongs to that product
- The main product is usually the most central, most readable, or most prominent product in the photo
- Prefer the product/package text in the scene image over price-tag OCR when deciding the final product_name
- Use the selected price tag mainly for price, barcode, and secondary confirmation
- If package text and price-tag OCR disagree, trust the package text
- Do not "correct" a clearly visible package word into a different Vietnamese word just because the tag OCR is noisy
- Example: if the package clearly shows "PHỐ", keep "Phố", not "Phở"
- If several candidates belong to the same product, choose the clearest price tag with a readable price
- If another candidate or the full scene image shows the product name more clearly than the selected price tag, use that clearer wording for product_name
- Normalize Vietnamese text with proper diacritics
- If a product or tag uses Vietnamese without accents, rewrite it with natural Vietnamese accents when you are confident
- Classify the product into exactly one of: dairy, snack, beverage, bakery, condiment, personal_care, household, other

Return ONLY JSON:
{{
  "selected_candidate_id": number or null,
  "selected_crop_name": string or null,
  "product_name": string or null,
  "product_name_source": string or null,
  "price": number or null,
  "category": string or null,
  "price_tag_text_normalized": string or null,
  "reason": string,
  "confidence": number
}}
"""

    def _prepare_selection_candidates(self, candidates: List[Dict]) -> List[Dict]:
        price_ranked = sorted(
            candidates,
            key=lambda candidate: (
                candidate["result"].get("price") is not None,
                candidate["result"].get("name") is not None,
                len(candidate["result"].get("raw_ocr_text") or ""),
            ),
            reverse=True,
        )
        context_ranked = sorted(
            candidates,
            key=lambda candidate: (
                len(candidate["result"].get("raw_ocr_text") or ""),
                candidate["result"].get("name") is not None,
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
        raw_text_length = len(result.get("raw_ocr_text") or "")
        if result.get("price") is not None:
            return "likely_price_tag"
        if raw_text_length >= 20 or result.get("name"):
            return "likely_product_text_or_context"
        return "unclear"

    def _image_content(self, image_path: Path) -> Dict:
        mime_type = self._guess_mime_type(image_path)
        image_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{image_base64}",
            },
        }

    def _select_best_candidate_fallback(self, candidates: List[Dict]) -> Optional[Dict]:
        viable_candidates = [candidate for candidate in candidates if candidate.get("result")]
        if not viable_candidates:
            return None

        best_candidate = sorted(
            viable_candidates,
            key=lambda candidate: (
                candidate["result"].get("price") is not None,
                candidate["result"].get("name") is not None,
                len(candidate["result"].get("raw_ocr_text") or ""),
            ),
            reverse=True,
        )[0]

        result = best_candidate["result"]
        return self._normalize_payload({
            "selected_candidate_id": best_candidate["candidate_id"],
            "selected_crop_name": best_candidate["crop_name"],
            "product_name": result.get("name"),
            "product_name_source": f"candidate_{best_candidate['candidate_id']}",
            "price": result.get("price"),
            "category": result.get("category"),
            "price_tag_text_normalized": result.get("price_tag_text_normalized"),
            "reason": "Fallback selection based on the most complete candidate.",
            "confidence": 0.35,
        }, selection_mode=True)

    def _normalize_payload(self, payload: Dict, selection_mode: bool = False) -> Dict:
        normalized = dict(payload or {})

        text_keys = ["price_tag_text_normalized", "reason", "selected_crop_name", "category"]
        if selection_mode:
            text_keys.extend(["product_name", "product_name_source"])
        else:
            text_keys.append("name")

        for key in text_keys:
            if key in normalized:
                normalized[key] = self._normalize_text(normalized.get(key))

        if "price" in normalized:
            normalized["price"] = self._normalize_price(normalized.get("price"))

        if "category" in normalized:
            normalized["category"] = self._normalize_category(normalized.get("category"))

        if "selected_candidate_id" in normalized:
            normalized["selected_candidate_id"] = self._normalize_integer(
                normalized.get("selected_candidate_id")
            )

        if "confidence" in normalized:
            normalized["confidence"] = self._normalize_confidence(normalized.get("confidence"))

        return normalized

    def _normalize_text(self, value):
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        cleaned = " ".join(value.split()).strip()
        return cleaned or None

    def _normalize_price(self, value):
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        text = str(value).strip()
        if not text:
            return None

        digits_only = "".join(ch for ch in text if ch.isdigit())
        if not digits_only:
            return None

        try:
            return int(digits_only)
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
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
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
            "personal_care": "personal_care",
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

    def _extract_text_content(self, content) -> str:
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            text = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") in {None, "text", "output_text"}
            ).strip()
        else:
            raise ValueError(f"Unsupported content type: {type(content)!r}")

        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _guess_mime_type(self, image_path: Path) -> str:
        suffix = image_path.suffix.lower()
        if suffix == ".png":
            return "image/png"
        if suffix in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if suffix == ".webp":
            return "image/webp"
        return "application/octet-stream"


class OllamaLLMExtractor(OCRLLMExtractor):

    def __init__(self):
        super().__init__(provider="ollama")


class AlibabaLLMExtractor(OCRLLMExtractor):

    def __init__(self):
        super().__init__(provider="alibaba")


def build_llm_extractor(provider: Optional[str] = None) -> OCRLLMExtractor:
    return OCRLLMExtractor(provider=provider)
