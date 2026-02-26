"""
Step 3.6 — RAG Retriever Tool (upgraded with FOUND/MISSING logic)
Encode query locally → search Pinecone → tag as FOUND or MISSING.
FOUND: return evidence with safety warnings injected.
MISSING: use RAG_GROUNDED_ADVICE prompt for grounded generation.
"""

import json
import logging
from functools import lru_cache

from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from langchain_core.tools import tool

from shared.services.config import settings
from shared.services.tools.safety_checker import (
    scan_text_for_banned,
    get_banned_chemicals_for_crop,
)

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.15
TOP_K = 3


# ── RAG Grounded Advice Prompt (from old system) ─────────────────────────

RAG_GROUNDED_ADVICE_PROMPT = """You are a Senior Agronomist at Haryana Agricultural University (HAU, Hisar).
Your task is to provide agricultural advice to an Indian farmer.

STRICT LANGUAGE RULE:
- EVERY WORD of the response must be in HINDI (Devanagari script).
- Translate all English 'queries' and English 'evidence' into professional, easy-to-understand Hindi.
- Keep technical chemical names in Hindi script (e.g., 'Imidacloprid' as 'इमिडाक्लोप्रिड').

OUTPUT STRUCTURE:
1. Introduction: Always start with "किसान भाई, यह रहा आपके सवालों का उत्तर:"

2. Conditional Headers:
   - IF ALL queries have status 'FOUND': Do NOT use any section headers. Just list Q&A.
   - IF THERE is a MIX of 'FOUND' and 'MISSING':
     * Use Header: "**भाग अ: प्रमाणित जानकारी**" for FOUND entries.
     * Use Header: "**भाग ब: विशेषज्ञ शोध**" for MISSING entries.

3. Content Logic:
   - For 'FOUND': Translate the provided evidence accurately into Hindi.
   - For 'MISSING': Use your expert internal knowledge to write a factual answer in Hindi.

4. SAFETY — BANNED PESTICIDES:
   - Some RAG results may contain a "safety_warnings" field.
   - If present, these chemicals are BANNED by CIB&RC India for this crop.
   - You MUST NOT include any banned chemical in your response.
   - Instead, suggest a safe, registered alternative for the same problem.
   - If no alternative is known, advise the farmer to consult HAU/KVK experts.

5. Formatting:
   - Use bullet points for dosages and steps."""


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load sentence-transformer once, cache forever."""
    return SentenceTransformer(settings.sentence_transformer_model)


@lru_cache(maxsize=1)
def _get_index():
    """Connect to Pinecone index once, cache forever."""
    pc = Pinecone(api_key=settings.pinecone_api_key)
    return pc.Index(settings.pinecone_index_name)


def _normalize_crop(crop_name: str) -> str:
    """Normalize crop name to match Pinecone metadata format."""
    return crop_name.strip().lower().replace(" ", "_")


def _search_pinecone(query: str, crop_name: str) -> list[dict]:
    """Encode query locally and search Pinecone with crop filter."""
    model = _get_model()
    query_vector = model.encode(query).tolist()

    index = _get_index()
    crop_tag = _normalize_crop(crop_name)

    results = index.query(
        vector=query_vector,
        top_k=TOP_K,
        filter={"crop": crop_tag},
        include_metadata=True,
    )

    matches = []
    for match in results.get("matches", []):
        score = match.get("score", 0.0)
        if score >= SIMILARITY_THRESHOLD:
            metadata = match.get("metadata", {})
            matches.append({
                "id": match["id"],
                "score": round(score, 4),
                "text": metadata.get("text_full", metadata.get("text_preview", "")),
                "crop": metadata.get("crop", ""),
            })

    return matches


def _inject_safety_warnings(evidence_texts: list[str], crop_name: str) -> list[str]:
    """Scan evidence for banned chemicals and return warning strings."""
    warnings = []
    for text in evidence_texts:
        banned = scan_text_for_banned(text, crop_name)
        for b in banned:
            name = b["chemical_name"]
            warnings.append(
                f"⚠️ BANNED: {name} is banned for {crop_name} per CIB&RC India. "
                f"Do NOT recommend this chemical. Suggest a safe, registered alternative instead."
            )
    # Deduplicate
    return list(dict.fromkeys(warnings))


async def _grounded_generation(rag_result: dict, crop_name: str) -> str:
    """Use RAG_GROUNDED_ADVICE prompt to generate a grounded response."""
    from shared.services.gemini_pool import GeminiPool

    keys = settings.gemini_keys_list
    if not keys:
        return ""

    pool = GeminiPool(api_keys=keys)
    payload = json.dumps(rag_result, ensure_ascii=False)
    prompt = f"{RAG_GROUNDED_ADVICE_PROMPT}\n\nRAG_RESULTS_JSON:\n{payload}"

    try:
        return await pool.generate(
            model=settings.gemini_model_quality,
            contents=prompt,
            temperature=0,
        )
    except Exception as e:
        logger.error("Grounded generation failed for crop=%s: %s", crop_name, e)
        return ""


@tool
async def rag_retriever(query: str, crop_name: str) -> dict:
    """Retrieve agricultural knowledge for a crop query. Searches the RAG knowledge base.
    Returns FOUND results with evidence, or MISSING with Gemini-generated grounded advice."""

    # 1. Search Pinecone
    matches = _search_pinecone(query, crop_name)

    if matches:
        # ── FOUND path ──────────────────────────────────────────────
        evidence_texts = [m["text"] for m in matches]
        safety_warnings = _inject_safety_warnings(evidence_texts, crop_name)

        rag_result = {
            "query": query,
            "crop": crop_name,
            "status": "FOUND",
            "evidence": evidence_texts,
            "scores": [m["score"] for m in matches],
        }
        if safety_warnings:
            rag_result["safety_warnings"] = safety_warnings

        # Generate grounded response using the proven prompt
        grounded = await _grounded_generation(rag_result, crop_name)

        return {
            "source": "pinecone_rag",
            "status": "FOUND",
            "grounded_response": grounded,
            "evidence_count": len(matches),
            "top_score": matches[0]["score"] if matches else 0,
            "safety_warnings": safety_warnings,
        }

    # ── MISSING path ────────────────────────────────────────────────
    logger.info("No RAG results for crop=%s, query=%s. Status: MISSING.", crop_name, query[:80])

    rag_result = {
        "query": query,
        "crop": crop_name,
        "status": "MISSING",
        "evidence": [],
    }

    # Generate response using grounded prompt (it knows to use expert knowledge for MISSING)
    grounded = await _grounded_generation(rag_result, crop_name)

    if not grounded:
        return {
            "source": "none",
            "status": "MISSING",
            "grounded_response": "",
            "evidence_count": 0,
        }

    # Run local banned chemical scan on generated text
    banned_found = scan_text_for_banned(grounded, crop_name)

    return {
        "source": "gemini_grounded",
        "status": "MISSING",
        "grounded_response": grounded,
        "evidence_count": 0,
        "safety_warnings": [
            f"⚠️ BANNED: {b['chemical_name']} found in generated advice"
            for b in banned_found
        ] if banned_found else [],
    }
