# Text-to-Speech (TTS) Module

Module chuyển đổi văn bản thành giọng nói tiếng Việt cho người khiếm thị.

## Nhiệm vụ

1. Nhận text từ backend (kết quả sau khi xử lý YOLO + OCR + LLM)
2. Chuyển đổi thành audio (speech)
3. Phát ra loa/tai nghe hoặc gửi về Micro:bit

## Cấu trúc folder

```
tts/
├── tts_engine.py         # TTS wrapper (gTTS, pyttsx3, Vieneu)
├── vieneu_tts.py         # Async adapter cho Vieneu Vietnamese TTS
├── voices/               # Audio cache
├── requirements.txt
└── Dockerfile
```

## Các approach

### Option 1: gTTS (Google Text-to-Speech) - Online

```python
from gtts import gTTS

tts = gTTS("Xin chào, đây là hộp sữa", lang='vi')
tts.save("output.mp3")
```

**Ưu điểm:**
- Giọng tiếng Việt tự nhiên
- Dễ sử dụng

**Nhược điểm:**
- Cần internet

### Option 2: pyttsx3 - Offline

```python
import pyttsx3

engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Tốc độ nói
engine.say("Xin chào, đây là hộp sữa")
engine.runAndWait()
```

**Ưu điểm:**
- Offline, không cần internet
- Nhanh

**Nhược điểm:**
- Giọng ít tự nhiên hơn
- Không có giọng tiếng Việt tốt

### Option 3: Vbee TTS (Vietnamese) - API

- Giọng tiếng Việt rất tự nhiên
- Có nhiều giọng nam/nữ khác nhau
- Cần API key (có free tier)

### Option 4: Vieneu - Local Vietnamese TTS

- Provider mới đã được ghép vào `TTSEngine` với key `vieneu`
- Sinh file `.wav` cục bộ và phù hợp hơn với flow OCR -> LLM -> TTS trong repo
- Dockerfile của `ai-pipeline` đã cài dependency cần thiết cho provider này

## API Interface

```python
# Input: Text message
{
    "text": "Đây là hộp sữa Vinamilk, giá 15 ngàn đồng, hạn sử dụng đến ngày 20 tháng 10 năm 2026",
    "lang": "vi",
    "speed": 1.0
}

# Output: Audio file hoặc stream
- File: output.mp3
- Hoặc stream qua WebSocket
```

## Integration với Micro:bit

Khi không dùng tai nghe Bluetooth, có thể gửi tín hiệu xuống Micro:bit:
- Hiển thị biểu tượng trên LED matrix
- Phát beep sound từ buzzer (nếu có)

## Thành viên phụ trách

- **Bạn (UI/Dashboard)**: Setup ban đầu
- Sau này có thể giao cho thành viên khác maintain

## Dependencies

```bash
# gTTS (online)
pip install gtts

# pyttsx3 (offline)
pip install pyttsx3

# Hoặc Vbee TTS (API)
pip install requests

# Vieneu (local provider)
pip install vieneu --extra-index-url https://pnnbao97.github.io/llama-cpp-python-v0.3.16/cpu/
```
