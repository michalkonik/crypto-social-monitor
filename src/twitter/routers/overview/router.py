import orjson
from typing import (
    Dict,
    Optional,
    List
)

from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException,
)

from src.auth.jwt import (
    parse_jwt_user_data
)
from src.auth.schemas import (
    JWTData
)

from src.twitter.helpers import (
    parse_timeframe_to_hours
)

import pytz

from datetime import (
    datetime,
    timedelta
)

import src.twitter.services.overview.overview_service as overview_service

router = APIRouter()


@router.get("/report", response_model=Dict)
async def get_overview_page_data(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        timeframe: Optional[str] = "1d"
):
    """
    Get overview page data
    :return:
    """
    overview_data = await overview_service.get_overview_data(
        timeframe=timeframe
    )
    if not overview_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No overview data found."
        )
    return {
        "hourly_changes_follows": orjson.loads(overview_data["hourly_changes_follows"]),
        "hourly_changes_ticker_mentions": orjson.loads(overview_data["hourly_changes_ticker_mentions"]),
        "word_cloud": orjson.loads(overview_data["word_cloud"]),
        "follows_activity": orjson.loads(overview_data["follows_activity"]),
        "posts_activity": orjson.loads(overview_data["posts_activity"]),
        "sentiment_activity": orjson.loads(overview_data["sentiment_activity"]),
        "projects_mind_share_activity": orjson.loads(overview_data["projects_mind_share_activity"]),
        "category_mind_share_activity": orjson.loads(overview_data["category_mind_share_activity"])
    }


@router.get("/activity", response_model=Dict)
async def get_twitter_activity(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    """
    Get CT activity
    :return:
    """
    activity = await overview_service.get_activity()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No activity found."
        )
    return activity


@router.get("/overview", response_model=Dict)
async def search_project(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        user_id: Optional[int] = None,
        screen_name: Optional[str] = None,
        timeframe: Optional[str] = "1d",
):
    """
    Get user overview
    :return:
    """
    OVERVIEW_TIME_FRAMES = ["1h", "4h", "6h", "12h", "1d", "3d", "7d", "14d", "1m"]
    if timeframe not in OVERVIEW_TIME_FRAMES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timeframe value.")

    if not user_id and not screen_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'user_id' or 'screen_name' must be provided."
        )

    # Define the timeframe in which we fetch the results
    hours = parse_timeframe_to_hours(
        timeframe_str=timeframe
    )
    current_time = datetime.now(pytz.timezone('Etc/GMT-3'))  # Adjust 'Etc/GMT-3' to match your specific timezone
    start_time = current_time - timedelta(hours=hours)

    user_overview = await overview_service.get_user_overview(
        twitter_user_id=user_id,
        screen_name=screen_name,
        start_time=start_time
    )
    if not user_overview or not user_overview["status"] or not user_overview["data"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User overview not found."
        )

    return user_overview["data"]


@router.get("/sentiment", response_model=List)
async def get_sentiment_overview(
        jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    """
    Get sentiment overview
    :return:
    """
    sentiment_overview = await overview_service.get_sentiment_overview_with_smoothening()
    if not sentiment_overview:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No sentiment overview found."
        )
    return sentiment_overview
