"""
Step 10.1 — Prometheus Metrics for Agent Worker
Custom counters and histograms for agent processing.
Exposes /metrics on port 9090 via a background HTTP server.
"""

import logging
from prometheus_client import Counter, Histogram, start_http_server

logger = logging.getLogger(__name__)

# ── Counters ────────────────────────────────────────────────────────

messages_processed = Counter(
    "kcc_messages_processed_total",
    "Total messages processed by workers",
    ["topic", "status"],  # status: success, error
)

tool_calls = Counter(
    "kcc_tool_calls_total",
    "Total tool invocations by the agent",
    ["tool_name"],
)

gemini_calls = Counter(
    "kcc_gemini_calls_total",
    "Total Gemini API calls",
    ["model", "status"],  # status: success, rate_limited, error
)

rag_results = Counter(
    "kcc_rag_results_total",
    "RAG retrieval outcomes",
    ["source"],  # source: pinecone_hit, gemini_fallback
)

safety_triggers = Counter(
    "kcc_safety_triggers_total",
    "Banned chemicals caught by safety audit",
    ["layer"],  # layer: local_scan, gemini_auditor
)

# ── Histograms ──────────────────────────────────────────────────────

agent_latency = Histogram(
    "kcc_agent_latency_seconds",
    "End-to-end agent processing duration",
    buckets=[1, 2, 5, 10, 15, 20, 30, 45, 60, 90, 120],
)


def start_metrics_server(port: int = 9090):
    """Start a background HTTP server to expose /metrics for Prometheus."""
    start_http_server(port)
    logger.info("Prometheus metrics server started on port %d", port)
