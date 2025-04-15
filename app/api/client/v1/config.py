from fastapi import APIRouter
from app.schemas.response import ApiResponse
from app.common.release import RELEASE_CONFIG

router = APIRouter()


@router.get("/release")
async def get_release_config():
    return ApiResponse.success(data=RELEASE_CONFIG)
    

