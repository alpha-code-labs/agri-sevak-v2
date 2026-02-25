import json                                                                                                                                                                                                                                                                
from pathlib import Path                                                                   
from rapidfuzz import fuzz, process                                                                                                                                                                                                                                        
from langchain_core.tools import tool                                                                                                                                                                                                                                    
from shared.services.crop_classifier import CropClassifier                                                                                                                                                                                                                 
from shared.services.config import settings                                                                                                                                                                                                                              
                                                                                                                                                                                                                                                                             
DATA_DIR = Path(__file__).parent.parent.parent / "data"                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                                             
  # Load crops.json for fuzzy matching                                                                                                                                                                                                                                       
with open(DATA_DIR / "crops.json", "r") as f:                                                                                                                                                                                                                              
      CROPS_DATA = json.load(f)["crops"]

  # Build synonym lookup for fuzzy matching
SYNONYM_TO_MASTER = {}
for crop in CROPS_DATA:
      master = crop["master_name"]
      for syn in crop["synonyms"]:
          SYNONYM_TO_MASTER[syn["en"].lower()] = master
          SYNONYM_TO_MASTER[syn["hi"]] = master

ALL_SYNONYMS = list(SYNONYM_TO_MASTER.keys())

  # Load classifier (lazy — initialized on first use)
_classifier = None


def _get_classifier() -> CropClassifier:
      global _classifier
      if _classifier is None:
          _classifier = CropClassifier(settings.crop_classifier_model_path)
      return _classifier


def fuzzy_detect(text: str, threshold: int = 70) -> dict | None:
      """Layer 2: RapidFuzz fuzzy matching against all synonyms."""
      text_lower = text.lower().strip()

      # Exact match first
      if text_lower in SYNONYM_TO_MASTER:
          return {"crop_name": SYNONYM_TO_MASTER[text_lower], "source": "exact", "confidence": 1.0}

      # Fuzzy match
      result = process.extractOne(text_lower, ALL_SYNONYMS, scorer=fuzz.token_sort_ratio)
      if result and result[1] >= threshold:
          matched_synonym = result[0]
          return {
              "crop_name": SYNONYM_TO_MASTER[matched_synonym],
              "source": "fuzzy",
              "confidence": round(result[1] / 100, 4),
              "matched": matched_synonym,
          }

      return None


@tool
async def crop_detector(farmer_input: str) -> dict:
      """Detect which crop the farmer is asking about from their input text."""

      # Layer 1: PyTorch classifier
      classifier = _get_classifier()
      predictions = classifier.predict(farmer_input, top_k=3)

      if predictions[0]["confidence"] >= 0.5:
          return {
              "crop_name": predictions[0]["crop"],
              "source": "classifier",
              "confidence": predictions[0]["confidence"],
              "top_3": predictions,
          }

      # Layer 2: RapidFuzz fuzzy matching
      fuzzy_result = fuzzy_detect(farmer_input)
      if fuzzy_result:
          return {
              "crop_name": fuzzy_result["crop_name"],
              "source": fuzzy_result["source"],
              "confidence": fuzzy_result["confidence"],
              "top_3": predictions,
          }

      # Layer 3: Gemini fallback
      from shared.services.gemini_pool import GeminiPool

      keys = settings.gemini_keys_list
      if keys:
          pool = GeminiPool(api_keys=keys)
          prompt = (
              f"A farmer said: \"{farmer_input}\"\n"
              f"Which crop is the farmer talking about?\n"
              f"Reply with ONLY the crop name in English. If no crop is mentioned, reply with: NONE"
          )
          try:
              response = await pool.generate(model=settings.gemini_model_fast, contents=prompt)
              crop_name = response.strip().strip('"').strip("'")

              if crop_name.upper() == "NONE":
                  return {
                      "crop_name": None,
                      "source": "gemini_none",
                      "confidence": 0.0,
                      "top_3": predictions,
                  }

              return {
                  "crop_name": crop_name,
                  "source": "gemini_fallback",
                  "confidence": 0.6,
                  "top_3": predictions,
              }
          except Exception:
              pass

      # Everything failed
      return {
          "crop_name": None,
          "source": "none",
          "confidence": 0.0,
          "top_3": predictions,
      }
