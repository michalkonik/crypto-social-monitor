from typing import (
    List
)

from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException,
    Query
)

from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData

import src.twitter.services.search.search_service as search_service

router = APIRouter()


@router.get("/project", response_model=List)
async def search_project(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        search_term: str = Query(None),
        limit: int = 60
):
    """
    Get search term matches
    :return:
    """
    search_matches = await search_service.search_project(
        search_term=search_term,
        limit=limit
    )
    if not search_matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search term matches were not found."
        )
    return search_matches
