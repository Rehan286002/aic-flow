from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.redis_client import redis_client
from app.db.session import engine

router = APIRouter()


@router.get("/health")
def health_check():
    checks = {}

    # Check PostgreSQL
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        checks["database"] = "ok"

    except Exception:  # noqa: BLE001
        checks["database"] = "error"

    # Check Redis
    try:
        redis_client.ping()
        checks["redis"] = "ok"

    except Exception:  # noqa: BLE001
        checks["redis"] = "error"

    is_healthy = all(value == "ok" for value in checks.values())

    return JSONResponse(
        status_code=200 if is_healthy else 503,
        content={
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "AIC-Flow API",
            "checks": checks,
        },
    )
