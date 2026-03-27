import asyncio
import logging
from pathlib import Path

try:
    from .kreuzberg_extractor import KreuzbergFramework, KreuzbergOCRExtractor
    from .llm_extractor import build_llm_extractor
    from .pipeline import PriceTagPipeline
except ImportError:
    from kreuzberg_extractor import KreuzbergFramework, KreuzbergOCRExtractor
    from llm_extractor import build_llm_extractor
    from pipeline import PriceTagPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    sample_dir = Path("sample_docs")
    sample_dir.mkdir(exist_ok=True)
    test_file = sample_dir / "invoice_1.jpg"

    if not test_file.exists():
        logging.warning(f"File not found: {test_file}")
        logging.info(f"Place a price tag image in '{sample_dir}' as '{test_file.name}' to run.")
        return

    ocr = KreuzbergOCRExtractor(framework=KreuzbergFramework(backend="paddleocr", language="vi"))
    llm = build_llm_extractor()
    pipeline = PriceTagPipeline(ocr=ocr, llm=llm)

    result = await pipeline.run(test_file)
    
    if result:
        logging.info(f"Main received final data: Item={result.get('name')}, Price={result.get('price')}")


if __name__ == "__main__":
    asyncio.run(main())
