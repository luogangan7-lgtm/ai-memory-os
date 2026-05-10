# AI Memory OS - Prometheus Metrics
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

search_counter = Counter("memory_search_total", "Total search requests")
store_counter = Counter("memory_store_total", "Total memory stores")
search_latency = Histogram("memory_search_seconds", "Search latency")
memory_count = Counter("memory_total", "Total memories", ["lifecycle_stage"])

def metrics_response():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
