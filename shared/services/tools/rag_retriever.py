"""
  Step 3.6 — RAG Retriever Tool
  Encode query locally → search Pinecone → safety scan results.
  If no results → Gemini generative fallback + auditor pass.
  """

import logging
from functools import lru_cache

from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from langchain_core.tools import tool

from shared.services.config import settings
from shared.services.tools.safety_checker import scan_text_for_banned

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.15
TOP_K = 3


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


async def _gemini_fallback(query: str, crop_name: str) -> str:
      """When RAG has no results, use Gemini to generate an answer."""
      from shared.services.gemini_pool import GeminiPool

      keys = settings.gemini_keys_list
      if not keys:
          return ""

      pool = GeminiPool(api_keys=keys)
      prompt = (
          f"You are a Senior Agronomist at Haryana Agricultural University (HAU, Hisar).\n"
          f"A farmer growing {crop_name} asked: \"{query}\"\n\n"
          f"Provide scientifically verified advice in Hindi. "
          f"Include specific product names, dosages, and application methods where relevant. "
          f"If unsure, say so clearly."
      )

      try:
          return await pool.generate(model=settings.gemini_model_quality, contents=prompt)
      except Exception as e:
          logger.error(f"Gemini fallback failed: {e}")
          return ""


async def _gemini_auditor(generated_text: str, crop_name: str) -> dict:
      """Audit Gemini-generated text for safety — check for banned chemicals."""
      from shared.services.gemini_pool import GeminiPool

      # Layer 1: Local JSON scan (fast, free)
      banned_found = scan_text_for_banned(generated_text, crop_name)

      # Layer 2: Gemini auditor (catches what JSON scan might miss)
      keys = settings.gemini_keys_list
      gemini_audit = ""
      if keys:
          pool = GeminiPool(api_keys=keys)
          prompt = (
              f"You are a pesticide safety auditor for Indian agriculture.\n"
              f"Review this advice given to a farmer growing {crop_name}:\n\n"
              f"---\n{generated_text}\n---\n\n"
              f"Check if ANY banned, restricted, or withdrawn pesticide in India is recommended.\n"
              f"If you find any, list them. If the advice is safe, reply: SAFE"
          )
          try:
              gemini_audit = await pool.generate(
                  model=settings.gemini_model_fast, contents=prompt
              )
          except Exception as e:
              logger.error(f"Gemini auditor failed: {e}")

      return {
          "banned_chemicals_found": banned_found,
          "gemini_audit": gemini_audit.strip(),
          "is_safe": len(banned_found) == 0 and "SAFE" in gemini_audit.upper(),
      }


@tool
async def rag_retriever(query: str, crop_name: str) -> dict:
      """Retrieve agricultural knowledge for a crop query. Searches the RAG knowledge base and falls back to Gemini if needed."""

      # 1. Search Pinecone
      matches = _search_pinecone(query, crop_name)

      if matches:
          # Found in RAG corpus — run safety scan on the evidence
          combined_text = "\n".join(m["text"] for m in matches)
          banned_found = scan_text_for_banned(combined_text, crop_name)

          return {
              "source": "pinecone_rag",
              "evidence": [{"id": m["id"], "score": m["score"], "text": m["text"]} for m in matches],
              "safety": {
                  "banned_chemicals_found": banned_found,
                  "is_safe": len(banned_found) == 0,
              },
          }

      # 2. No RAG results — Gemini generative fallback
      logger.info(f"No RAG results for crop={crop_name}, query={query[:80]}. Using Gemini fallback.")
      generated = await _gemini_fallback(query, crop_name)

      if not generated:
          return {
              "source": "none",
              "evidence": [],
              "safety": {"banned_chemicals_found": [], "is_safe": True},
          }

      # 3. Audit the generated response
      audit = await _gemini_auditor(generated, crop_name)

      return {
          "source": "gemini_fallback",
          "evidence": [{"text": generated, "score": 0.0}],
          "safety": audit,
      }
