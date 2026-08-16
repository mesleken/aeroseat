from fastapi import APIRouter
from app.api.v1.endpoints import projects, simulations, correlation, evidence, pulse_upload, cad_upload

api_router = APIRouter()

api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(simulations.router, tags=["simulations"])
api_router.include_router(correlation.router, tags=["correlation"])
api_router.include_router(evidence.router, tags=["evidence"])
api_router.include_router(pulse_upload.router, tags=["pulses"])
api_router.include_router(cad_upload.router, tags=["cad"])
