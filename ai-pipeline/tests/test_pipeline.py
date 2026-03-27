import asyncio
import json
import logging
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    try:
        from ocr.kreuzberg_extractor import KreuzbergFramework, KreuzbergOCRExtractor
        from ocr.llm_extractor import build_llm_extractor
        from ocr.pipeline import PriceTagPipeline
        from tts.vieneu_tts import VieneuTTS
    except ImportError as exc:
        logging.error("Missing runtime dependency: %s", exc)
        logging.info("Install dependencies first with `pip install -r requirements.txt` and `pip install -r ocr/requirements.txt`.")
        return

    sample_dir = ROOT_DIR / "sample_docs"
    sample_dir.mkdir(parents=True, exist_ok=True)

    test_image = Path(
        os.getenv(
            "AGENTIC_TEST_IMAGE",
            sample_dir / "invoice_1.jpg",
        )
    )

    if not test_image.exists():
        logging.warning(f"File not found: {test_image}")
        logging.info("Place a sample image there or set AGENTIC_TEST_IMAGE before running.")
        return

    pipeline = PriceTagPipeline(
        KreuzbergOCRExtractor(KreuzbergFramework()),
        build_llm_extractor(),
        VieneuTTS(),
    )

    result = await pipeline.run(test_image)

    output_path = ROOT_DIR / "tests" / "output.json"
    output_path.write_text(
        json.dumps({test_image.name: result}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n===== FINAL RESULT =====")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
