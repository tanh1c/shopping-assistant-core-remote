# LLM Extraction Module

Module dùng LLM/LayoutLM để extract thông tin có cấu trúc từ raw OCR text.

## Nhiệm vụ

1. Nhận raw text từ OCR module
2. Dùng LLM để extract và normalize thông tin:
   - Product name (tên sản phẩm)
   - Price (giá tiền)
   - Expiry date (hạn sử dụng)
   - Ingredients (thành phần)
3. Output JSON structured data cho backend

## Cấu trúc folder

```
llm/
├── extractor.py          # LLM extraction logic
├── prompt_templates.py   # Prompt templates cho các tác vụ
├── layoutlm/             # LayoutLM model (optional)
│   └── inference.py
├── requirements.txt
└── Dockerfile
```

## API Interface

```python
# Input: Raw OCR text + detected object name
{
    "ocr_text": "Sữa tươi Vinamilk 180ml\n15,000đ\nHSD: 20/12/2026",
    "detected_object": "sữa",
    "image_crop": base64_image
}

# Output: Structured JSON
{
    "product_name": "Sữa tươi Vinamilk 180ml",
    "price": 15000,
    "currency": "VND",
    "expiry_date": "2026-12-20",
    "category": "dairy",
    "confidence": 0.92
}
```

## Các approach

### Option 1: Prompt Engineering với LLM API (Gemini/GPT/Qwen-compatible)

```python
from google import genai

client = genai.Client(api_key="...")
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=f"""
    Extract structured information from this OCR text.
    Return JSON format with fields: product_name, price, expiry_date, category.

    OCR Text: {ocr_text}
    """
)
```

### Option 2: LayoutLM (Microsoft)

- Pretrained model cho document understanding
- Tốt cho việc hiểu layout của văn bản trên bao bì
- Cần fine-tune trên dataset tiếng Việt

## Thành viên phụ trách

- **QHieu**: LLM integration & prompt engineering
- **NNam**: LayoutLM fine-tuning & OCR post-processing

## Dependencies

```bash
# LLM API
pip install google-generativeai openai

# LayoutLM (optional)
pip install transformers paddlepaddle
```

## Alibaba DashScope Option

- Default provider mới của monorepo là `alibaba`
- OpenAI-compatible base URL:
  `https://coding-intl.dashscope.aliyuncs.com/v1`
- Anthropic-compatible URL được lưu sẵn trong env cho các luồng khác:
  `https://coding-intl.dashscope.aliyuncs.com/apps/anthropic`
- Các model visual có thể cấu hình qua `LLM_MODEL`:
  `qwen3.5-plus`, `kimi-k2.5`
