"""
Text-to-Speech Module - Chuyển đổi văn bản thành giọng nói
"""
import asyncio
from pathlib import Path
from typing import Optional


class TTSEngine:
    """
    Wrapper cho Text-to-Speech engines
    """

    def __init__(self, provider: str = "gtts", lang: str = "vi"):
        self.provider = provider
        self.lang = lang
        self.cache_dir = Path("voices")
        self.cache_dir.mkdir(exist_ok=True)
        self.gTTS = None
        self.engine = None
        self.vieneu_engine = None

        if provider == "gtts":
            self._init_gtts()
        elif provider == "pyttsx3":
            self._init_pyttsx3()
        elif provider == "vieneu":
            self._init_vieneu()
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _init_gtts(self):
        """Khởi tạo gTTS"""
        try:
            from gtts import gTTS
            self.gTTS = gTTS
        except ImportError:
            print("Cần cài đặt: pip install gtts")
            self.gTTS = None

    def _init_pyttsx3(self):
        """Khởi tạo pyttsx3"""
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)  # Tốc độ nói
        except ImportError:
            print("Cần cài đặt: pip install pyttsx3")
            self.engine = None

    def _init_vieneu(self):
        """Khởi tạo Vieneu TTS"""
        try:
            try:
                from .vieneu_tts import VieneuTTS
            except ImportError:
                from tts.vieneu_tts import VieneuTTS
            self.vieneu_engine = VieneuTTS()
        except ImportError:
            print("Cần cài đặt Vieneu để dùng provider 'vieneu'")
            self.vieneu_engine = None

    def speak(self, text: str, play: bool = True) -> Optional[str]:
        """
        Chuyển văn bản thành giọng nói và phát

        Args:
            text: Văn bản cần đọc
            play: Có phát âm thanh ngay không

        Returns:
            Path đến file audio (nếu lưu)
        """
        if self.provider == "gtts":
            return self._speak_gtts(text, play)
        elif self.provider == "pyttsx3":
            return self._speak_pyttsx3(text, play)
        elif self.provider == "vieneu":
            return self._run_async(self.speak_async(text, play))
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def speak_async(self, text: str, play: bool = True) -> Optional[str]:
        """Async wrapper for providers that need to run inside an event loop."""
        if self.provider == "gtts":
            return await asyncio.to_thread(self._speak_gtts, text, play)
        if self.provider == "pyttsx3":
            return await asyncio.to_thread(self._speak_pyttsx3, text, play)
        if self.provider == "vieneu":
            return await self._speak_vieneu(text, play)
        raise ValueError(f"Unsupported provider: {self.provider}")

    def _speak_gtts(self, text: str, play: bool = True) -> Optional[str]:
        """Dùng gTTS (online)"""
        filepath = self._generate_gtts_file(text)
        if filepath is None:
            return None

        # Phát âm thanh
        if play:
            self._play_audio(filepath)

        return filepath

    def _speak_pyttsx3(self, text: str, play: bool = True) -> None:
        """Dùng pyttsx3 (offline)"""
        if self.engine is None:
            print("pyttsx3 not initialized")
            return

        if play:
            self.engine.say(text)
            self.engine.runAndWait()

    async def _speak_vieneu(self, text: str, play: bool = True) -> Optional[str]:
        filepath = await self._generate_vieneu_file(text)
        if filepath is None:
            return None

        if play:
            await asyncio.to_thread(self._play_audio, filepath)

        return filepath

    def _play_audio(self, filepath: str):
        """Phát file audio"""
        import platform
        system = platform.system()

        if system == "Windows":
            import os
            os.startfile(filepath)
        elif system == "Darwin":
            import subprocess
            subprocess.call(["afplay", filepath])
        else:  # Linux
            try:
                import subprocess
                subprocess.call(["aplay", filepath])
            except FileNotFoundError:
                print("Không tìm thấy trình phát audio. Cài đặt: sudo apt install alsa-utils")

    def generate_speech_file(self, text: str, output_path: Optional[str] = None) -> str:
        """
        Generate speech file mà không phát ngay

        Returns:
            Path đến file audio
        """
        if self.provider == "gtts":
            generated_path = self._generate_gtts_file(text, output_path)
            if generated_path is None:
                raise ValueError("gTTS is not initialized")
            return generated_path
        if self.provider == "vieneu":
            return self._run_async(self.generate_speech_file_async(text, output_path))
        raise ValueError("Only gTTS and Vieneu support file generation")

    async def generate_speech_file_async(self, text: str, output_path: Optional[str] = None) -> Optional[str]:
        """Async version for file generation, safe to call inside the main pipeline."""
        if self.provider == "gtts":
            return await asyncio.to_thread(self._generate_gtts_file, text, output_path)
        if self.provider == "vieneu":
            return await self._generate_vieneu_file(text, output_path)
        if self.provider == "pyttsx3":
            return None
        raise ValueError(f"Unsupported provider: {self.provider}")

    def _generate_gtts_file(self, text: str, output_path: Optional[str] = None) -> Optional[str]:
        if self.gTTS is None:
            print("gTTS not initialized")
            return None

        filepath = Path(output_path) if output_path else self._build_cache_path(text, ".mp3")
        filepath.parent.mkdir(parents=True, exist_ok=True)
        if not filepath.exists():
            tts = self.gTTS(text=text, lang=self.lang)
            tts.save(str(filepath))
            print(f"Generated: {filepath}")

        return str(filepath)

    async def _generate_vieneu_file(self, text: str, output_path: Optional[str] = None) -> Optional[str]:
        if self.vieneu_engine is None:
            print("Vieneu not initialized")
            return None

        filepath = Path(output_path) if output_path else self._build_cache_path(text, ".wav")
        filepath.parent.mkdir(parents=True, exist_ok=True)
        if filepath.exists():
            return str(filepath)

        audio_bytes = await self.vieneu_engine.synthesize(text)
        if not audio_bytes:
            return None

        filepath.write_bytes(audio_bytes)
        print(f"Generated: {filepath}")
        return str(filepath)

    def _build_cache_path(self, text: str, suffix: str) -> Path:
        import hashlib

        filename = f"speech_{hashlib.md5(text.encode()).hexdigest()[:8]}{suffix}"
        return self.cache_dir / filename

    def _run_async(self, coroutine) -> Optional[str]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        raise RuntimeError("Use the async TTS methods when a loop is already running.")


# Demo usage
if __name__ == '__main__':
    # Test với gTTS
    tts = TTSEngine(provider="gtts")

    test_text = "Xin chào. Đây là hộp sữa Vinamilk, giá 15 ngàn đồng, hạn sử dụng đến ngày 20 tháng 10 năm 2026"

    print("Generating speech...")
    filepath = tts.speak(test_text, play=False)
    print(f"Saved to: {filepath}")

    print("\nPlaying audio...")
    tts.speak(test_text, play=True)
