"""                                                                                                                                                                                                                                                                        
  Step 4.3 — Safety Audit Post-Processing                                                                                                                                                                                                                                    
  After the agent produces a final answer, run:                                                                                                                                                                                                                              
  1. Local JSON scan for banned chemicals (fast, free)                                                                                                                                                                                                                       
  2. Gemini auditor pass with crop-specific banned chemical list injected                                                                                                                                                                                                    
  Returns the cleaned, audited response.                                                                                                                                                                                                                                     
  """                                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                                             
import logging
from shared.services.config import settings
from shared.services.gemini_pool import GeminiPool
from shared.services.tools.safety_checker import (
      get_banned_chemicals_for_crop,
      scan_text_for_banned,
  )

logger = logging.getLogger(__name__)


def _build_banned_list_text(crop_name: str) -> str:
      """Build a readable list of banned chemicals for this crop to inject into the auditor prompt."""
      banned = get_banned_chemicals_for_crop(crop_name)
      if not banned:
          return "No specific banned chemicals found for this crop."

      lines = []
      for chem in banned:
          name = chem["chemical_name"]
          aliases = chem.get("aliases", [])
          category = chem.get("category", "")
          alias_str = f" (also known as: {', '.join(aliases)})" if aliases else ""
          lines.append(f"- {name}{alias_str} [{category}]")

      return "\n".join(lines)


AUDITOR_PROMPT = """You are a Senior Agricultural Auditor and WhatsApp UX Designer.
  Your task is to audit a response given to a farmer growing {crop_name} in {district} district, Haryana.

  STEP 1 — SAFETY AUDIT:
  The following chemicals are BANNED/RESTRICTED by CIB&RC India for this crop:
  {banned_list}

  Check the response below. If ANY banned chemical is recommended:
  - REMOVE it completely
  - REPLACE with a safe, registered alternative for the same problem
  - If no alternative is known, write: "अपने नजदीकी KVK से संपर्क करें"
  - NEVER mention the banned chemical by name in the response. Do not write its name even to say "don't use it" or "avoid it". Simply recommend the safe alternative directly.

  STEP 2 — WHATSAPP FORMATTING:
  - Start with: "किसान भाई, आपके सवालों का सटीक समाधान यहाँ है:"
  - Use *bold* for section titles (NOT # or ##)
  - For chemicals, use: *[Chemical Name]*: *[Dosage]*
  - Keep sentences short. Use bullet points for dosages and steps.
  - Use double line breaks between different topics.
  - Keep total response under 1500 characters.
  - Entire response MUST be in Hindi (Devanagari script).

  STEP 3 — OUTPUT:
  Output ONLY the final audited and formatted response. No preamble, no "I have audited this".

  RESPONSE TO AUDIT:
  ---
  {agent_response}
  ---"""


async def safety_audit(
      agent_response: str,
      crop_name: str,
      district: str = "",
  ) -> dict:
      """
      Run dual-layer safety audit on the agent's response.
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

      # Layer 2: Gemini auditor (catches nuance, reformats for WhatsApp)
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
      banned_list_text = _build_banned_list_text(crop_name)

      prompt = AUDITOR_PROMPT.format(
          crop_name=crop_name,
          district=district or "Haryana",
          banned_list=banned_list_text,
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
