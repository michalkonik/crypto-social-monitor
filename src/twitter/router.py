from typing import List, Any, Optional, Dict

from fastapi import APIRouter, Depends, Query, BackgroundTasks, status, HTTPException

from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData

from src.twitter.schemas import (
    TwitterUsers,
    TwitterSuggestedUsers,
    TwitterFollowedUsers,
    Posts,
)

from src.twitter.helpers import (
    frequency_analysis
)

from src.twitter import service

router = APIRouter()


@router.get("/hourly_changes_stats", response_model=List)
async def get_hourly_changes_stats(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        data_type: Optional[str] = "follows",
        timeframe: Optional[str] = "7d"
):
    """
    Get hourly changes in followings, comparing the recent period defined by `timeframe`
    to the previous period of the same length.

    :param jwt_data:
    :param data_type: Options are ["follows", "ticker_mentions"]
    :param timeframe: Options are ["1h", "4h", "6h", "12h", "1d", "3d", "7d", "14d", "1m"]
    :return:
    """
    TRENDING_TIME_FRAMES = ["1h", "4h", "6h", "12h", "1d", "3d", "7d", "14d", "1m"]
    if timeframe not in TRENDING_TIME_FRAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timeframe value."
        )

    DATA_TYPES_OPTIONS = ["follows", "ticker_mentions"]
    if data_type not in DATA_TYPES_OPTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data_type value."
        )

    hourly_changes_stats = []
    if data_type == "follows":
        hourly_changes_stats = await service.fetch_hourly_changes_of_follows(
            timeframe=timeframe
        )
    elif data_type == "ticker_mentions":
        hourly_changes_stats = await service.fetch_hourly_changes_of_ticker_mentions(
            timeframe=timeframe
        )
    # elif data_type == "twitter_profile_mentions":
    #     hourly_changes_stats = []

    if not hourly_changes_stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No changes found for timeframe."
        )

    return hourly_changes_stats


@router.get("/wordcloud", response_model=Dict)
async def get_word_cloud(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        timeframe: Optional[str] = "1d",
        limit: Optional[int] = 1000,
):
    """
    Get word cloud data
    :param jwt_data:
    :param timeframe: Options are ["1h", "4h", "6h", "12h", "1d", "3d", "7d", "14d", "1m"]
    :param limit:
    :return:
    """
    TRENDING_TIME_FRAMES = ["1h", "4h", "6h", "12h", "1d", "3d", "7d", "14d", "1m"]

    if timeframe not in TRENDING_TIME_FRAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timeframe value."
        )

    word_cloud_data = await service.get_posts_for_timeframe(
        timeframe=timeframe
    )
    if not word_cloud_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No posts found for timeframe."
        )

    return frequency_analysis(
        posts=word_cloud_data,
        limit=limit
    )


@router.get("/projects", response_model=List)
async def get_crypto_projects(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        order_by: Optional[str] = "latest",
        sort_order: Optional[str] = "desc",
        timeframe: Optional[str] = "1d",
        page: int = 1,
        page_size: int = 10
):
    """
    Get crypto projects profiles
    :param jwt_data:
    :param sort_order: desc or asc
    :param order_by: Options are ["followers_count", "tweets_count", "latest", "trending", "score"]
    :param timeframe: Options are ["1h", "4h", "6h", "12h", "1d", "3d", "7d", "14d", "1m"]
    :param page:
    :param page_size:
    :return:
    """
    ORDER_BY_OPTIONS = ["followers_count", "tweets_count", "latest", "trending", "score"]
    SORT_ORDER_OPTIONS = ["desc", "asc"]
    TRENDING_TIME_FRAMES = ["1h", "4h", "6h", "12h", "1d", "3d", "7d", "14d", "1m"]

    if order_by not in ORDER_BY_OPTIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order_by value.")

    if sort_order not in SORT_ORDER_OPTIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sort_order value.")

    if timeframe not in TRENDING_TIME_FRAMES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timeframe value.")

    mentions = await service.get_crypto_projects_profiles(
        order_by=order_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        timeframe=timeframe
    )
    return mentions


@router.get("/tickers/mentions/", response_model=List)
async def get_tickers_info(
        tickers: List[str] = Query(...),
        relative_strength_index: Optional[bool] = False,
        limit: Optional[int] = None,
        jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    if not tickers:
        # Here you raise an HTTPException with status code 400 for "Bad Request"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No tickers provided.")

    mentions = await service.get_tickers_mentions(
        tickers=tickers,
        limit=limit
    )
    return mentions if not relative_strength_index else await service.get_relative_mentions_score_for_tickers(
        mentions=mentions
    )


@router.get("/tickers", response_model=Dict)
async def get_tickers_info(
        page: int = 1,
        page_size: int = 10,
        mentions_limit: Optional[int] = 5,
        jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    tickers_info = await service.get_all_tickers_for_which_we_know_the_twitter_handler(
        page=page,
        page_size=page_size
    )

    tickers_info_dict = {}
    tickers = []
    for info in tickers_info:
        ticker = f"${info['ticker'].lower()}"
        tickers.append(ticker)
        if ticker not in tickers_info_dict:
            tickers_info_dict[ticker] = {}
        tickers_info_dict[ticker] = info

    if not tickers:
        # Here you raise an HTTPException with status code 400 for "Bad Request"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No tickers provided.")

    tickers_with_mentions = {}
    for ticker in tickers:
        if ticker not in tickers_with_mentions:
            tickers_with_mentions[ticker] = {}
        mentions = await service.get_tickers_mentions(
            tickers=[ticker],
            limit=mentions_limit
        )
        # mentions_with_strength_score = await service.get_relative_mentions_score_for_tickers(
        #     mentions=mentions
        # )
        tickers_with_mentions[ticker]['market_data'] = tickers_info_dict[f"{ticker.lower()}"]
        tickers_with_mentions[ticker]['mentions'] = mentions
    return tickers_with_mentions


