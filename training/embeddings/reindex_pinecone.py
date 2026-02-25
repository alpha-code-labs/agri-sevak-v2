import os
import sys
import time
from pathlib import Path

from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

  # ── Config ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from shared.services.config import settings

GEMINI_DIR = PROJECT_ROOT / "gemini_responses"
MODEL_NAME = settings.sentence_transformer_model  # paraphrase-multilingual-MiniLM-L12-v2
INDEX_NAME = settings.pinecone_index_name          # kisaan-crops
DIMENSION = 384
BATCH_SIZE = 100  # Pinecone upsert batch limit


def load_documents() -> list[dict]:
      """Walk gemini_responses/{crop}/q_*.txt and return list of {id, crop, text}."""
      docs = []
      for crop_dir in sorted(GEMINI_DIR.iterdir()):
          if not crop_dir.is_dir():
              continue
          crop_name = crop_dir.name
          for txt_file in sorted(crop_dir.glob("q_*.txt")):
              text = txt_file.read_text(encoding="utf-8").strip()
              if not text:
                  continue
              doc_id = f"{crop_name}/{txt_file.name}"
              docs.append({
                  "id": doc_id,
                  "crop": crop_name,
                  "text": text,
              })
      return docs


def create_or_get_index(pc: Pinecone) -> any:
      """Create the Pinecone index if it doesn't exist, then return it."""
      existing = [idx.name for idx in pc.list_indexes()]
      if INDEX_NAME not in existing:
          print(f"Creating index '{INDEX_NAME}' (dim={DIMENSION}, cosine)...")
          pc.create_index(
              name=INDEX_NAME,
              dimension=DIMENSION,
              metric="cosine",
              spec=ServerlessSpec(cloud="aws", region="us-east-1"),
          )
          # Wait for index to be ready
          while not pc.describe_index(INDEX_NAME).status["ready"]:
              print("  Waiting for index to be ready...")
              time.sleep(2)
          print("  Index ready.")
      else:
          print(f"Index '{INDEX_NAME}' already exists.")
      return pc.Index(INDEX_NAME)


def main():
      # 1. Load docs
      print("Loading documents from gemini_responses/...")
      docs = load_documents()
      print(f"  Found {len(docs)} documents across {len(set(d['crop'] for d in docs))} crops.")

      # 2. Load sentence-transformer model
      print(f"Loading model: {MODEL_NAME}...")
      model = SentenceTransformer(MODEL_NAME)
      print("  Model loaded.")

      # 3. Encode all texts
      print("Encoding documents (this may take a few minutes)...")
      texts = [d["text"] for d in docs]
      # Encode in batches to show progress
      all_embeddings = []
      encode_batch = 256
      for i in range(0, len(texts), encode_batch):
          batch = texts[i : i + encode_batch]
          embeddings = model.encode(batch, show_progress_bar=False)
          all_embeddings.extend(embeddings)
          print(f"  Encoded {min(i + encode_batch, len(texts))}/{len(texts)}")
      print("  Encoding complete.")

      # 4. Connect to Pinecone and create/get index
      api_key = settings.pinecone_api_key
      if not api_key:
          print("ERROR: PINECONE_API_KEY not set in .env")
          sys.exit(1)

      pc = Pinecone(api_key=api_key)
      index = create_or_get_index(pc)

      # 5. Upsert in batches
      print(f"Upserting {len(docs)} vectors to Pinecone (batch_size={BATCH_SIZE})...")
      upserted = 0
      for i in range(0, len(docs), BATCH_SIZE):
          batch_docs = docs[i : i + BATCH_SIZE]
          batch_embs = all_embeddings[i : i + BATCH_SIZE]

          vectors = []
          for doc, emb in zip(batch_docs, batch_embs):
              # Store first 500 chars of text as metadata (Pinecone metadata limit)
              vectors.append({
                  "id": doc["id"],
                  "values": emb.tolist(),
                  "metadata": {
                      "crop": doc["crop"],
                      "text_preview": doc["text"][:500],
                      "text_full": doc["text"][:8000],  # Pinecone allows up to 40KB metadata
                  },
              })

          index.upsert(vectors=vectors)
          upserted += len(vectors)
          print(f"  Upserted {upserted}/{len(docs)}")

      # 6. Verify
      stats = index.describe_index_stats()
      print(f"\nDone! Index stats: {stats}")
      print(f"Total vectors in index: {stats.get('total_vector_count', 'N/A')}")


if __name__ == "__main__":
      main()