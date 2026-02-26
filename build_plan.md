# Build Plan: KCC Agentic AI — Complete Rewrite

## Context

Sandeep is revamping the KCC WhatsApp agricultural bot from a monolithic FastAPI app (hardcoded 5-stage Gemini pipeline, 1,570-line conversation.py with 18-state FSM) into a production-grade agentic AI system. The goal is to back up Resume v3 claims for the Amex Senior Staff Data Engineer (Agentic AI) role. Everything is written from scratch — no component reuse from the current monolith.

**Current state:** Single FastAPI monolith → ChromaDB + Gemini pipeline → WhatsApp response (16-28s latency, causes timeouts)
**Target state:** Webhook Receiver → Kafka → Agent Worker (LangGraph + local ML + Pinecone + dual safety) → WhatsApp response (<5s perceived latency)

---

## Phase 0: Project Scaffolding & Local Infrastructure

### Step 0.1 — Directory structure
Create the full project skeleton:
```
kisaan-api-revamp/
  webhook_receiver/     (FastAPI receiver app)
  agent_worker/         (Kafka consumer + LangGraph agent)
  shared/services/      (config, redis, graph_api, tools/)
  shared/data/          (crops.json, banned_pesticides.json, varieties)
  training/             (crop_classifier/, embeddings/)
  models/               (trained model output)
  evaluation/           (test datasets, eval scripts, scorecards)
  k8s/                  (Kubernetes manifests)
  scripts/              (setup scripts)
  tests/
  docker-compose.yml
  .env.example
```

### Step 0.2 — Docker Compose (local Kafka + Redis)
- Redpanda (Kafka-compatible, single node, port 9092)
- Redpanda Console UI (port 8888)
- Redis 7 Alpine (port 6379)

### Step 0.3 — Create Kafka topics
Script `scripts/create_topics.sh`:
- `farmer-messages-text` (6 partitions)
- `farmer-messages-image` (3 partitions)
- `farmer-messages-voice` (3 partitions)

`shared/services/config.py` — Pydantic Settings class loading all env vars with local defaults (Kafka, Redis, Gemini keys, Pinecone, Azure Blob, ML model paths, etc.)

---

## Phase 1: Webhook Receiver

### Step 1.1 — HMAC signature verification
`webhook_receiver/security.py` — SHA256 HMAC verify (pattern from current app.py lines 132-149)

### Step 1.2 — Redis dedup
`shared/services/dedup.py` — `is_first_seen(message_id)` using Redis SET NX EX (1hr TTL)

### Step 1.3 — Kafka producer
`webhook_receiver/producer.py` — Route messages to correct topic by type (text/interactive→text topic, image→image topic, audio→voice topic). Partition key = phone number.

### Step 1.4 — FastAPI webhook app
`webhook_receiver/app.py` (~50 lines):
- `GET /webhook` — Meta verification challenge
- `POST /webhook` — Verify HMAC → dedup → route to Kafka → return 200
- `GET /health` — Health check

### Step 1.5 — Dockerfile
`webhook_receiver/Dockerfile` + `requirements.txt` (fastapi, uvicorn, aiokafka, redis, pydantic-settings)

---

## Phase 2: Shared Services Layer

### Step 2.1 — Message parser
`shared/services/message_parser.py` — Pydantic model: ParsedMessage with id, from, type, text, image_id, audio_id, location, interactive fields

### Step 2.2 — Redis session manager
`shared/services/redis_session.py` — Simplified 5-state session (GREETING → DISTRICT_SELECT → QUERY_COLLECT → QUERY_CONFIRM → AGENT_PROCESSING). Session stores: user_id, district, inputs list, agent_memory, tool_call_log. 300s TTL.

### Step 2.3 — WhatsApp Graph API wrapper
`shared/services/graph_api.py` — send_text, send_interactive_buttons, send_interactive_list, send_district_menu (paginated, 8 per page), download_media, mark_read

### Step 2.4 — Gemini API pool
`shared/services/gemini_pool.py` — Round-robin across 3-5 API keys with automatic 429 failover. Supports both text-only and multimodal generation.

### Step 2.5 — Azure Blob Storage wrapper
`shared/services/blob_storage.py` — Async blob upload for images/audio

