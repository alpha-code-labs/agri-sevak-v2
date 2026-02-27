# Agent Tools

1. **crop_detector** — 3-layer cascade (MuRIL classifier → RapidFuzz fuzzy → Gemini fallback) to identify the crop from farmer input
2. **rag_retriever** — Encode query with sentence-transformer → Pinecone vector search → return verified knowledge. Gemini generative fallback if no results.
3. **safety_checker** — Check if response contains banned pesticides (pure JSON lookup, no API call)
4. **weather_fetcher** — OpenWeatherMap 7-day forecast, Hindi formatted. District-to-coordinates mapping for Haryana.
5. **image_analyzer** — Observer-only: Gemini multimodal describes visual symptoms from farmer photo (no diagnosis, no treatment)
6. **variety_advisor** — Crop variety and sowing time recommendations from varieties JSON data
7. **general_crop_advisor** — Gemini-powered advice for crops outside the RAG corpus (when crop_detector returns gemini_fallback source)
