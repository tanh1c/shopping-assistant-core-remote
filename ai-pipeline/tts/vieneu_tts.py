import asyncio
import logging
import tempfile
from pathlib import Path


logger = logging.getLogger("VieneuTTS")


class VieneuTTS:
    """Async adapter around the Vieneu Vietnamese TTS engine."""

    def __init__(self):
        try:
            from vieneu import Vieneu
        except ImportError as exc:
            raise ImportError(
                "VieneuTTS requires the `vieneu` package to be installed."
            ) from exc

        self._tts = Vieneu()

    async def synthesize(self, text: str) -> bytes:
        if not text.strip():
            logger.warning("Empty text passed to VieneuTTS.")
            return b""

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self._infer_and_read, text)
        except Exception as exc:
            logger.error(f"TTS synthesis failed: {exc}")
            return b""

    def _infer_and_read(self, text: str) -> bytes:
        audio_spec = self._tts.infer(text=text)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)

        self._tts.save(audio_spec, tmp_path)

        try:
            return tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)

    def close(self) -> None:
        try:
            self._tts.close()
        except Exception:
            pass
