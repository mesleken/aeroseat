from fastapi import APIRouter
from app.api.v1.endpoints import projects, simulations, correlation, evidence

api_router = APIRouter()

api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(simulations.router, tags=["simulations"])
api_router.include_router(correlation.router, tags=["correlation"])
api_router.include_router(evidence.router, tags=["evidence"])
