from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.applications import router as applications_router
from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.validation import router as validation_router
from app.api.routes.workflow import router as workflow_router
from app.core.config import settings

# Initialize the FastAPI application
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

# Configure CORS with explicit origins and credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Accept"],
)

# Register API routes
app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(applications_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(validation_router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": "AIC-Flow API is running",
        "environment": settings.app_env,
    }
