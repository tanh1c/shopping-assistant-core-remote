import json
import logging
from pathlib import Path
from typing import Optional, Dict

try:
    from .interfaces import BaseOCRExtractor, BaseLLMExtractor, BaseTTS
except ImportError:
    from interfaces import BaseOCRExtractor, BaseLLMExtractor, BaseTTS

logger = logging.getLogger("Pipeline")


class PriceTagPipeline:

    def __init__(
        self,
        ocr: BaseOCRExtractor,
        llm: BaseLLMExtractor,
        tts: Optional[BaseTTS] = None,
    ):
        self._ocr = ocr
        self._llm = llm
        self._tts = tts

    async def run(self, file_path: Path) -> Optional[Dict]:
        """
        Args:
            file_path: Path to the price tag image or document.
        Returns:
            Dict with extracted fields, or None on failure.
        """
        logger.info(f"--- PIPELINE START: {file_path.name} ---")

        # OCR
        raw_text = await self._ocr.extract_text(file_path)
        if not raw_text:
            logger.error("OCR returned no text. Aborting.")
            return None

        logger.info(f"OCR preview: {raw_text[:100]}...")

        # LLM
        result = await self._llm.extract_info(raw_text, image_path=file_path)
        if result:
            result = dict(result)
            result.pop("expiration_date", None)
            result.setdefault("raw_ocr_text", raw_text)
            print("\n" + "=" * 50)
            print("EXTRACTION RESULT:")
            print(json.dumps(result, indent=4, ensure_ascii=False))
            print("=" * 50)
        else:
            logger.error("LLM extraction failed.")

        if self._tts and result:
            await self._handle_tts(result, file_path)

        return result

    def _format_for_tts(self, data: Dict) -> str:
        """Convert extracted JSON into a natural Vietnamese utterance."""
        parts = []

        if "name" in data and data["name"]:
            parts.append(f"Sản phẩm {data['name']}.")
        if "price" in data and data["price"] is not None:
            parts.append(f"Giá {self._format_price(data['price'])} đồng.")

        return " ".join(parts)

    def _format_price(self, price) -> str:
        try:
            price_int = int(price)
            if price_int >= 1000:
                return f"{price_int // 1000} nghìn"
            return str(price_int)
        except (TypeError, ValueError):
            return str(price)

    async def _handle_tts(self, result: Dict, file_path: Path) -> None:
        text = self._format_for_tts(result)
        if not text:
            logger.warning("TTS skipped because formatted text is empty.")
            return

        logger.info(f"TTS text: {text}")

        audio_bytes = await self._tts.synthesize(text)
        if not audio_bytes:
            logger.error("TTS returned empty audio bytes.")
            return

        output_path = Path("audio") / f"{file_path.stem}.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as output_file:
            output_file.write(audio_bytes)

        logger.info(f"Audio saved to {output_path}")
