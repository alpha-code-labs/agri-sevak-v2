"""
Step 10.1 — Prometheus Metrics for Webhook Receiver
Auto-instruments all FastAPI endpoints via prometheus-fastapi-instrumentator.
"""

from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    excluded_handlers=["/health", "/metrics"],
)
