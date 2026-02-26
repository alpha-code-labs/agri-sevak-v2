"""
Step 4.3 — Full Auditor Post-Processing (upgraded from old system)
After the agent produces a final answer, run:
1. Local JSON scan for banned chemicals (fast, free)
2. Full scientific auditor: verifies accuracy of generated parts,
   removes banned chemicals, formats for WhatsApp.
Returns the cleaned, audited, WhatsApp-formatted response.
"""

import logging
from shared.services.config import settings
from shared.services.gemini_pool import GeminiPool
from shared.services.tools.safety_checker import (
    get_banned_chemicals_for_crop,
    scan_text_for_banned,
)

logger = logging.getLogger(__name__)


def _build_safety_instruction(crop_name: str) -> str:
    """Generate crop-specific banned chemical block for the auditor prompt."""
    banned = get_banned_chemicals_for_crop(crop_name)
    if not banned:
        return ""

    fully_banned = [b for b in banned if b["category"] in ("banned", "refused", "withdrawn")]
    restricted = [b for b in banned if b["category"] == "restricted"]

    lines = [
        f"\n\nCRITICAL SAFETY RULE — BANNED PESTICIDES FOR {crop_name.upper()}:",
        "The following chemicals are BANNED by CIB&RC India. If ANY of these appear in the response, "
        "you MUST remove that recommendation entirely and suggest a safe, registered alternative.",
        "",
    ]

    if restricted:
        lines.append(f"BANNED SPECIFICALLY FOR {crop_name.upper()}:")
        for b in restricted:
            name = b["chemical_name"]
            aliases = b.get("aliases", [])
            alias_str = f" (also: {', '.join(aliases)})" if aliases else ""
            lines.append(f"  - {name}{alias_str}")
        lines.append("")

    if fully_banned:
        lines.append(
            f"Additionally, {len(fully_banned)} chemicals are completely banned in India "
            f"(including Endosulfan, Methyl Parathion, Phorate, Dichlorovos, Carbaryl, etc.). "
            f"Do not recommend any of these."
        )
        lines.append("")

    lines.append(
        "If you remove a banned chemical, restructure the answer to maintain completeness — "
        "suggest an alternative treatment or direct the farmer to consult HAU/KVK experts."
    )

    return "\n".join(lines)


AUDITOR_PROMPT = """You are a Senior Agricultural Auditor and UX Designer.
Your goal is to verify technical accuracy and output a scannable WhatsApp message.

LOGIC:
1. DETECT & AUDIT: Examine the response carefully.
   - If you see 'भाग अ' (verified data) and 'भाग ब' (expert-generated), focus your audit on 'भाग ब'.
   - Verify all technical data: Fertilizer doses, Chemical names, Irrigation timings, etc.
   - Ensure dosages are safe and chemicals are HAU-standard for the crop.
   - Correct any errors directly in the final output.

2. CLEANING & REPLACING (CRITICAL):
   - DELETE labels like "भाग अ", "भाग ब", "[सवाल]", and "[विस्तृत उत्तर]".
   - Do NOT use brackets [] in the final response.

3. WHATSAPP UI FORMATTING:
   - Start with: "किसान भाई, आपके सवालों का सटीक समाधान यहाँ है:"
   - For every question, use: ❓ *[Question Text Here]*
   - For every answer, use: ✅ [Answer Text Here]
   - For chemicals, use: 🧪 *[Chemical Name]*: *[Dosage]*
   - For irrigation stages, use: 💧 *[Stage Name]*: [Details]

4. STRUCTURE:
   - Use double line breaks between different topics.
   - Keep sentences short. Use bolding for emphasis on numbers and chemicals.
   - Keep total response under 1500 characters (WhatsApp readability).
   - Entire response MUST be in Hindi (Devanagari script).

5. OUTPUT:
   - Output ONLY the final audited and formatted response.
   - DO NOT add introductory filler like "I have audited this."
{safety_block}

TEXT TO AUDIT:
---
{agent_response}
---"""


async def safety_audit(
    agent_response: str,
    crop_name: str,
    district: str = "",
) -> dict:
    """
    Run full audit on the agent's response:
    1. Local banned chemical scan
    2. Scientific accuracy verification
    3. Banned chemical removal with alternatives
    4. WhatsApp formatting
    Returns: {
        "audited_response": str,
        "local_scan": list[dict],
        "is_safe_before_audit": bool,
        "audit_applied": bool,
    }
    """
    # Layer 1: Local JSON scan (instant, free)
    local_banned = scan_text_for_banned(agent_response, crop_name)
    is_safe_before = len(local_banned) == 0

    if local_banned:
        logger.warning(
            "Local scan found %d banned chemicals in agent response for crop=%s: %s",
            len(local_banned),
            crop_name,
            [c["chemical_name"] for c in local_banned],
        )

    # Layer 2: Full Gemini auditor (scientific accuracy + safety + formatting)
    keys = settings.gemini_keys_list
    if not keys:
        logger.warning("No Gemini keys — skipping auditor pass")
        return {
            "audited_response": agent_response,
            "local_scan": local_banned,
            "is_safe_before_audit": is_safe_before,
            "audit_applied": False,
        }

    pool = GeminiPool(api_keys=keys)
    safety_block = _build_safety_instruction(crop_name) if crop_name else ""

    prompt = AUDITOR_PROMPT.format(
        safety_block=safety_block,
        agent_response=agent_response,
    )

    try:
        audited = await pool.generate(
            model=settings.gemini_model_fast,
            contents=prompt,
            temperature=0,
        )
    except Exception as e:
        logger.error("Gemini auditor failed: %s", e)
        return {
            "audited_response": agent_response,
            "local_scan": local_banned,
            "is_safe_before_audit": is_safe_before,
            "audit_applied": False,
        }

    # Layer 3: Re-scan the audited response (verify the auditor didn't introduce banned chemicals)
    post_audit_banned = scan_text_for_banned(audited, crop_name)
    if post_audit_banned:
        logger.error(
            "Auditor INTRODUCED banned chemicals! crop=%s chemicals=%s",
            crop_name,
            [c["chemical_name"] for c in post_audit_banned],
        )

    return {
        "audited_response": audited,
        "local_scan": local_banned,
        "post_audit_scan": post_audit_banned,
        "is_safe_before_audit": is_safe_before,
        "audit_applied": True,
    }
