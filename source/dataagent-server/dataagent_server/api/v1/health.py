"""Health check endpoint."""

import time

from fastapi import APIRouter

from dataagent_server import __version__
from dataagent_server.models import HealthResponse

router = APIRouter(tags=["health"])

# Server start time for uptime calculation
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.
    
    Returns service status, version, and uptime.
    """
    return HealthResponse(
        status="ok",
        version=__version__,
        uptime=time.time() - _start_time,
    )