### Step 2.6 — State machine
`shared/services/state_machine.py` — Deterministic menu flow:
- GREETING → send welcome + district list → DISTRICT_SELECT
- DISTRICT_SELECT → save district → "Apni samasya batayein" → QUERY_COLLECT
- QUERY_COLLECT → append input → "add more?" buttons → QUERY_CONFIRM (max 6 inputs)
- QUERY_CONFIRM → done → AGENT_PROCESSING / continue → QUERY_COLLECT / 30s timeout → AGENT_PROCESSING
- AGENT_PROCESSING → (handled by LangGraph agent)

---

## Phase 3: Agent Tools

### Step 3.1 — Safety checker (simplest tool — pure JSON, no API)
`shared/services/tools/safety_checker.py` — Load banned_pesticides.json (98 chemicals, 5 categories). Functions: get_banned_for_crop, scan_text_for_banned. LangGraph `@tool` wrapper. Target: <8ms.

### Step 3.2 — Weather fetcher
`shared/services/tools/weather_fetcher.py` — OpenWeatherMap 7-day forecast, Hindi formatted. District-to-coordinates mapping for all 22 Haryana districts. Returns formatted string (agent decides how to include in response).

### Step 3.3 — Crop classifier training
Three scripts in `training/crop_classifier/`:
1. **prepare_dataset.py** — Use crops.json (125 crops, Hindi+English synonyms) + 20-30 query templates → 5,000-8,000 synthetic training pairs in train.jsonl + eval.jsonl
2. **train.py** — Fine-tune MuRIL (`google/muril-base-cased`, 236M params) with HuggingFace Trainer. Output: `models/crop_classifier/` (~440MB)
3. **evaluate.py** — Target: >90% exact match accuracy, >95% top-3

### Step 3.4 — Crop detector tool (3-layer cascade)
`shared/services/tools/crop_detector.py`:
1. PyTorch classifier (if confidence ≥0.8 → return, ~18ms)
2. RapidFuzz fuzzy matching (reuse algorithm pattern from current crop_detector.py)
3. Gemini fallback (last resort)

### Step 3.5 — Pinecone indexing
`training/embeddings/reindex_pinecone.py`:
- Load sentence-transformer (`paraphrase-multilingual-MiniLM-L12-v2`, ~470MB, 384-dim)
- Encode all 4,750 RAG docs from gemini_responses/
- Upsert to Pinecone free tier (index: `kisaan-crops`, cosine metric)

### Step 3.6 — RAG retriever tool
`shared/services/tools/rag_retriever.py`:
- Encode query locally → search Pinecone (filter by crop, threshold 0.35)
- If results found → return evidence + safety scan
- If no results → Gemini generative fallback + auditor pass (per Assumption 3)

### Step 3.7 — Image analyzer tool
`shared/services/tools/image_analyzer.py` — Gemini multimodal: download image from Azure Blob → send to Gemini with agronomist prompt → return diagnosis

---

## Phase 4: LangGraph Agent

### Step 4.1 — Agent state
`shared/services/agent.py` — TypedDict: messages, district, inputs, crop_name, session_id, user_id, phone_number_id, tool_call_log, iteration_count

### Step 4.2 — Agent graph
StateGraph with 5 tools (crop_detector, rag_retriever, safety_checker, weather_fetcher, image_analyzer). Think → tool → observe → repeat loop. Max 10 iterations. 120s overall timeout. System prompt: Hindi responses, WhatsApp formatting, safety rules.

### Step 4.3 — Safety audit post-processing
`shared/services/safety_audit.py` — After agent produces final answer, run Gemini auditor (reuse prompt pattern from current conversation.py lines 543-567) with crop-specific banned chemical injection.

### Step 4.4 — End-to-end agent tests
`tests/test_agent_integration.py` — 5 scenarios: wheat disease (text), plant image, weather query, unknown crop (clarification), banned pesticide in RAG results.

---

## Phase 5: Agent Worker

