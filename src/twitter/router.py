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


@router.get("/users/unique_mentions", response_model=Dict)
async def get_user_unique_mentions(
        screen_names: List[str] = Query(...),
        limit: Optional[int] = None,
):
    if not screen_names:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No screen names provided.")

    return await service.get_tickers_mentioned_by_users(
        screen_names=screen_names,
        limit=limit
    )


@router.get("/users/", response_model=Dict)
async def get_users_info(
        screen_names: List[str] = Query(...),
        short_info: Optional[bool] = False,
        include_market_data: Optional[bool] = False,
        all_ticker_mentions: Optional[bool] = False,
        limit: Optional[int] = None,
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        background_tasks: BackgroundTasks = BackgroundTasks()
) -> dict[str, str] | dict[str, str] | dict[Any, dict[str, dict[Any, Any] | Any]]:
    if sum([short_info, include_market_data, all_ticker_mentions]) > 1:
        return {"detail": "You can only use one of short_info, include_market_data, or only_ticker_mentions at a time"}

    if not screen_names:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No screen names provided.")

    accounts_info = await service.get_user_profiles_info(
        screen_names=screen_names
    )
    if not accounts_info:
        return {"detail": "Users are not found."}

    accounts_pnl_data = {}
    recently_mentioned_tickers = {}
    most_mentioned_tickers = {}

    if include_market_data:
        accounts_pnl_data = await service.get_screen_names_pnl(
            screen_names=screen_names,
            limit=limit,
            background_tasks=background_tasks
        )
    elif short_info:
        # TODO: Add to the response Wins, Loses, and Total PnL which would be saved in Redis
        # Get recently mentioned tickers
        recently_mentioned_tickers = await service.get_tickers_mentioned_by_users(
            screen_names=screen_names,
            limit=service.RECENTLY_MENTIONED_THRESHOLD
        )
        # Get most mentioned tickers
        most_mentioned_tickers = await service.get_tickers_mentioned_by_users(
            screen_names=screen_names,
            most_mentioned=True,
            limit=service.MOST_MENTIONED_THRESHOLD
        )

    result = {}
    for screen_name, account_info in accounts_info.items():
        user_data = {"account_info": account_info}

        if include_market_data:
            user_data["pnl_per_ticker"] = accounts_pnl_data.get(screen_name, {})

        if short_info:
            tickers = list(set(ticker['ticker'] for ticker in recently_mentioned_tickers.get(screen_name, [])))
            user_data["recently_mentioned_unique_tickers"] = tickers
            tickers = list(set(ticker['ticker'] for ticker in most_mentioned_tickers.get(screen_name, [])))
            user_data["most_mentioned_unique_tickers"] = tickers

        result[screen_name] = user_data

    return result


@router.get("/monitored", response_model=List[TwitterUsers])
async def get_monitored_users(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        page: int = 1,
        page_size: int = 10
) -> list[dict[str, Any]]:
    monitored_users = await service.get_monitored_twitter_users(
        skip=(page - 1) * page_size,
        limit=page_size
    )

    return monitored_users


@router.get("/suggested", response_model=List[TwitterSuggestedUsers])
async def get_monitored_users(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        page: int = 1,
        page_size: int = 10
) -> list[dict[str, Any]]:
    suggested_users = await service.get_suggested_twitter_users(
        skip=(page - 1) * page_size,
        limit=page_size
    )

    return suggested_users


@router.get("/followed", response_model=List[TwitterFollowedUsers])
async def get_followed_users(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        page: int = 1,
        page_size: int = 10
) -> list[dict[str, Any]]:
    followed_users = await service.get_followed_twitter_users(
        skip=(page - 1) * page_size,
        limit=page_size
    )

    return followed_users


@router.get("/posts", response_model=List[Posts])
async def get_twitter_posts(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        user: str = None,
        search_keywords: Optional[List[str]] = Query(None),  # This line is crucial
        page: int = 1,
        page_size: int = 10
) -> list[dict[str, Any]]:
    posts = await service.get_twitter_posts(
        user=user,
        search_keywords=search_keywords,
        skip=(page - 1) * page_size,
        limit=page_size
    )

    return posts


@router.get("/keyword_daily_stats", response_model=List)
async def get_twitter_tickers(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        keywords: List[str] = Query(...),
):
    if not keywords:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No keywords provided.")

    daily_stats = await service.get_keyword_mentions_stats_per_day(
        keywords=keywords,
    )
    return daily_stats


@router.get("/tickers", response_model=List)
async def get_twitter_user_tickers(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        user: str = None,
        ticker: str = None,
        page: int = 1,
        page_size: int = 10
) -> list[dict[str, Any]]:
    if not user and not ticker:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No user or ticker provided.")

    tickers = await service.get_twitter_tickers(
        user=user,
        ticker=ticker,
        skip=(page - 1) * page_size,
        limit=page_size
    )

    return tickers
