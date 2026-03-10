"""
Text-to-Speech Module - Chuyển đổi văn bản thành giọng nói
"""
import os
from typing import Optional
from pathlib import Path


class TTSEngine:
    """
    Wrapper cho Text-to-Speech engines
    """

    def __init__(self, provider: str = "gtts", lang: str = "vi"):
        self.provider = provider
        self.lang = lang
        self.cache_dir = Path("voices")
        self.cache_dir.mkdir(exist_ok=True)

        if provider == "gtts":
            self._init_gtts()
        elif provider == "pyttsx3":
            self._init_pyttsx3()

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
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _speak_gtts(self, text: str, play: bool = True) -> Optional[str]:
        """Dùng gTTS (online)"""
        if self.gTTS is None:
            print("gTTS not initialized")
            return None

        # Tạo filename từ text (hash)
        import hashlib
        filename = f"speech_{hashlib.md5(text.encode()).hexdigest()[:8]}.mp3"
        filepath = self.cache_dir / filename

        # Kiểm tra cache
        if not filepath.exists():
            tts = self.gTTS(text=text, lang=self.lang)
            tts.save(str(filepath))
            print(f"Generated: {filepath}")

        # Phát âm thanh
        if play:
            self._play_audio(filepath)

        return str(filepath)

    def _speak_pyttsx3(self, text: str, play: bool = True) -> None:
        """Dùng pyttsx3 (offline)"""
        if self.engine is None:
            print("pyttsx3 not initialized")
            return

        if play:
            self.engine.say(text)
            self.engine.runAndWait()

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

    def generate_speech_file(self, text: str, output_path: str) -> str:
        """
        Generate speech file mà không phát ngay

        Returns:
            Path đến file audio
        """
        if self.provider == "gtts":
            tts = self.gTTS(text=text, lang=self.lang)
            tts.save(output_path)
            return output_path
        else:
            raise ValueError("Only gTTS supports file generation")


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
