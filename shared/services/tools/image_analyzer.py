"""
Step 3.7 — Image Analyzer Tool
Download image from Azure Blob → send to Gemini multimodal → return visual observations.
The tool only describes what it sees (symptoms, visual signs). Diagnosis and treatment
are handled downstream by the agent via rag_retriever.
"""

import logging
from langchain_core.tools import tool

from shared.services.config import settings
from shared.services.blob_storage import BlobStorage
from shared.services.gemini_pool import GeminiPool

logger = logging.getLogger(__name__)

OBSERVER_PROMPT = (
    "You are a trained agricultural field observer.\n"
    "A farmer has sent you this photo. Your job is ONLY to describe what you see.\n\n"
    "Provide:\n"
    "1. CROP: What crop/plant/fruit is visible (if identifiable)\n"
    "2. PLANT PART: Which part is affected — leaf, fruit, stem, root, flower\n"
    "3. VISUAL SYMPTOMS: Describe exactly what you see — color, shape, texture, pattern of marks/spots/lesions. "
    "Be precise (e.g., 'dark brown rough corky patches on fruit surface' NOT 'disease spots').\n"
    "4. SPREAD: Localized to a few spots, scattered, or widespread across the visible area\n"
    "5. SEVERITY: mild / moderate / severe based on how much of the plant/fruit is affected\n\n"
    "STRICT RULES:\n"
    "- Do NOT diagnose or name any disease, pest, or deficiency.\n"
    "- Do NOT suggest any treatment, chemical, or remedy.\n"
    "- ONLY describe the visual symptoms you observe.\n"
    "- Respond in English for technical accuracy.\n"
    "- If the image is unclear or not a crop/plant photo, say so clearly."
)


@tool
async def image_analyzer(blob_name: str, crop_name: str = "") -> dict:
    """Analyze a crop photo. Downloads from Azure Blob, sends to Gemini multimodal to describe visual symptoms. Does NOT diagnose — returns observations only."""

    # 1. Download image from Azure Blob
    try:
        blob = BlobStorage()
        image_bytes = await blob.download(blob_name)
    except Exception as e:
        logger.error(f"Failed to download image {blob_name}: {e}")
        return {"error": f"Image download failed: {e}", "observations": ""}

    # 2. Build prompt (include crop name if known for context)
    prompt = OBSERVER_PROMPT
    if crop_name:
        prompt += (
            f"\n\nNote: The farmer mentioned '{crop_name}' in their text message. "
            f"However, you MUST identify the crop in this image INDEPENDENTLY based on what you see. "
            f"If the image shows a different crop than '{crop_name}', clearly state what crop the image actually shows."
        )

    # 3. Send to Gemini multimodal
    try:
        pool = GeminiPool(api_keys=settings.gemini_keys_list)
        observations = await pool.generate_multimodal(
            model=settings.gemini_model_quality,
            image_bytes=image_bytes,
            text_prompt=prompt,
        )
    except Exception as e:
        logger.error(f"Gemini multimodal failed: {e}")
        return {"error": f"Image analysis failed: {e}", "observations": ""}

    return {"observations": observations}
