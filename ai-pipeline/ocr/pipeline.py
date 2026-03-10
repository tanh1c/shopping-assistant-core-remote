import json
import logging
from pathlib import Path
from typing import Optional, Dict

from interfaces import BaseOCRExtractor, BaseLLMExtractor

logger = logging.getLogger("Pipeline")


class PriceTagPipeline:

    def __init__(self, ocr: BaseOCRExtractor, llm: BaseLLMExtractor):
        self._ocr = ocr
        self._llm = llm

    async def run(self, file_path: Path) -> Optional[Dict]:
        """
        Args:
            file_path: Path to the price tag image or document.
        Returns:
            Dict with extracted fields, or None on failure.
        """
        logger.info(f"--- PIPELINE START: {file_path.name} ---")

        raw_text = await self._ocr.extract_text(file_path)
        if not raw_text:
            logger.error("OCR returned no text. Aborting.")
            return None

        logger.info(f"OCR preview: {raw_text[:100]}...")

        result = await self._llm.extract_info(raw_text)
        if result:
            print("\n" + "=" * 50)
            print("EXTRACTION RESULT:")
            print(json.dumps(result, indent=4, ensure_ascii=False))
            print("=" * 50)
        else:
            logger.error("LLM extraction failed.")

        return result
