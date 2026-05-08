from fastapi import APIRouter

from app.services.agent_registry import get_registry

router = APIRouter(tags=["agents"])


@router.get("/agents")
async def list_agents() -> dict:
    registry = get_registry()
    result = {}
    for name, cls in registry.items():
        meta = cls.describe()
        result[name] = {
            "name": meta.name,
            "version": meta.version,
            "supported_languages": meta.supported_languages,
            "max_input_size_bytes": meta.max_input_size_bytes,
            "cost_profile": meta.cost_profile,
            "description": meta.description,
        }
    return result
