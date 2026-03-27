from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional


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
    async def extract_info(self, raw_text: str, image_path: Optional[Path] = None) -> Optional[Dict]:
        """
        Args:
            raw_text: Raw OCR output string.
            image_path: Optional cropped image path for multimodal extraction.
        Returns:
            Dict with extracted fields, or None on failure.
        """
        ...

    async def select_best_candidate(self, scene_image_path: Path, candidates: List[Dict]) -> Optional[Dict]:
        """
        Optional multimodal ranking step to choose the best price tag candidate
        for a full scene image. Implementations may override this.
        """
        return None


class BaseTTS(ABC):

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Generate full audio bytes for the provided text."""
        ...

    async def stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """Default stream implementation that yields a single synthesized chunk."""
        yield await self.synthesize(text)
