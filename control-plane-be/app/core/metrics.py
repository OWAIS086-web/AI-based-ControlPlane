"""
Custom Prometheus metrics for per-user and business-level tracking.

Standard HTTP metrics (latency, throughput, status codes) are handled
automatically by prometheus-fastapi-instrumentator.  This module adds
user-level counters that the instrumentator cannot provide.
"""

from prometheus_client import Counter

# Per-authenticated-user request counter.
# Labels kept to a minimum to avoid high cardinality.
user_requests_total = Counter(
    "controlplane_user_requests_total",
    "Total HTTP requests per authenticated user",
    ["user_id", "method", "handler", "status_code"],
)
