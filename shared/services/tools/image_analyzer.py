"""                                          
  Step 3.7 — Image Analyzer Tool                                                                                                                                                                                                                                             
  Download image from Azure Blob → send to Gemini multimodal → return diagnosis.                                                                                                                                                                               
  """                                                                                                                                                                                                                                                                        
                                                                                   
import logging                                                                                                                                                                                                                                                             
from langchain_core.tools import tool                                            

from shared.services.config import settings
from shared.services.blob_storage import BlobStorage
from shared.services.gemini_pool import GeminiPool
from shared.services.tools.safety_checker import scan_text_for_banned

logger = logging.getLogger(__name__)

AGRONOMIST_PROMPT = (
      "You are a Senior Agronomist at Haryana Agricultural University (HAU, Hisar).\n"
      "A farmer has sent you this photo of their crop.\n\n"
      "Analyze the image and provide:\n"
      "1. What crop is shown\n"
      "2. What disease, pest, or deficiency you can identify (if any)\n"
      "3. Severity (mild / moderate / severe)\n"
      "4. Recommended treatment with specific product names and dosages\n"
      "5. Preventive measures for the future\n\n"
      "Respond in Hindi. Be specific and actionable. "
      "If the image is unclear or not a crop photo, say so clearly."
  )


@tool
async def image_analyzer(blob_name: str, crop_name: str = "") -> dict:
      """Analyze a crop disease image. Downloads from Azure Blob, sends to Gemini multimodal for diagnosis."""

      # 1. Download image from Azure Blob
      try:
          blob = BlobStorage()
          image_bytes = await blob.download(blob_name)
      except Exception as e:
          logger.error(f"Failed to download image {blob_name}: {e}")
          return {"error": f"Image download failed: {e}", "diagnosis": "", "safety": {}}

      # 2. Build prompt (include crop name if known)
      prompt = AGRONOMIST_PROMPT
      if crop_name:
          prompt += f"\n\nThe farmer mentioned the crop is: {crop_name}"

      # 3. Send to Gemini multimodal
      try:
          pool = GeminiPool(api_keys=settings.gemini_keys_list)
          diagnosis = await pool.generate_multimodal(
              model=settings.gemini_model_quality,
              image_bytes=image_bytes,
              text_prompt=prompt,
          )
      except Exception as e:
          logger.error(f"Gemini multimodal failed: {e}")
          return {"error": f"Image analysis failed: {e}", "diagnosis": "", "safety": {}}

      # 4. Safety scan the diagnosis for banned chemicals
      scan_crop = crop_name if crop_name else "general"
      banned_found = scan_text_for_banned(diagnosis, scan_crop)

      return {
          "diagnosis": diagnosis,
          "safety": {
              "banned_chemicals_found": banned_found,
              "is_safe": len(banned_found) == 0,
          },
      }