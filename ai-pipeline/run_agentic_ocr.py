import asyncio
import json
import logging
import os
from pathlib import Path
from typing import List

from inference_service import InferenceOptions, build_inference_service, default_inference_options

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("AgenticOCRRunner")


def _load_project_env(base_dir: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env_path = base_dir.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def _list_images(directory: Path) -> List[Path]:
    return sorted(
        path for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )


def _runner_options() -> InferenceOptions:
    defaults = default_inference_options()
    return InferenceOptions(
        use_yolo=defaults.use_yolo,
        enable_selection=defaults.enable_selection,
        enable_tts=defaults.enable_tts,
        enable_backend_sync=defaults.enable_backend_sync,
    )


async def main():
    base_dir = Path(__file__).resolve().parent
    _load_project_env(base_dir)

    sample_dir = Path(os.getenv("AGENTIC_SAMPLE_DIR", base_dir / "sample_docs"))
    cropped_dir = Path(os.getenv("AGENTIC_CROPPED_DIR", base_dir / "cropped_tags"))
    output_path = Path(os.getenv("AGENTIC_OUTPUT_JSON", base_dir / "tests" / "output.json"))

    sample_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image_files = _list_images(sample_dir)
    if not image_files:
        logger.warning("No images found in '%s'.", sample_dir)
        logger.info("Place one or more .jpg/.jpeg/.png/.webp files there, then rerun.")
        return

    logger.info("Initializing reusable inference service...")
    service = build_inference_service(base_dir=base_dir)
    options = _runner_options()
    all_results = {}

    for image_path in image_files:
        logger.info("")
        logger.info("=" * 60)
        logger.info("PROCESSING IMAGE: %s", image_path.name)
        logger.info("=" * 60)

        result = await service.infer_image(
            image_path,
            options=options,
            source_image=image_path.name,
            crop_output_dir=cropped_dir if options.use_yolo else None,
            keep_crops=options.use_yolo,
        )

        if result.get("ok"):
            selected = result.get("selected_result") or {}
            logger.info(
                "SELECTED RESULT: Item=%s, Price=%s, Crop=%s",
                selected.get("product_name") or selected.get("name"),
                selected.get("price"),
                selected.get("selected_crop_name"),
            )
        else:
            logger.error("Failed to determine a final result for %s: %s", image_path.name, result.get("message"))

        all_results[image_path.name] = {
            "source_image": result.get("source_image"),
            "selected_result": result.get("selected_result"),
            "selection": result.get("selection"),
            "all_candidates": result.get("all_candidates", []),
            "audio_path": result.get("audio_path"),
            "backend_sync": result.get("backend_sync"),
            "debug": result.get("debug"),
            "ok": result.get("ok", False),
            "message": result.get("message"),
        }

    output_path.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Saved aggregated output to %s", output_path)


if __name__ == "__main__":
    asyncio.run(main())