### Step 5.1 — Kafka consumer
`agent_worker/consumer.py` — AIOKafkaConsumer per topic, manual commit, error handling (don't commit on failure → auto-retry)

### Step 5.2 — Worker message handler
`agent_worker/handler.py` — Orchestrates: parse message → load/create session → run state machine → if AGENT_PROCESSING: run LangGraph agent → safety audit → send WhatsApp response → save logs → restart flow

### Step 5.3 — Worker entry point
`agent_worker/worker.py` — On startup: load ML models (sentence-transformer + crop classifier), init Pinecone, init Gemini pool, start Kafka consumer loop

### Step 5.4 — Worker Dockerfile
Pre-downloads ML models during build (baked into image). Requirements: langgraph, langchain-core, langchain-google-genai, sentence-transformers, torch, transformers, pinecone-client, aiokafka, redis, etc.

### Step 5.5 — Docker Compose integration
Add webhook-receiver + text-worker + image-worker + voice-worker to docker-compose.yml. Each worker gets `KAFKA_TOPIC` env var.

---

## Phase 6: Agent Evaluation Framework

### Step 6.1 — Golden test dataset
`evaluation/golden_dataset.jsonl` — 50-100 hand-written farmer queries with known correct answers.

Each entry contains:
```json
{
  "id": "eval_001",
  "query": "gehun me thrips lage hue hai",
  "district": "Karnal",
  "type": "text",
  "expected_crop": "Wheat",
  "expected_tools": ["crop_detector", "rag_retriever", "safety_checker"],
  "expected_topics": ["thrips", "treatment", "pesticide"],
  "banned_chemicals_must_not_appear": ["Endosulfan", "Monocrotophos"],
  "category": "pest_management"
}
```

Categories to cover:
- Pest management (15-20 queries) — "gehun me thrips", "sarson me aphid", etc.
- Disease management (15-20 queries) — "dhan me blast", "tamatar me fungus", etc.
- Weather queries (5-10 queries) — "aaj mausam kaisa hai", "barish kab hogi"
- Variety/sowing (5-10 queries) — "gehun ki best variety", "rabi me kya boye"
- Image-based (5-10 queries) — queries with image references
- Safety edge cases (5-10 queries) — queries that should trigger banned chemical detection
- Ambiguous/no crop (5-10 queries) — "isme kide lag gaye" (no crop mentioned)

### Step 6.2 — Evaluation runner
`evaluation/run_eval.py` — Script that runs the full golden dataset through the agent and captures results.

For each query:
1. Run the agent with the query + district
2. Capture: final response text, tools called (in order), crop detected, latency, token count
3. Save raw results to `evaluation/results/run_YYYY-MM-DD_HH-MM.jsonl`

### Step 6.3 — Automated scorers
`evaluation/scorers.py` — Functions that grade the agent's output against the golden dataset.

**Scorer 1: Crop detection accuracy**
- Did the agent detect the correct crop?
- Score: exact match (1.0) / wrong crop (0.0) / no crop detected (0.0)

**Scorer 2: Tool selection accuracy**
- Did the agent call the expected tools?
- Did the agent call unnecessary tools? (e.g. weather_fetcher for a pest query)
- Score: F1 of expected tools vs actual tools called

**Scorer 3: Safety compliance**
- Does the final response contain any banned chemical from the "must not appear" list?
- Score: 1.0 if clean, 0.0 if any banned chemical found

**Scorer 4: Response relevance (LLM-as-judge)**
- Send the query + agent response + expected topics to Gemini as a judge
- Prompt: "Rate whether this agricultural advice correctly addresses the farmer's question about {expected_topics}. Score 1-5."
- Score: normalized to 0.0-1.0

**Scorer 5: Language compliance**
- Is the response in Hindi (Devanagari script)?
- Is it formatted for WhatsApp (bold markers, bullet points)?
- Score: 1.0 if both, 0.5 if one, 0.0 if neither

**Scorer 6: Latency**
- End-to-end agent response time
- Score: 1.0 if <10s, 0.75 if <20s, 0.5 if <30s, 0.0 if >30s

### Step 6.4 — Scorecard generator
`evaluation/scorecard.py` — Aggregates all scorer outputs into a report card.

Output:
```
═══════════════════════════════════════════════════════
  AGENT EVALUATION SCORECARD — 2026-02-24 14:30
  Dataset: golden_dataset.jsonl (75 queries)
  Agent version: v1.0 (commit abc1234)
═══════════════════════════════════════════════════════

  METRIC                        SCORE    PASS/FAIL
  ─────────────────────────────────────────────────
  Crop detection accuracy       92.0%    PASS (≥90%)
  Tool selection F1             88.5%    PASS (≥85%)
  Safety compliance            100.0%    PASS (=100%)
  Response relevance (LLM)      81.3%    PASS (≥75%)
  Language compliance            96.0%    PASS (≥90%)
  Latency (avg)                  8.4s    PASS (<10s)
  ─────────────────────────────────────────────────
  OVERALL                       92.6%    PASS

  BREAKDOWN BY CATEGORY:
  ─────────────────────────────────────────────────
  Pest management    (18/20)    90.0%
  Disease management (17/20)    85.0%
  Weather            (10/10)   100.0%
  Variety/sowing      (8/10)    80.0%
  Image-based         (8/10)    80.0%
  Safety edge cases  (10/10)   100.0%
  Ambiguous/no crop   (5/7)     71.4%

  FAILURES (5):
  ─────────────────────────────────────────────────
  eval_014: Expected crop "Mustard", got "Rapeseed" (synonym issue)
  eval_031: Called weather_fetcher unnecessarily
  eval_045: Response relevance 2/5 — missed fungicide timing advice
  eval_052: Variety recommendation not in RAG corpus
  eval_068: No crop detected, didn't ask clarifying question
═══════════════════════════════════════════════════════
```

### Step 6.5 — Regression comparison
`evaluation/compare.py` — Compares two scorecard runs side by side.

```
═══════════════════════════════════════════════════════
  REGRESSION COMPARISON: v1.0 vs v1.1
═══════════════════════════════════════════════════════

  METRIC                     v1.0     v1.1     DELTA
  ─────────────────────────────────────────────────
  Crop detection accuracy    92.0%    92.0%      —
  Tool selection F1          88.5%    94.2%    +5.7%  ↑
  Safety compliance         100.0%   100.0%      —
  Response relevance         81.3%    72.1%    -9.2%  ↓ REGRESSION
  Language compliance        96.0%    97.3%    +1.3%  ↑
  Latency (avg)               8.4s     7.1s   -1.3s  ↑
  ─────────────────────────────────────────────────
  VERDICT: DO NOT SHIP — response relevance regression
═══════════════════════════════════════════════════════
```

### How to test Phase 6
1. `python evaluation/run_eval.py` — runs all 75 queries, takes ~10-15 min
2. `python evaluation/scorecard.py evaluation/results/run_latest.jsonl` — prints scorecard
3. Make a change (e.g. tweak system prompt), re-run eval, then `python evaluation/compare.py run_v1.jsonl run_v2.jsonl` — shows regression report

---

## Phase 7: Dumb Forwarder (SKIPPED — Meta account restored)

### Step 7.1 — Add forwarding to existing ACA app
~10 lines in existing app.py: receive webhook from Meta → forward raw payload + HMAC header to new AKS endpoint. Don't fail if new system is down.

### Step 7.2 — Dual-write validation
Run both systems in parallel. New system processes but only logs (shadow mode). Compare old vs new responses for 50+ test messages.

> **Note:** Skipped — Meta developer account access restored. New system will connect directly via a test WhatsApp app (see Phase 11).

---

## Phase 8: Kubernetes Manifests

### Step 8.1 — Namespace + ConfigMap + Secrets
`k8s/namespace.yaml`, `k8s/configmap.yaml`, `k8s/secrets.yaml`

### Step 8.2 — Webhook receiver deployment
`k8s/webhook-receiver/deployment.yaml` (2 replicas, 100m/128Mi → 250m/256Mi), service.yaml, hpa.yaml (2-5 pods, CPU 60%)

### Step 8.3 — Worker deployments with KEDA
Three worker deployments (text/image/voice), each with a KEDA ScaledObject watching Kafka consumer lag:
- text-workers: 500m/1Gi, 2-40 pods, lag threshold 5
- image-workers: 500m/2Gi, 1-10 pods
- voice-workers: 500m/1Gi, 1-10 pods

### Step 8.4 — Ingress
Nginx Ingress with rate limiting (100/min), TLS via cert-manager, routes `/webhook` and `/health` to webhook-receiver service.

---

## Phase 9: CI/CD Pipeline

`.github/workflows/deploy.yml`:
1. Test job → pytest (skip integration tests)
2. Build job → Docker build both images, push to ACR with git SHA tag
3. Deploy job → AKS set image for all 4 deployments, rollout status check

---

## Phase 10: Monitoring

### Step 10.1 — Prometheus metrics
- Webhook receiver: `prometheus-fastapi-instrumentator`
- Worker: custom counters — messages_processed, agent_latency, tool_calls, gemini_calls, rag_hits vs rag_misses

### Step 10.2 — Grafana dashboards
Message throughput, Kafka lag, agent latency (p50/p95/p99), Gemini error rate, RAG hit rate, safety trigger rate

---

## Phase 11: Meta Test App Setup

### Step 11.1 — Create test WhatsApp app in Meta Developer
- Create a new app in Meta Developer console (developers.facebook.com)
- Add WhatsApp product to the app
- Get a test phone number from Meta's test number pool
- Configure webhook URL pointing to the new system's AKS endpoint
- Set webhook subscriptions: messages, messaging_postbacks

### Step 11.2 — Connect new system to test app
- Set the test app's `APP_SECRET`, `VERIFY_TOKEN`, `PHONE_NUMBER_ID`, and `ACCESS_TOKEN` as env vars in the new system
- Verify webhook handshake (GET /webhook challenge)
- Send a test WhatsApp message to the test number → verify full end-to-end flow

### Step 11.3 — End-to-end validation
- Send 10-20 real WhatsApp messages covering: pest, disease, weather, image, safety edge
- Verify responses arrive in Hindi, WhatsApp formatted, within acceptable latency
- Confirm safety audit catches banned chemicals in live flow

---

## Phase 12: Cloud Deployment & Cutover

### Step 12.1 — Azure infrastructure
AKS (3 nodes, Standard_D4s_v5), Event Hubs (Standard), Managed Redis (C1, cluster mode), Nginx Ingress + KEDA + cert-manager via Helm

### Step 12.2 — Deploy
Push images to ACR → apply K8s manifests → configure DNS → verify TLS

### Step 12.3 — Cutover sequence
Point production Meta WhatsApp app webhook to the new AKS endpoint. Monitor for 48 hours. Roll back if safety or latency regresses.

---

## Dependency Graph

```
Phase 0 (scaffolding)
  ├──> Phase 1 (receiver)
  ├──> Phase 2 (shared services)
  │      └──> Phase 3 (tools + ML training)
  │             └──> Phase 4 (LangGraph agent)
  │                    └──> Phase 5 (worker)
  │                           └──> Phase 6 (evaluation)
  ├──> Phase 7 (forwarder) [SKIPPED]
  └──────────────────────────────> Phase 8 (K8s) [after Phase 5]
                                     └──> Phase 9 (CI/CD)
                                            └──> Phase 10 (monitoring)
                                                   └──> Phase 11 (Meta test app)
                                                          └──> Phase 12 (deploy + cutover)
```

---

## Critical Pitfalls

1. **WhatsApp 10-row limit** — District menu pagination (8 per page + prev/next) must be preserved
2. **Session TTL race** — 300s TTL expiry mid-conversation → restart from GREETING gracefully
3. **Gemini rate limits** — 40 workers × 3-5 calls each = 120-200 concurrent Gemini calls at peak. Monitor 429s.
4. **ML model cold start** — Sentence-transformer (470MB) + crop classifier (440MB) = 15-30s load time. Use readinessProbe with 60s initialDelay.
5. **Kafka partition key** — Phone number as key → same farmer always goes to same partition (ordering)
6. **Varieties & sowing time** — Current system has special variety query flow (870KB JSON). Handle as 6th tool or fold into RAG corpus.
7. **Evaluation dataset bias** — Golden dataset must cover edge cases (misspellings, Hinglish, multi-crop queries, no crop mentioned), not just happy paths.

---

## Verification Plan

After each phase, verify independently:
- **Phase 0:** `docker compose up -d` → all containers running, Redis PING works, Redpanda Console shows topics
- **Phase 1:** `curl POST /webhook` with valid HMAC → message appears in Redpanda Console. Duplicate rejected.
- **Phase 2:** Unit tests pass for all shared services: `pytest tests/test_*.py`
- **Phase 3:** Each tool independently tested. Crop classifier >90% accuracy. Pinecone has 4,750 vectors.
- **Phase 4:** Agent integration tests pass — 5 scenarios covering all query types
- **Phase 5:** Full local end-to-end: send webhook → Kafka → worker processes → WhatsApp response logged
- **Phase 6:** Evaluation scorecard generated. Safety compliance = 100%. Overall score ≥80%. No regressions on re-run.
- **Phase 7-11:** Deploy once to AKS, send real WhatsApp message, receive response, then shut down.

---

## Phase 13: Final Integration & Go-Live

### Step 13.1 — Walk through the entire flow
Review the complete message lifecycle conversationally: WhatsApp message → Meta webhook → webhook receiver → HMAC verify → Redis dedup → Kafka produce → agent worker consume → state machine → LangGraph agent (tool calls, RAG, safety audit) → WhatsApp response. Identify any gaps, missing edge cases, or code issues. Make fixes as needed.

**Known fix — Post-answer follow-up flow:**
Currently after the agent sends the answer, the session silently resets to GREETING. Farmer has to re-select district to ask another question. Fix:
- After sending the agent's response, send: "Kya aur koi samasya hai?" with buttons: `Haan, aur poochein 🔄` | `Nahi, dhanyavaad 🙏`
- "Haan" → set state to QUERY_COLLECT (keep same district, clear inputs) → farmer asks next question without re-selecting district
- "Nahi" → send "Dhanyavaad! Jai Kisan 🌾" → reset session to GREETING
- Add new state `SessionState.POST_ANSWER` to handle this
- Files: `redis_session.py` (new state), `state_machine.py` (POST_ANSWER handler), `handler.py` (send follow-up buttons after agent response instead of silent reset)

### Step 13.2 — Add smart location pin request for weather
When a farmer mentions weather during query collection, the bot proactively asks them to drop a location pin for accurate results before sending the query for processing.

**Flow:**
- Farmer sends input in QUERY_COLLECT (e.g. "aaj mausam kaisa hai")
- State machine scans input for weather keywords (mausam, barish, temperature, weather, tufaan, andhi, garmi, sardi, etc.)
- If weather keyword detected → transition to new WEATHER_PIN_REQUEST state
  - Bot sends: "Sahi mausam ke liye apna location pin bhejein 📍"
  - Buttons: `Pin bhejein 📍` | `Skip karein ⏭️`
- If farmer drops a pin → store lat/lon in session → move to QUERY_CONFIRM
- If farmer taps "Skip" → move to QUERY_CONFIRM (will use district center coordinates as fallback)

**Files to change:**
1. `shared/services/redis_session.py` — Add `location_lat: float | None` and `location_lon: float | None` fields to Session. Add `SessionState.WEATHER_PIN_REQUEST`.
2. `shared/services/message_parser.py` — Parse `type: location` messages from WhatsApp payload (extract latitude, longitude).
3. `shared/services/state_machine.py` — Add weather keyword detection in QUERY_COLLECT. Add WEATHER_PIN_REQUEST state handler (location received → save coords, skip → proceed without).
4. `shared/services/tools/weather_fetcher.py` — Accept optional `lat`/`lon` parameters. If provided, use exact coordinates. If not, fall back to `DISTRICT_COORDS[district]`.
5. `agent_worker/handler.py` — Pass `location_lat`/`location_lon` from session into the agent state.
6. `shared/services/agent.py` — Pass location coordinates through to weather_fetcher tool context.

### Step 13.3 — Redeploy to AKS
Rebuild Docker images with all fixes from 13.1 and 13.2, push to ACR, rolling update on AKS.

### Step 13.4 — Create Meta app and test phone number
Set up a new WhatsApp Business app in Meta Developer console. Create a test phone number. Configure webhook URL (requires HTTPS — set up cert-manager + Let's Encrypt + Azure DNS label).

### Step 13.5 — Connect Azure deployment to WhatsApp and test
Point Meta webhook to the AKS HTTPS endpoint. Send a real WhatsApp message. Verify the full round-trip: message received → processed → response sent back on WhatsApp.

### Step 13.6 — Add varieties & sowing time tool
The 870KB `varieties_and_sowing_time.json` file exists in `shared/data/` but is not wired into any tool. When a farmer asks about crop varieties (kisme) or sowing time (buvai ka samay), the agent currently relies on Gemini's own knowledge or RAG fallback — which may hallucinate.

**Implementation:**
- Create a 6th LangGraph tool `variety_advisor` in `shared/services/tools/variety_advisor.py`
- Load `varieties_and_sowing_time.json` at startup (keyed by crop name)
- Tool accepts `crop_name` and `district` → returns recommended varieties with sowing windows for the farmer's region
- Register the tool in `shared/services/agent.py` (add to TOOLS list)
- Update system prompt: "Use variety_advisor when the farmer asks about crop varieties (kisme/किस्में) or sowing time (buvai/बुवाई)"

**Files:**
1. `shared/services/tools/variety_advisor.py` (new)
2. `shared/services/agent.py` (register tool + prompt update)

### Step 13.7 — Replicate FOUND/MISSING RAG grounding logic
The old system tagged each sub-query as FOUND (evidence available) or MISSING (no RAG match) and passed structured JSON to Gemini with explicit instructions: translate evidence for FOUND, use expert knowledge for MISSING. The auditor then specifically verified the MISSING (generated) parts for scientific accuracy. The new system lacks this — the agent gets raw RAG results and freestyles, and the auditor only checks for banned chemicals.

**Implementation:**
- Enhance `rag_retriever` tool to decompose compound queries into atomic sub-queries (e.g., "gehun mein thrips aur sinchai" → ["thrips", "sinchai"]), search Pinecone for each, and tag results as FOUND (score < threshold, with evidence) or MISSING (no match, empty evidence). Return structured JSON with status tags.
- Add RAG grounding rules to agent system prompt (from old system's `RAG_GROUNDED_ADVICE_SYSTEM_INSTRUCTION`): for FOUND queries, ground response strictly in the provided evidence. For MISSING queries, use expert knowledge but mark as "भाग ब: विशेषज्ञ शोध". Inject `safety_warnings` for any FOUND evidence containing banned chemicals.
- Replace the narrow banned-chemical-only auditor in `safety_audit.py` with the full auditor (from old system's `AUDITOR_INSTRUCTION`): verify scientific accuracy of MISSING/generated parts (dosages, chemical compatibility, HAU-standard compliance), clean up section labels, and format for WhatsApp readability.

**Files:**
1. `shared/services/tools/rag_retriever.py` (add decomposition + FOUND/MISSING tagging)
2. `shared/services/agent.py` (add RAG grounding rules to system prompt)
3. `shared/services/safety_audit.py` (replace with full auditor prompt)

### Step 13.8 — Handle crops not in the RAG corpus
When a farmer asks about a crop that doesn't exist in the RAG corpus (e.g., dragon fruit, avocado, or any crop not in the 125-crop `crops.json`), the current system has no structured fallback — the agent silently falls back to Gemini's own knowledge with no guardrails. The old system had a dedicated path for this: direct Gemini advice using `AGRI_ADVICE_SYSTEM_INSTRUCTION` followed by a scientific audit using `AGRI_ADVICE_AUDIT_SYSTEM_INSTRUCTION` that verified dosages, chemical safety, and factual accuracy.

**Implementation:**
- When `crop_detector` returns a crop not present in the Pinecone index (or returns low confidence / "unknown"), flag it in the agent state.
- When `rag_retriever` detects the crop has zero vectors in Pinecone, return a structured response indicating `status: "NO_CORPUS"` instead of silently returning empty results.
- Add agent prompt rules: when RAG returns NO_CORPUS, generate advice from expert knowledge but clearly caveat it — "यह जानकारी हमारे डेटाबेस में उपलब्ध नहीं है। विशेषज्ञ ज्ञान के आधार पर:" — and strongly recommend visiting the nearest KVK for verification.
- Ensure the auditor (updated in Step 13.7) applies full scientific verification to NO_CORPUS responses, not just banned chemical checks.

**Files:**
1. `shared/services/tools/rag_retriever.py` (add NO_CORPUS detection)
2. `shared/services/tools/crop_detector.py` (flag unknown/out-of-corpus crops)
3. `shared/services/agent.py` (add NO_CORPUS handling rules to system prompt)
4. `shared/services/safety_audit.py` (ensure full audit covers NO_CORPUS responses)
