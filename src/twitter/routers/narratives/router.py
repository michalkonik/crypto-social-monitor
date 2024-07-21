from typing import (
    List,
    Any,
    Optional,
    Dict
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

import src.twitter.services.narratives.narratives_service as narratives_service

router = APIRouter()


@router.get("/list", response_model=List)
async def get_narratives(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    """
    Get narratives list
    :return:
    """
    narratives = await narratives_service.get_narratives()
    if not narratives:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No narratives found."
        )
    return narratives


@router.get("/projects", response_model=List)
async def get_users_narratives(
        screen_names: Optional[List[str]] = Query(None),
        narrative_names: Optional[List[str]] = Query(None),
        order_by: Optional[str] = "updated_at",
        sort_order: Optional[str] = "desc",
        jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    """
    Get narratives for users
    :param screen_names:    Optional
    :param narrative_names: Optional
    :param order_by:  Optional  Default: created_time
    :param sort_order: Optional  Default: desc
    :return:
    """

    ORDER_BY_OPTIONS = ["score", "custom_score", "created_time"]
    SORT_ORDER_OPTIONS = ["asc", "desc"]

    if order_by not in ORDER_BY_OPTIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order_by value.")

    if sort_order not in SORT_ORDER_OPTIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sort_order value.")

    users_narratives = await narratives_service.get_screen_names_narratives_map(
        screen_names=screen_names,
        narrative_names=narrative_names,
        order_by=order_by,
        sort_order=sort_order
    )
    if not users_narratives:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No result found."
        )
    return users_narratives
