"""
Step 13.6 — Variety Advisor Tool
Provides crop variety and sowing time information.
Path 1: JSON lookup (1,052 pre-verified records) → instant, no API call.
Path 2: Gemini fetch + audit fallback for crops not in JSON.
"""

import json
import logging
from pathlib import Path

from langchain_core.tools import tool

from shared.services.config import settings

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"

# ── Load varieties JSON once at import ────────────────────────────────────
_varieties_cache: dict | None = None


def _get_varieties_data() -> list[dict]:
    global _varieties_cache
    if _varieties_cache is None:
        path = DATA_DIR / "varieties_and_sowing_time.json"
        with open(path, "r", encoding="utf-8") as f:
            _varieties_cache = json.load(f)
    return _varieties_cache.get("records", [])


def _lookup_varieties(crop_name: str) -> list[dict]:
    """Find all variety records matching the crop name (case-insensitive)."""
    records = _get_varieties_data()
    crop_lower = crop_name.lower().strip()
    return [
        r for r in records
        if (r.get("Crop") or "").lower() == crop_lower
    ]


def _format_varieties(crop_name: str, records: list[dict]) -> str:
    """Format variety records into a readable string for the agent."""
    lines = [f"{crop_name} की किस्में और बुवाई का समय:"]
    for record in records:
        variety = record.get("Variety") or "N/A"
        sowing_time = record.get("Sowing_Time") or record.get("Sowing Time") or "N/A"
        description = record.get("description") or record.get("Description") or ""
        lines.append(f"- {variety} — {sowing_time}")
        if description:
            lines.append(description)
    return "\n".join(lines)


# ── Gemini fallback prompts (from old system) ────────────────────────────

VARIETIES_FETCH_PROMPT = """You are a Senior Agronomist and Citrus Specialist specialized in Haryana Agricultural University (HAU) recommendations.

TASK: Provide an exhaustive list of distinct varieties suited for Haryana in a specific WhatsApp-optimized format.

STEP-BY-STEP LOGIC:

GRANULAR SELECTION: Identify specific selections, clonal strains, or improved hybrids recommended for the North Indian plains (HAU Hisar, ICAR-NRCC, or PAU Ludhiana).

WHATSAPP CARD STRUCTURE: The "description" field for each variety MUST follow this exact visual structure: 🌱 [Catchy Hindi Title for the Variety] 💰

पैदावार: [Specific Yield Data] बुवाई: [Month/Window] 🗓️

[Feature 1 Keyword] [Short Detail]

[Feature 2 Keyword] [Short Detail]

[Feature 3 Keyword] [Short Detail]

💡 प्रो-टिप: [One actionable advice for the farmer] 🗓️

STRICT JSON OUTPUT FORMAT: { "crop_name": "[Input Crop]", "varieties": [ { "variety_name": "[Full Technical Name]", "sowing_time": "[Specific Months]", "description": "[The WhatsApp Card structure defined above in Hindi]" } ] }

STRICT RULES:

PROVIDE MULTIPLE DISTINCT ENTRIES.

Use bold for keywords within the description.

Use Emojis (🌱, 💰, 🗓️, 💡) exactly as shown.

DO NOT return markdown blocks (NO ```json).

THE RESPONSE MUST START WITH { AND END WITH }.

Focus on heat tolerance, frost resistance, and Haryana climatic conditions."""


VARIETIES_AUDIT_PROMPT = """You are a Senior Agricultural Scientist at Haryana Agricultural University (HAU) Hisar.
Your task is to audit and fact-check a JSON object containing crop varieties and sowing times.

TASK:
1. VALIDATE: Check if each variety name actually exists and is recommended for Haryana.
2. REMOVE HALLUCINATIONS: If a variety is made up or purely tropical, remove it.
3. CORRECT SOWING TIMES: Ensure the 'sowing_time' aligns with Haryana's Rabi/Kharif seasons.
4. REWRITE DESCRIPTIONS: Refine Hindi terminology. Bold **पैदावार**, **बीमारी**, and **मौसम**.

STRICT OUTPUT RULES:
- Return ONLY the corrected JSON object.
- NO markdown blocks (NO ```json).
- NO conversational filler."""


async def _fetch_varieties_from_gemini(crop_name: str) -> str | None:
    """Fallback: fetch varieties from Gemini and audit them."""
    from shared.services.gemini_pool import GeminiPool

    keys = settings.gemini_keys_list
    if not keys:
        return None

    pool = GeminiPool(api_keys=keys)

    # Step 1: Fetch varieties
    fetch_prompt = f"{VARIETIES_FETCH_PROMPT}\n\nCrop: {crop_name}"
    try:
        raw = await pool.generate(
            model=settings.gemini_model_quality,
            contents=fetch_prompt,
            temperature=0,
        )
    except Exception as e:
        logger.error("Gemini varieties fetch failed for %s: %s", crop_name, e)
        return None

    # Parse JSON
    json_text = raw.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Gemini varieties JSON for %s", crop_name)
        return None

    # Step 2: Audit
    audit_input = json.dumps(parsed, ensure_ascii=False)
    audit_prompt = f"{VARIETIES_AUDIT_PROMPT}\n\nJSON:\n{audit_input}"
    try:
        audited_raw = await pool.generate(
            model=settings.gemini_model_quality,
            contents=audit_prompt,
            temperature=0,
        )
        audited_text = audited_raw.replace("```json", "").replace("```", "").strip()
        audited = json.loads(audited_text)
        parsed = audited
    except Exception as e:
        logger.warning("Gemini varieties audit failed for %s, using unaudited: %s", crop_name, e)

    # Format the result
    varieties = parsed.get("varieties", [])
    if not varieties:
        return None

    crop_label = parsed.get("crop_name", crop_name)
    lines = [f"{crop_label} की किस्में और बुवाई का समय:"]
    for entry in varieties:
        variety_name = entry.get("variety_name") or "N/A"
        sowing_time = entry.get("sowing_time") or "N/A"
        description = entry.get("description") or ""
        lines.append(f"- {variety_name} — {sowing_time}")
        if description:
            lines.append(description)

    return "\n".join(lines) if len(lines) > 1 else None


# ── LangGraph Tool ────────────────────────────────────────────────────────

@tool
async def variety_advisor(crop_name: str) -> dict:
    """Get recommended crop varieties and sowing times for a specific crop in Haryana.
    Use this when the farmer asks about varieties (kisme/किस्में) or sowing time (buvai/बुवाई ka samay)."""

    # Path 1: JSON lookup
    records = _lookup_varieties(crop_name)
    if records:
        return {
            "source": "verified_database",
            "crop": crop_name,
            "count": len(records),
            "data": _format_varieties(crop_name, records),
        }

    # Path 2: Gemini fallback
    logger.info("Crop '%s' not in varieties JSON, falling back to Gemini", crop_name)
    gemini_result = await _fetch_varieties_from_gemini(crop_name)

    if gemini_result:
        return {
            "source": "gemini_generated_and_audited",
            "crop": crop_name,
            "data": gemini_result,
            "caveat": "यह जानकारी AI द्वारा उत्पन्न है। सटीक जानकारी के लिए अपने नजदीकी KVK से संपर्क करें।",
        }

    # Both failed
    return {
        "source": "not_found",
        "crop": crop_name,
        "data": f"{crop_name} की किस्मों की जानकारी उपलब्ध नहीं है। कृपया अपने नजदीकी KVK या HAU हिसार से संपर्क करें।",
    }
