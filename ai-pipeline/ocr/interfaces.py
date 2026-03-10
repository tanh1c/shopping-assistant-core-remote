from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict


class BaseOCRExtractor(ABC):

    @abstractmethod
    async def extract_text(self, file_path: Path) -> Optional[str]:
        """
        Args:
            file_path: Path to the image or document file.
        Returns:
            Extracted text string, or None on failure.
        """
        ...


class BaseLLMExtractor(ABC):

    @abstractmethod
    async def extract_info(self, raw_text: str) -> Optional[Dict]:
        """
        Args:
            raw_text: Raw OCR output string.
        Returns:
            Dict with extracted fields, or None on failure.
        """
        ...
