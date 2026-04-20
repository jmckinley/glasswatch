"""
Prometheus metrics endpoint.

Exposes application metrics for Prometheus scraping.
"""
from fastapi import APIRouter, Response

from backend.services.metrics_service import get_metrics_service


router = APIRouter()


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text exposition format.
    """
    metrics_service = get_metrics_service()
    
    metrics_data = metrics_service.generate_metrics()
    content_type = metrics_service.get_content_type()
    
    return Response(
        content=metrics_data,
        media_type=content_type,
    )
