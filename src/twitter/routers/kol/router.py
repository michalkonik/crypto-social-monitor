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

from src.auth.jwt import (
    parse_jwt_user_data
)
from src.auth.schemas import (
    JWTData
)

import src.twitter.services.kol.kol_service as kol_service

router = APIRouter()


@router.get("/list", response_model=List | Dict[str, Any])
async def get_kol_clusters(
        include_cluster_stats: Optional[bool] = False,
        jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    """
    Get clusters list
    :return:
    """
    kol_cluster = await kol_service.get_kol_clusters(
        include_cluster_stats=include_cluster_stats
    )
    if not kol_cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No clusters found."
        )
    return kol_cluster


@router.get("/profiles", response_model=List)
async def get_cluster_profiles(
        screen_names: Optional[List[str]] = Query(None),
        cluster_names: Optional[List[str]] = Query(None),
        order_by: Optional[str] = "updated_at",
        sort_order: Optional[str] = "desc",
        jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    """
    Get cluster users
    :param screen_names:    Optional
    :param cluster_names: Optional
    :param order_by:  Optional  Default: created_time
    :param sort_order: Optional  Default: desc
    :return:
    """

    ORDER_BY_OPTIONS = ["created_time"]
    SORT_ORDER_OPTIONS = ["asc", "desc"]

    if order_by not in ORDER_BY_OPTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order_by value."
        )

    if sort_order not in SORT_ORDER_OPTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid sort_order value."
        )

    clusters_profiles = await kol_service.get_kol_profiles(
        screen_names=screen_names,
        cluster_names=cluster_names,
        order_by=order_by,
        sort_order=sort_order
    )
    if not clusters_profiles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No result found."
        )
    return clusters_profiles
