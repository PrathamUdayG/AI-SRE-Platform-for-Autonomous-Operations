from fastapi import APIRouter

router = APIRouter()


@router.get("/infrastructure", tags=["Infrastructure"])
async def get_infrastructure():
    return []
