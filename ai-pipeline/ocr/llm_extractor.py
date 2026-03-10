import json
import logging
from typing import Optional, Dict

from ollama import AsyncClient
from config import settings
from interfaces import BaseLLMExtractor

logger = logging.getLogger("LLMExtractor")


class OllamaLLMExtractor(BaseLLMExtractor):

    def __init__(self):
        self._model = settings.LLM_MODEL
        self._client = AsyncClient(host=settings.OLLAMA_HOST)

    async def extract_info(self, raw_text: str) -> Optional[Dict]:
        """
        Args:
            raw_text: Raw OCR output string.
        Returns:
            Dict with item_name, price, expiration_date fields, or None on failure.
        """
        prompt = f"""You are a helpful assistant that extracts information from price tags.
Extract the following fields from the OCR text below:
- "name": name of the product
- "price": numerical price only (no currency symbols)
- "expiration_date": expiration or best-before date

Output ONLY a valid JSON object. Set missing fields to null.

OCR TEXT:
{raw_text}
"""
        try:
            logger.info(f"Requesting extraction from {self._model}...")
            response = await self._client.generate(
                model=self._model,
                prompt=prompt,
                format="json",
                options={"temperature": 0.0}
            )
            result = json.loads(response["response"])
            logger.info(f"Extraction result: {result}")
            return result
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return None
