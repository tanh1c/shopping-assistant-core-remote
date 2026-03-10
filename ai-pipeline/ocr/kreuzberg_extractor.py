import asyncio
from pathlib import Path
from typing import Optional, List, Dict
import logging

from kreuzberg import extract_file, OcrConfig, ExtractionConfig, ExtractionResult
from interfaces import BaseOCRExtractor

logger = logging.getLogger("KreuzbergOCR")


class KreuzbergFramework:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, backend: str = "paddleocr", language: str = "vi"):
        if not hasattr(self, '_initialized'):
            self.config = ExtractionConfig(
                ocr=OcrConfig(backend=backend, language=language)
            )
            self._initialized = True
            logger.info(f"KreuzbergFramework initialized | backend={backend} | language={language}")


class KreuzbergOCRExtractor(BaseOCRExtractor):

    def __init__(self, framework: KreuzbergFramework):
        self._framework = framework

    async def extract_text(self, file_path: Path) -> Optional[str]:
        """
        Args:
            file_path: Path to the image or document file.
        Returns:
            Extracted text content, or None on failure.
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        logger.info(f"Processing: {file_path.name}")
        try:
            result: ExtractionResult = await extract_file(file_path, config=self._framework.config)
            logger.info(f"Done: {file_path.name} | {len(result.content)} chars")
            return result.content
        except Exception as e:
            logger.error(f"Extraction failed for {file_path.name}: {e}")
            return None

    async def extract_batch(self, file_paths: List[Path]) -> Dict[Path, Optional[str]]:
        """
        Args:
            file_paths: List of file paths to process concurrently.
        Returns:
            Dict mapping each path to its extracted text, or None on failure.
        """
        tasks = [self.extract_text(p) for p in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {
            path: (None if isinstance(r, Exception) else r)
            for path, r in zip(file_paths, results)
        }
