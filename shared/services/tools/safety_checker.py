import json                                                                                                                                                                                                     
import re                                    
from pathlib import Path                                                                                                                                                                                        
from langchain_core.tools import tool                                            
                                                                                                                                                                                                                  
DATA_DIR = Path(__file__).parent.parent.parent / "data"                                                                                                                                                         
                                                                                                                                                                                                                  
  # Load banned pesticides once at import time                                                                                                                                                                    
with open(DATA_DIR / "banned_pesticides.json", "r") as f:                                                                                                                                                       
      BANNED_DATA = json.load(f)


def _normalize(text: str) -> str:
      return text.lower().strip()


def get_banned_chemicals_for_crop(crop: str) -> list[dict]:
      """Get all banned/restricted chemicals relevant to a specific crop."""
      crop_lower = _normalize(crop)
      results = []

      for category_key, category_data in BANNED_DATA.items():
          if not isinstance(category_data, dict) or "chemicals" not in category_data:
              continue

          for chemical in category_data["chemicals"]:
              name = chemical.get("name", "")
              aliases = chemical.get("aliases", [])
              crops_affected = [_normalize(c) for c in chemical.get("crops", [])]

              # Universally banned — applies to all crops
              if not crops_affected or category_key in ("banned", "withdrawn"):
                  results.append({
                      "chemical_name": name,
                      "aliases": aliases,
                      "category": category_key,
                      "description": category_data.get("description", ""),
                  })
              # Crop-specific restriction
              elif crop_lower in crops_affected:
                  results.append({
                      "chemical_name": name,
                      "aliases": aliases,
                      "category": category_key,
                      "description": category_data.get("description", ""),
                      "crops": chemical.get("crops", []),
                  })

      return results


def scan_text_for_banned(text: str, crop: str) -> list[dict]:
      """Scan any text for mentions of banned chemicals."""
      banned = get_banned_chemicals_for_crop(crop)
      found = []
      text_lower = _normalize(text)

      for chem in banned:
          names_to_check = [_normalize(chem["chemical_name"])] + [_normalize(a) for a in chem.get("aliases", [])]
          for name in names_to_check:
              if re.search(re.escape(name), text_lower):
                  found.append(chem)
                  break

      return found


@tool
def safety_checker(crop_name: str, text_to_scan: str = "") -> dict:
      """Check banned/restricted pesticides for a crop. Optionally scan text for banned chemicals."""
      banned = get_banned_chemicals_for_crop(crop_name)
      scanned = scan_text_for_banned(text_to_scan, crop_name) if text_to_scan else []
      return {
          "banned_for_crop": banned,
          "found_in_text": scanned,
          "total_banned": len(banned),
          "total_found_in_text": len(scanned),
      }
