from fastapi import APIRouter

router = APIRouter()


@router.get("/incidents", tags=["Incidents"])
async def list_incidents():
    return []
