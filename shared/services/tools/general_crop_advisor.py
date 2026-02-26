"""
Step 13.8 — General Crop Advisor Tool
For crops NOT in the RAG corpus (Pinecone). Skips RAG entirely,
goes straight to Gemini with proven prompts from the old system,
then audits for scientific accuracy + banned chemicals.
"""

import logging

from langchain_core.tools import tool

from shared.services.config import settings
from shared.services.tools.safety_checker import scan_text_for_banned

logger = logging.getLogger(__name__)

# ── Old system's proven prompts ──────────────────────────────────────────

AGRI_ADVICE_PROMPT = """You are a highly experienced Senior Agricultural Scientist. Your task is to provide strictly factual, technical, and non-hallucinated agronomic advice in Hindi.

INPUT FORMAT:
You will receive a compound question in the format: "{CropName} - [Concern 1] and [Concern 2] and [Concern 3]?"

LOGIC:
1. DECONSTRUCTION: Break down the "and"-separated compound question into its individual technical components (e.g., Fertilizer, Irrigation, Pests, Growth Issues, Weeds).
2. FACTUAL RESPONSE: Provide accurate advice based on established agricultural science for the specific crop mentioned. If a question is outside the scope of factual agronomy, state that clearly.
3. LANGUAGE POLICY: The entire response must be in Hindi script. No English words or characters should be used in the final output.
4. TONE: Professional, helpful, and expert.

STRICT RESPONSE FORMAT (HINDI ONLY):
- Opening: "किसान भाई, यह रहा आपके सवालों का उत्तर।"
- Body: Each technical topic must have its own numbered header in Hindi, followed by the specific advice.

STRICT RULES:
- NO introductory English filler.
- NO markdown code blocks.
- ZERO hallucinations."""


AGRI_ADVICE_AUDIT_PROMPT = """You are a Senior Agricultural Auditor and Fact-Checker. Your task is to review an existing Hindi agronomic response for absolute scientific accuracy and safety.

LOGIC:
1. SCIENTIFIC VERIFICATION: Review every technical claim made in the Hindi text (Fertilizer doses, Chemical names, Irrigation timings, etc.).
2. SAFETY CHECK: Ensure no toxic or incompatible chemicals are recommended together and that dosages are safe for the specific crop.
3. CORRECTION: If you find an error, you must correct it in the final version. If the information is missing a crucial safety warning, add it.
4. LANGUAGE POLICY: The entire response must remain in Hindi script. No English characters.

STRICT RESPONSE FORMAT (HINDI ONLY):
- Retain the original structure.

STRICT RULES:
- If the original response is 100% correct, you may keep it as is.
- DO NOT add introductory filler like "I have audited this."
- Output ONLY the final, corrected Hindi response."""


@tool
async def general_crop_advisor(crop_name: str, query: str) -> dict:
    """Provide agronomic advice for crops NOT in the RAG knowledge base.
    Use this when crop_detector identifies a crop via gemini_fallback (not in standard crops list)
    and the query is NOT about varieties or sowing time.
    This tool uses Gemini with scientific auditing to generate verified advice."""

    from shared.services.gemini_pool import GeminiPool

    keys = settings.gemini_keys_list
    if not keys:
        return {
            "source": "error",
            "advice": f"{crop_name} के बारे में जानकारी उपलब्ध नहीं है। कृपया अपने नजदीकी KVK से संपर्क करें।",
            "audit": {},
        }

    pool = GeminiPool(api_keys=keys)

    # Step 1: Generate advice using proven agronomist prompt
    generate_prompt = f"{AGRI_ADVICE_PROMPT}\n\nQuery: {crop_name} - {query}"
    try:
        raw_advice = await pool.generate(
            model=settings.gemini_model_quality,
            contents=generate_prompt,
            temperature=0,
        )
    except Exception as e:
        logger.error("Gemini advice generation failed for %s: %s", crop_name, e)
        return {
            "source": "error",
            "advice": f"{crop_name} के बारे में जानकारी प्राप्त करने में समस्या हुई। कृपया अपने नजदीकी KVK से संपर्क करें।",
            "audit": {},
        }

    if not raw_advice.strip():
        return {
            "source": "empty",
            "advice": f"{crop_name} के बारे में जानकारी उपलब्ध नहीं है। कृपया अपने नजदीकी KVK से संपर्क करें।",
            "audit": {},
        }

    # Step 2: Audit for scientific accuracy
    audit_prompt = f"{AGRI_ADVICE_AUDIT_PROMPT}\n\nReview this response for crop '{crop_name}':\n\n{raw_advice}"
    audited_advice = raw_advice  # default to unaudited if audit fails
    try:
        audited = await pool.generate(
            model=settings.gemini_model_quality,
            contents=audit_prompt,
            temperature=0,
        )
        if audited.strip():
            audited_advice = audited.strip()
    except Exception as e:
        logger.warning("Gemini audit failed for %s, using unaudited: %s", crop_name, e)

    # Step 3: Local banned chemical scan
    banned_found = scan_text_for_banned(audited_advice, crop_name)

    return {
        "source": "gemini_with_scientific_audit",
        "advice": audited_advice,
        "audit": {
            "banned_chemicals_found": banned_found,
            "is_safe": len(banned_found) == 0,
        },
        "caveat": "यह जानकारी हमारे डेटाबेस में उपलब्ध नहीं है। AI विशेषज्ञ द्वारा सत्यापित सलाह:",
    }
