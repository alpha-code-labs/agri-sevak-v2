"""Debug: check if Pinecone index has data and if queries return results."""                                                                                                                                                                                               
import sys
from pathlib import Path                                                                                                                                                                                                                                                   
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))                     

from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from shared.services.config import settings

  # 1. Check index stats
pc = Pinecone(api_key=settings.pinecone_api_key)
index = pc.Index(settings.pinecone_index_name)
stats = index.describe_index_stats()
print(f"Index: {settings.pinecone_index_name}")
print(f"Total vectors: {stats.get('total_vector_count', 0)}")
print(f"Namespaces: {stats.get('namespaces', {})}")
print()

  # 2. Try a raw query without any filter
model = SentenceTransformer(settings.sentence_transformer_model)
query_vec = model.encode("gehun me fungal rog ka ilaj").tolist()

print("Query WITHOUT crop filter:")
results = index.query(vector=query_vec, top_k=3, include_metadata=True)
for m in results.get("matches", []):
      print(f"  id={m['id']}  score={m['score']:.4f}  crop={m['metadata'].get('crop', '?')}")
print()

  # 3. Try with crop filter
print("Query WITH filter {'crop': 'wheat'}:")
results2 = index.query(vector=query_vec, top_k=3, filter={"crop": "wheat"}, include_metadata=True)
for m in results2.get("matches", []):
      print(f"  id={m['id']}  score={m['score']:.4f}  crop={m['metadata'].get('crop', '?')}")
print()

  # 4. Check what crop values exist
print("Sample crop values in index (first 5 vectors):")
fetch_result = index.query(vector=[0.0]*384, top_k=5, include_metadata=True)
for m in fetch_result.get("matches", []):
      print(f"  id={m['id']}  crop={m['metadata'].get('crop', '?')}")
