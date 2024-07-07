import logging
import os
from datetime import (
    datetime,
    timedelta,
    timezone
)

from typing import (
    Any,
    List,
    Dict,
    Optional
)

import pytz

from sqlalchemy import (
    select,
    or_,
    distinct,
    func,
    join,
    and_,
    desc,
    text,
    cast,
    Float,
)
from sqlalchemy.sql.expression import (
    case,
    asc
)
from sqlalchemy.orm import (
    aliased
)

from src.twitter.schemas import (
    TwitterUsers,
    TwitterFollowedUsers,
    TwitterSuggestedUsers,
    Posts,
    Tickers,
    TickerMarketData,
    CoingeckoMetaData,
    PreCalculatedDataStore
)

from src.database import (
    fetch_one,
    fetch_all
)

from src.twitter.background_tasks import (
    update_market_data_in_a_thread
)

from src.twitter.helpers import (
    parse_timeframe_to_hours,
    calculate_smart_followers_score,
    match_category_with_score,
    extract_categories_from_json,
    flatten_mixed_list
)

RECENTLY_MENTIONED_THRESHOLD = 7
MOST_MENTIONED_THRESHOLD = 5

EXCLUDED_CATEGORIES = ["coin", "token"]


async def fetch_categories_for_screen_names(screen_names: List[str]):
    # Assuming a hypothetical function that returns a query for a given screen name and table name
    def get_query_for_screen_name_and_table(_screen_name: str, _table_name: str) -> str:
        column = 'meta_data' if _table_name != 'extractedcontractsmetadata' else 'market_meta_data'
        # This is a placeholder: you'll need to replace it with actual SQL that makes sense for your schema
        return (f"SELECT {column} as meta_data FROM {table_name} "
                f"WHERE twitter_username = '{screen_name}' LIMIT 1")

    results = {}
    table_names = [
        'coingeckometadata',
        'coinmarketcapmetadata',
        'GeckoTerminalMetaData',
        'extractedcontractsmetadata'
    ]

    for screen_name in screen_names:
        for table_name in table_names:
            # Get the query for the current table and screen name
            query = get_query_for_screen_name_and_table(screen_name, table_name)
            result = await fetch_one(text(query))
            if not result:
                continue
            # Assuming we want to bundle results by screen name and table
            if screen_name not in results:
                results[screen_name] = []
            res = extract_categories_from_json(
                json_data=result.get("meta_data")
            )
            if not res:
                continue
            res = flatten_mixed_list(res)
            res = [r for r in res if r.lower() not in EXCLUDED_CATEGORIES]
            if not res:
                continue
            results[screen_name].extend(res)

    return results


async def fetch_hourly_changes_of_ticker_mentions(
        timeframe: str
) -> list:
    """
    Fetches changes in ticker mentions, comparing the recent period defined by `hours`
    to the previous period of the same length.

    :param timeframe: Timeframe for calculating changes, e.g., "1d" for one day.
    :return: A list of dictionaries with the query results.
    """
    hours = parse_timeframe_to_hours(timeframe_str=timeframe)
    recent_period_start = datetime.now() - timedelta(hours=hours)
    previous_period_start = datetime.now() - timedelta(hours=2 * hours)
    previous_period_end = datetime.now() - timedelta(hours=hours)

    recent_mentions = select(
        Tickers.ticker,
        func.count().label('recent_count')
    ).where(
        Tickers.created_time >= recent_period_start
    ).group_by(Tickers.ticker).cte('recent_mentions')

    previous_mentions = select(
        Tickers.ticker,
        func.count().label('previous_count')
    ).where(
        (Tickers.created_time < previous_period_end) &
        (Tickers.created_time >= previous_period_start)
    ).group_by(Tickers.ticker).cte('previous_mentions')

    final_query = select(
        recent_mentions.c.ticker,
        recent_mentions.c.recent_count,
        previous_mentions.c.previous_count,
        (recent_mentions.c.recent_count - func.coalesce(previous_mentions.c.previous_count, 0)).label('increase')
    ).select_from(
        recent_mentions.join(previous_mentions, recent_mentions.c.ticker == previous_mentions.c.ticker, isouter=True)
    ).where(
        recent_mentions.c.recent_count > func.coalesce(previous_mentions.c.previous_count, 0),
        (recent_mentions.c.recent_count - func.coalesce(previous_mentions.c.previous_count, 0)) > 3
    ).order_by(
        text('increase DESC')
    )

    return await fetch_all(final_query)


async def fetch_hourly_changes_of_follows(timeframe: str) -> list:
    """
    Fetches weekly changes in followings, comparing the recent period defined by `hours`
    to the previous period of the same length.

    :param timeframe:
    :return: A list of dictionaries with the query results.
    """
    hours = parse_timeframe_to_hours(
        timeframe_str=timeframe
    )
    recent_period_start = datetime.now() - timedelta(hours=hours)
    previous_period_start = datetime.now() - timedelta(hours=2 * hours)
    previous_period_end = datetime.now() - timedelta(hours=hours)

    recent_follows = select(
        TwitterFollowedUsers.followed_user_id,
        func.count().label('recent_count')
    ).where(
        TwitterFollowedUsers.created_time >= recent_period_start
    ).group_by(TwitterFollowedUsers.followed_user_id).cte('recent_follows')

    previous_follows = select(
        TwitterFollowedUsers.followed_user_id,
        func.count().label('previous_count')
    ).where(
        (TwitterFollowedUsers.created_time < previous_period_end) &
        (TwitterFollowedUsers.created_time >= previous_period_start)
    ).group_by(TwitterFollowedUsers.followed_user_id).cte('previous_follows')

    final_query = select(
        TwitterUsers.screen_name,
        recent_follows.c.followed_user_id,
        recent_follows.c.recent_count,
        previous_follows.c.previous_count,
        (recent_follows.c.recent_count - func.coalesce(previous_follows.c.previous_count, 0)).label('increase')
    ).select_from(
        recent_follows.join(TwitterUsers, TwitterUsers.id == recent_follows.c.followed_user_id)
        .outerjoin(previous_follows, recent_follows.c.followed_user_id == previous_follows.c.followed_user_id)
    ).where(
        recent_follows.c.recent_count > func.coalesce(previous_follows.c.previous_count, 0),
        (recent_follows.c.recent_count - func.coalesce(previous_follows.c.previous_count, 0)) > 1,
        TwitterUsers.is_crypto_project == True
    ).order_by(
        text('increase DESC')
    )

    return await fetch_all(final_query)


async def get_posts_for_timeframe(
        timeframe: str = "1d"
) -> List[Dict[str, Any]]:
    hours = parse_timeframe_to_hours(
        timeframe_str=timeframe
    )
    current_time = datetime.now(pytz.timezone('Etc/GMT-3'))  # Adjust 'Etc/GMT-3' to match your specific timezone
    start_time = current_time - timedelta(hours=hours)

    query = (
        select(Posts.post).
        where(
            Posts.created_time.between(start_time, current_time)
        ).
        order_by(Posts.created_time.desc())
    )

    response = await fetch_all(query)
    return [post['post'] for post in response]


async def get_smart_followers_for_timeframe(
        start_time,
        current_time,
        twitter_user_ids: list = None,
):
    query = select(
        TwitterFollowedUsers.followed_user_id,
        func.sum(
            case(
                (TwitterFollowedUsers.created_time.between(start_time, current_time), 1),
                else_=0
            )
        ).label('smart_followers_for_timeframe')  # Count records within the time window for each user
    )

    if twitter_user_ids:
        query = query.filter(TwitterFollowedUsers.followed_user_id.in_(twitter_user_ids))

    query = query.group_by(
        TwitterFollowedUsers.followed_user_id
    )

    result = await fetch_all(query)
    # Convert to dictionary for easy lookup
    return {
        row['followed_user_id']: {
            'total_smart_followers': row['smart_followers_for_timeframe'],
            'smart_followers_for_timeframe': row['smart_followers_for_timeframe']
        }
        for row in result
    }


async def get_smart_followers_for_timeframe_small(start_time, current_time, twitter_user_ids: list = None):
    # Construct the basic query
    query = select(
        TwitterFollowedUsers.followed_user_id,
        func.count().label('smart_followers_for_timeframe')
    ).where(
        TwitterFollowedUsers.created_time.between(start_time, current_time)
    )

    # Filter by Twitter user IDs if provided
    if twitter_user_ids:
        query = query.filter(TwitterFollowedUsers.followed_user_id.in_(twitter_user_ids))

    # Group by user ID
    query = query.group_by(TwitterFollowedUsers.followed_user_id)

    result = await fetch_all(query)  # Ensure this matches how you execute and fetch results with your async DB session

    # Convert to dictionary for easy lookup
    return {
        row['followed_user_id']: row['smart_followers_for_timeframe']
        for row in result
    }


async def get_smart_mentions_for_timeframe(screen_names: list, start_time, current_time):
    # Query to get the count of smart followers mentions in the timeframe
    # Assuming screen_names, start_time, and current_time are defined
    screen_names_prefixed = [f'%@{name}%' for name in screen_names]

    # Timeframe mentions subquery
    timeframe_mentions_subq = (
        select(TwitterUsers.screen_name,
               func.count(Posts.id).label('mentions_timeframe'))
        .join(TwitterUsers, Posts.user_id == TwitterUsers.id)
        .where(and_(TwitterUsers.screen_name.in_(screen_names),
                    Posts.created_time.between(start_time, current_time),
                    or_(*[Posts.post.ilike(keyword) for keyword in screen_names_prefixed])))
        .group_by(TwitterUsers.screen_name)
        .alias('timeframe_mentions')
    )

    # Total mentions subquery
    total_mentions_subq = (
        select(TwitterUsers.screen_name,
               func.count(Posts.id).label('mentions_total'))
        .join(TwitterUsers, Posts.user_id == TwitterUsers.id)
        .where(and_(TwitterUsers.screen_name.in_(screen_names),
                    or_(*[Posts.post.ilike(keyword) for keyword in screen_names_prefixed])))
        .group_by(TwitterUsers.screen_name)
        .alias('total_mentions')
    )

    # Aliased for joining
    timeframe_mentions = aliased(timeframe_mentions_subq, name='tm')
    total_mentions = aliased(total_mentions_subq, name='tot')

    # Final query combining both
    final_query = (
        select(
            timeframe_mentions.c.screen_name,
            timeframe_mentions.c.mentions_timeframe,
            total_mentions.c.mentions_total
        ).join(
            total_mentions,
            timeframe_mentions.c.screen_name == total_mentions.c.screen_name
        )
    )
    return await fetch_all(final_query)


async def get_previous_followers_count(twitter_user_ids: list, start_time, current_time):
    subq = select(
        TwitterFollowedUsers.followed_user_id,
        TwitterFollowedUsers.followed_user_meta_data["legacy"]["followers_count"].label("followers_count"),
        func.row_number().over(
            partition_by=TwitterFollowedUsers.followed_user_id,
            order_by=TwitterFollowedUsers.created_time.asc()
            # or order_by=TwitterFollowedUsers.id.asc() if that's more appropriate
        ).label("rn")
    ).where(
        TwitterFollowedUsers.created_time.between(start_time, current_time),
        TwitterFollowedUsers.followed_user_id.in_(twitter_user_ids)
    ).subquery()

    # Then, query from this subquery, filtering to only rows with a row number of 1 (oldest per group)
    oldest_records_query = select(
        subq.c.followed_user_id.label("id"),
        subq.c.followers_count
    ).where(
        subq.c.rn == 1
    )

    # Execute the query
    oldest_records = await fetch_all(oldest_records_query)  # Adjust this line to use your async execution method

    # Convert to dictionary for easy lookup
    return {row['id']: row['followers_count'] for row in oldest_records}


async def get_base_query_for_crypto_projects_profiles(
        order_by: str,
        sort_order: str,
        page: int,
        page_size: int,
        twitter_user_ids: list = None
):
    # #################################################################################
    # Define base query
    query = (
        select(
            TwitterUsers.id,
            TwitterUsers.screen_name,
            TwitterUsers.account_info,
            TwitterUsers.created_time.label("discovered_time")
        ).filter(
            TwitterUsers.is_crypto_project == True
        )
    )
    if twitter_user_ids:
        query = query.filter(TwitterUsers.id.in_(twitter_user_ids))
    # #################################################################################
    # Sorting logic
    if order_by == "latest" or order_by == "score":
        query = query.order_by(desc(TwitterUsers.created_time)
                               if sort_order == "desc" else asc(TwitterUsers.created_time))
    elif order_by == "followers_count":
        query = query.order_by(
            desc(text("((account_info->'legacy'->>'followers_count')::integer)")) if sort_order == "desc" else
            asc(text("((account_info->'legacy'->>'followers_count')::integer)"))
        )
    elif order_by == "tweets_count":
        query = query.order_by(
            desc(text("((account_info->'legacy'->>'statuses_count')::integer)")) if sort_order == "desc" else
            asc(text("((account_info->'legacy'->>'statuses_count')::integer)"))
        )
    # #################################################################################
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    return await fetch_all(query)


async def get_trending_projects(
        dynamic_field: str,
        start_search_date: datetime,
        sort_order: str
):
    try:
        # Validate the dynamic_field
        if dynamic_field not in [
            'smart_followers_1h', 'smart_followers_4h', 'smart_followers_6h',
            'smart_followers_12h', 'smart_followers_1d', 'smart_followers_3d',
            'smart_followers_7d', 'smart_followers_14d', 'smart_followers_1m'
        ]:
            raise ValueError(f"Invalid column name: {dynamic_field}")

        query_text = text(
            f"""
            WITH RankedResults AS (
                SELECT
                    p.twitter_user_id,
                    p.{dynamic_field},
                    p.total_followers,
                    p.score,
                    p.category_tag,
                    p.total_smart_followers,
                    ROW_NUMBER() OVER (PARTITION BY p.twitter_user_id ORDER BY p.{dynamic_field} DESC) AS rn
                FROM
                    precalculateddatastore as p
                WHERE
                    p.created_time > '{start_search_date}'
                    AND p.{dynamic_field} > 1
            )
            SELECT
                twitter_user_id,
                {dynamic_field},
                total_followers,
                score,
                category_tag,
                total_smart_followers
            FROM
                RankedResults
            WHERE
                rn = 1
            ORDER BY
                {dynamic_field} {sort_order}
            """
        )
        result = await fetch_all(query_text)
        return {
            row['twitter_user_id']: {
                'smart_followers_for_timeframe': row[dynamic_field],
                'total_followers': row['total_followers'],
                'score': row['score'],
                'category_tag': row['category_tag'],
                'total_smart_followers': row['total_smart_followers']
            }
            for row in result
        }

    except Exception as error:
        logging.critical(
            f"[get_trending_projects] Error fetching trending projects: {error}"
        )
    return []


async def get_crypto_trending_projects(
        start_time: datetime,
        order_by: str = "latest",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 10,
        timeframe: str = "1d"
):
    trending_projects_for_timeframe = await get_trending_projects(
        dynamic_field=f"smart_followers_{timeframe}",
        start_search_date=start_time,
        sort_order=sort_order,
    )
    if not trending_projects_for_timeframe:
        return []
    result = await get_base_query_for_crypto_projects_profiles(
        order_by=order_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        twitter_user_ids=[row for row in trending_projects_for_timeframe]
    )
    for row in result:
        timeframe_data = trending_projects_for_timeframe.get(row['id'])
        row["total_followers"] = row["account_info"]["legacy"]["followers_count"]
        row["prev_followers_count"] = timeframe_data.get("total_followers", 0)
        row["total_smart_followers"] = timeframe_data.get("total_smart_followers", 0)
        row["smart_followers_for_timeframe"] = timeframe_data.get("smart_followers_for_timeframe", 0)
        row["score"] = timeframe_data.get("score", 0)
        row['category'] = timeframe_data.get("category_tag", "Other")

    return result


def sort_by_score(results: list, score_sort_order: str = 'desc'):
    return sorted(
        results,
        key=lambda x: x['score'],
        reverse=(score_sort_order == 'desc')
    )


async def get_crypto_projects_profiles(
        order_by: str = "latest",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 10,
        timeframe: str = "1d"
) -> List[Dict[str, Any]]:
    # Define the timeframe in which we fetch the results
    hours = parse_timeframe_to_hours(
        timeframe_str=timeframe
    )
    # Adjust 'Etc/GMT-3' to match your specific timezone
    current_time = datetime.now(pytz.timezone('Etc/GMT-3'))
    start_time = current_time - timedelta(hours=hours)
    # #################################################################################
    # Base query
    if order_by == "trending":
        return await get_crypto_trending_projects(
            start_time=start_time,
            order_by=order_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
            timeframe=timeframe
        )

    result = await get_base_query_for_crypto_projects_profiles(
        order_by=order_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )
    # Smart followers
    smart_followers = await get_smart_followers_for_timeframe(
        twitter_user_ids=[row["id"] for row in result],
        start_time=start_time,
        current_time=current_time
    )
    for row in result:
        smart_followers_dict = smart_followers.get(
            row['id'],
            {
                'total_smart_followers': 0,
                'smart_followers_for_timeframe': 0
            }
        )
        row["total_smart_followers"] = smart_followers_dict["smart_followers_for_timeframe"]
        row["smart_followers_for_timeframe"] = smart_followers_dict["smart_followers_for_timeframe"]
    # #################################################################################
    # Prev followers
    prev_followers = await get_previous_followers_count(
        twitter_user_ids=[row["id"] for row in result],
        start_time=start_time,
        current_time=current_time
    )
    for row in result:
        prev_followers_count = prev_followers.get(row['id'], 0)
        row["prev_followers_count"] = prev_followers_count or row["account_info"]["legacy"]["followers_count"]
    # #################################################################################
    # # Smart mentions
    # screen_name_mentions = await get_smart_mentions_for_timeframe(
    #     screen_names=[row["screen_name"] for row in result],
    #     start_time=start_time,
    #     current_time=current_time
    # )
    # # Construct a dictionary for quick lookup
    # screen_name_mentions_dict = {
    #     row['screen_name']: {
    #         "mentions_timeframe": row['mentions_timeframe'],
    #         "mentions_total": row['mentions_total'],
    #     }
    #     for row in screen_name_mentions
    # }
    #
    # for row in result:
    #     # Retrieve the mentions data for the screen name, defaulting to zeros if not found
    #     mentions_data = screen_name_mentions_dict.get(
    #         row['screen_name'],
    #         {"mentions_timeframe": 0, "mentions_total": 0}
    #     )
    #     # Assign the values to the current row
    #     row["smart_mentions_for_timeframe"] = mentions_data["mentions_timeframe"]
    #     row["total_smart_mentions"] = mentions_data["mentions_total"]
    # #################################################################################
    # #################################################################################
    # Score calculation
    # TODO: This has to be revisited
    for row in result:
        row["score"] = calculate_smart_followers_score(
            smart_followers_for_timeframe=row["smart_followers_for_timeframe"],
            total_smart_followers=row["total_smart_followers"],
            total_smart_followers_monitored=row["account_info"]["legacy"]["followers_count"]
        )
    # #################################################################################
    categories_with_keywords = {
        "DeFi": ["defi", "dex", "liquidity", "yield", "decentralised"],
        "AI": ["ai", "intelligence", "automation", "VR", "computing", "#AI"],
        "Infra": ["file", "storage", "cloud", "servers", "infrastructure", "infra", "devops", "mlops"],
        "RWA": ["real-world", "real", "world", "RWA"],
        "Meme": ["cat", "dog", "memes", "running", "fitness", "Memecoin", "meme", "joke", "funny"],
        "Launchpad": ["Launchpad", "Launchpads"],
        "Gaming": ["gaming", "games", "game"],
        "L1": ["L1", "Layer 1"],
        "L2": ["L2", "Layer 2"],
        "NFT": ["nft", "non fungible token", "fungible", "pictures", "images"]
    }
    # Match a category
    for row in result:
        row["category"] = match_category_with_score(
            categories_with_keywords=categories_with_keywords,
            description=row["account_info"]["legacy"]["description"]
        )
    # #################################################################################

    # Sort by score if option is selected
    if order_by == "score":
        result = sort_by_score(
            results=result,
            score_sort_order=sort_order
        )
    return result


async def get_tickers_mentions(tickers: List[str], limit: int = None):
    tickers_list_lower = [ticker.lower() for ticker in tickers]

    query = select(
        Tickers.ticker,
        Posts.created_time,
        Posts.post,
        Posts.post_id,
        Posts.profile_image,
        TwitterUsers.screen_name,
        TwitterUsers.account_info['legacy']['followers_count'].label('followers_count')
    ).select_from(
        Tickers
    ).join(
        Posts, Tickers.post_id == Posts.id
    ).join(
        TwitterUsers, Posts.user_id == TwitterUsers.id
    ).where(
        func.lower(Tickers.ticker).in_(tickers_list_lower)
    ).order_by(
        Posts.created_time.desc()
    )

    if limit:
        query = query.limit(limit)

    return await fetch_all(query)


async def get_relative_mentions_score_for_tickers(mentions: List):
    results = []
    # Cache for storing total mentions per date to avoid redundant queries
    total_mentions_cache = {}

    for mention in mentions:
        ticker = mention['ticker']
        created_time = mention['created_time']  # assuming this is a datetime object
        screen_name = mention['screen_name']
        date_str = created_time.strftime('%Y-%m-%d')  # Convert datetime to string for caching

        # Check if total mentions for this date are already cached
        if date_str not in total_mentions_cache:
            # Query to count total mentions of ALL tickers on the same day as created_time
            total_mentions_same_day_query = select(
                func.count(func.distinct(Tickers.ticker))
            ).select_from(
                Tickers
            ).join(
                Posts, Tickers.post_id == Posts.id
            ).where(
                func.date(Posts.created_time) == func.date(created_time)
            )
            total_mentions_same_day_result = await fetch_one(total_mentions_same_day_query)
            total_mentions_cache[date_str] = total_mentions_same_day_result[
                'count_1'] if total_mentions_same_day_result else 0

        total_mentions_same_day = total_mentions_cache[date_str]

        # Query to count mentions of THIS ticker on the same day as created_time
        ticker_mentions_same_day_query = select(
            func.count(Tickers.ticker)
        ).select_from(
            Tickers
        ).join(
            Posts, Tickers.post_id == Posts.id
        ).where(
            func.date(Posts.created_time) == func.date(created_time),
            Tickers.ticker == ticker
        )
        ticker_mentions_same_day_result = await fetch_one(ticker_mentions_same_day_query)
        ticker_mentions_same_day = ticker_mentions_same_day_result['count_1'] if ticker_mentions_same_day_result else 0

        # Calculate relative strength
        if total_mentions_same_day > 0:
            relative_strength = (ticker_mentions_same_day / total_mentions_same_day) * 100
        else:
            relative_strength = 0  # No mentions on this day

        results.append({
            "ticker": ticker,
            "datetime": created_time,
            "screen_name": screen_name,
            "all_tickers_mentions_for_the_day": total_mentions_same_day,
            "ticker_mentions_for_the_day": ticker_mentions_same_day,
            "relative_strength": relative_strength
        })

    return results


async def get_tickers_pnl_per_user(
        tickers: List[str],
        background_tasks,
        limit: int = None
) -> dict[Any, list[dict[str, Any]]]:
    pass


async def get_tickers_market_info(tickers: List[str]) -> List[Dict[str, Any]]:
    # Define a window function for the latest TickerMarketData entries
    latest_price_win = func.rank().over(partition_by=TickerMarketData.ticker,
                                        order_by=TickerMarketData.created_time.desc()).label('rnk')

    # Subquery for TickerMarketData with ranking
    tmd_subq = select(
        TickerMarketData.ticker,
        TickerMarketData.created_time.label('market_data_last_update'),
        TickerMarketData.price,
        latest_price_win
    ).subquery()

    # Main query that joins Tickers, Posts, and the subquery for TickerMarketData
    query = select(
        Tickers.ticker,
        func.min(Posts.created_time).label('first_mention'),
        tmd_subq.c.market_data_last_update,
        tmd_subq.c.price
    ).join(
        Posts, Tickers.post_id == Posts.id
    ).join(
        tmd_subq, and_(Tickers.ticker == tmd_subq.c.ticker, tmd_subq.c.rnk == 1), isouter=True
    ).where(
        Tickers.ticker.in_(tickers)
    ).group_by(
        Tickers.ticker, tmd_subq.c.market_data_last_update, tmd_subq.c.price
    )

    result = await fetch_all(query)

    # Mapping the result to a dictionary for each ticker
    tickers_info = [
        {
            'ticker': row['ticker'],
            'first_mention': row['first_mention'],
            'market_data_last_update': row['market_data_last_update'],
            'price': row['price']
        }
        for row in result
    ]

    return tickers_info


async def get_monitored_twitter_users(
        skip: int = 0,
        limit: int = 50
) -> list[dict[str, Any]]:
    select_query = (
        select(TwitterUsers).
        where(TwitterUsers.monitor_following == True).
        order_by(TwitterUsers.id.desc()).
        offset(skip).
        limit(limit)
    )
    return await fetch_all(select_query)


async def get_suggested_twitter_users(
        skip: int = 0,
        limit: int = 50
) -> list[dict[str, Any]]:
    # Subquery to get distinct suggested_user_id from TwitterSuggestedUsers
    subquery = select(distinct(TwitterSuggestedUsers.suggested_user_id))
    # Main query to get TwitterUsers where id is in the subquery
    query = select(TwitterUsers).where(TwitterUsers.id.in_(subquery))
    # Apply offset and limit
    query = query.offset(skip).limit(limit)
    return await fetch_all(query)


async def get_followed_twitter_users(skip: int = 0, limit: int = 50) -> list[dict[str, Any]]:
    select_query = (
        select(TwitterFollowedUsers).
        order_by(TwitterFollowedUsers.id.desc()).
        offset(skip).
        limit(limit)
    )
    return await fetch_all(select_query)


async def get_keyword_mentions_stats_per_day(
        keywords: List[str]
) -> List[Dict[str, Any]]:
    # Query to get the count of posts per day that mention any of the keywords
    query = (
        select(
            func.date(Posts.created_time).label('date'),
            func.count(Posts.id).label('mentions')
        ).
        where(
            or_(*[Posts.post.ilike(f'%{keyword}%') for keyword in keywords])
        ).
        group_by(func.date(Posts.created_time)).
        order_by(func.date(Posts.created_time))
    )
    return await fetch_all(query)


async def get_twitter_posts(
        user: str = None,
        search_keywords: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 50
) -> List[Dict[str, Any]]:
    # Join the Posts and TwitterUsers tables
    select_query = select(Posts).select_from(
        join(Posts, TwitterUsers, Posts.user_id == TwitterUsers.id)
    ).order_by(Posts.id.desc())

    if user is not None:
        # Filter by user name
        select_query = select_query.where(TwitterUsers.screen_name == user)

    if search_keywords is not None and len(search_keywords) > 0:
        keyword_conditions = [Posts.post.ilike(f'%{keyword}%') for keyword in search_keywords]
        select_query = select_query.where(or_(*keyword_conditions))

    # Add pagination
    select_query = select_query.offset(skip).limit(limit)

    # Execute the query and return the results
    return await fetch_all(select_query)


async def get_twitter_tickers(
        user: Optional[str] = None,  # Allow filtering by user
        ticker: Optional[str] = None,  # Allow filtering by ticker
        skip: int = 0,
        limit: int = 50
) -> List[Dict[str, Any]]:
    # Join the Tickers, Posts and TwitterUsers tables
    select_query = select(Tickers, TwitterUsers.screen_name).select_from(
        join(Tickers, Posts, Tickers.post_id == Posts.id).
        join(TwitterUsers, Posts.user_id == TwitterUsers.id)
    ).order_by(Tickers.id.desc())

    if user is not None:
        # Filter by user name
        select_query = select_query.where(TwitterUsers.screen_name == user)

    if ticker is not None:
        select_query = select_query.where(Tickers.ticker == ticker)

    # Apply pagination
    select_query = select_query.offset(skip).limit(limit)

    # Execute the query and return the results
    return await fetch_all(select_query)


async def get_most_mentioned_tickers(screen_names: List[str], limit: int) -> Dict[str, Any]:
    screen_name_tickers = {}
    for screen_name in screen_names:
        most_mentioned_tickers_query = (
            select(
                Tickers.ticker,
                func.count(Tickers.ticker).label('count'),
                func.min(Posts.created_time).label('first_mention')
            ).
            select_from(
                join(Tickers, Posts, Tickers.post_id == Posts.id).
                join(TwitterUsers, Posts.user_id == TwitterUsers.id)
            ).
            where(
                TwitterUsers.screen_name == screen_name
            ).
            group_by(
                Tickers.ticker
            ).
            order_by(
                desc('count')
            )
        )

        if limit is not None:
            most_mentioned_tickers_query = most_mentioned_tickers_query.limit(limit)

        screen_name_tickers[screen_name] = await fetch_all(most_mentioned_tickers_query)

    return screen_name_tickers


async def get_all_tickers_for_screen_names(
        screen_names: List[str]
) -> Dict[str, List[Dict[str, Any]]]:
    tickers_query = (
        select(
            Tickers.ticker,
            Posts.created_time,
            TwitterUsers.screen_name
        ).
        select_from(
            join(Tickers, Posts, Tickers.post_id == Posts.id).
            join(TwitterUsers, Posts.user_id == TwitterUsers.id)
        ).
        where(TwitterUsers.screen_name.in_(screen_names))
    )

    rows = await fetch_all(tickers_query)

    screen_name_tickers = {}
    for row in rows:
        screen_name = row['screen_name']
        if screen_name not in screen_name_tickers:
            screen_name_tickers[screen_name] = []

        screen_name_tickers[screen_name].append({
            'ticker': row['ticker'],
            'created_time': row['created_time']
        })

    return screen_name_tickers


async def get_tickers_mentioned_by_users(
        screen_names: List[str],
        most_mentioned: bool = False,
        all_ticker_mentions: bool = False,
        limit: int = None
) -> Dict[str, List[Dict[str, Any]]]:
    if all_ticker_mentions:
        return await get_all_tickers_for_screen_names(
            screen_names=screen_names
        )
    elif most_mentioned:
        return await get_most_mentioned_tickers(
            screen_names=screen_names,
            limit=limit
        )

    tickers = (
        select(
            Tickers.ticker.label('ticker'),
            func.min(Posts.created_time).label('first_mention'),
            func.max(TickerMarketData.created_time).label('market_data_last_update'),
            TwitterUsers.screen_name.label('screen_name')
        ).
        select_from(
            join(Tickers, Posts, Tickers.post_id == Posts.id).
            join(TwitterUsers, Posts.user_id == TwitterUsers.id).
            join(TickerMarketData, Tickers.ticker == TickerMarketData.ticker, isouter=True)
        ).
        where(TwitterUsers.screen_name.in_(screen_names))
    )

    tickers = tickers.group_by(
        Tickers.ticker,
        Posts.created_time,
        TwitterUsers.screen_name
    ).order_by(Posts.created_time.desc())

    if limit is not None:
        tickers = tickers.limit(limit)

    rows = await fetch_all(tickers)

    screen_name_tickers = {}
    for row in rows:
        screen_name = row['screen_name']
        if screen_name not in screen_name_tickers:
            screen_name_tickers[screen_name] = []

        screen_name_tickers[screen_name].append({
            'ticker': row['ticker'],
            'first_mention': row['first_mention'],
            'market_data_last_update': row.get('market_data_last_update')
        })

    return screen_name_tickers


async def calculate_pnl_for_tickers(user_mentions: Dict) -> dict[Any, list[dict[str, Any]]]:
    pnl_data = {}
    for screen_name, tickers in user_mentions.items():
        ticker_symbols = [ticker['ticker'] for ticker in tickers]
        first_mentions = {ticker['ticker']: ticker['first_mention'] for ticker in tickers}

        # Fetch records after the first mention for each ticker
        potential_first_records = await fetch_all(
            select(
                TickerMarketData.ticker,
                TickerMarketData.created_time,
                TickerMarketData.price
            ).filter(
                TickerMarketData.ticker.in_(ticker_symbols)
            ).order_by(
                TickerMarketData.ticker,
            )
        )

        # Process these records to find the one closest to 1 hour after first mention for each ticker
        first_prices = {}
        for record in potential_first_records:
            ticker = record['ticker']
            market_data_created_time = record['created_time']
            price = record['price']
            user_mention_time = first_mentions[ticker]

            market_data_created_time = market_data_created_time.astimezone(pytz.utc)
            user_mention_time = user_mention_time.astimezone(pytz.utc)

            time_difference = abs(market_data_created_time - user_mention_time)
            if time_difference <= timedelta(hours=4):
                first_prices[ticker] = {
                    'market_data_created_time': market_data_created_time,
                    "user_data_created_time": user_mention_time,
                    'price': price
                }
                logging.debug("======================")
                logging.debug(f"Ticker: {ticker}")
                logging.debug(f"Created time: {market_data_created_time}")
                logging.debug(f"Price: {price}")
                logging.debug(f"User: {screen_name} has mentioned {ticker} at: {user_mention_time}")
                logging.debug("======================")

        if not first_prices:
            continue

        last_prices_query = select(
            TickerMarketData.ticker,
            func.max(TickerMarketData.created_time).label('max_time')
        ).where(
            TickerMarketData.ticker.in_(ticker_symbols)
        ).group_by(
            TickerMarketData.ticker
        ).subquery()

        # Join this subquery with the original TickerMarketData to get the prices
        # corresponding to the max_time for each ticker
        last_prices = await fetch_all(
            select(
                TickerMarketData.ticker,
                TickerMarketData.price,
                last_prices_query.c.max_time
            ).join(
                last_prices_query, and_(
                    TickerMarketData.ticker == last_prices_query.c.ticker,
                    TickerMarketData.created_time == last_prices_query.c.max_time
                )
            )
        )

        # Calculate PnL for each ticker
        for ticker, details in first_prices.items():
            first_price = details['price']
            last_price = next(
                (
                    item for item in last_prices
                    if item['ticker'] == ticker and item['max_time'] >= details['user_data_created_time']
                ), {}
            ).get('price', None)
            if last_price:
                pnl = (last_price - first_price) / first_price * 100
                if screen_name not in pnl_data:
                    pnl_data[screen_name] = []
                pnl_data[screen_name].append(
                    {
                        'ticker': ticker,
                        'current_price': last_price,
                        'first_mention_price': first_price,
                        'fist_mention_at': details['user_data_created_time'],
                        'pnl': pnl
                    }
                )

    return pnl_data


async def get_screen_names_pnl(
        screen_names: List[str],
        background_tasks,
        limit: int = None
) -> dict[Any, list[dict[str, Any]]]:
    user_mentions = await get_tickers_mentioned_by_users(
        screen_names=screen_names,
        limit=limit
    )
    if not user_mentions:
        return {}

    # Parsing the environment variable for market data update interval
    update_interval_hours = int(os.getenv('MARKET_DATA_UPDATE_INTERVAL', 4))

    # Check if the last update time for the tickers is more than the update interval ago
    # we include tickers that have never been updated
    current_time = datetime.now(timezone.utc) - timedelta(hours=update_interval_hours)
    tickers_to_update = [
        ticker['ticker'] for screen_name, tickers in user_mentions.items()
        for ticker in tickers
        if
        (
                ticker['market_data_last_update'] is None
                or
                ticker['market_data_last_update'] < current_time
        )
    ] if user_mentions else []

    if tickers_to_update:
        logging.critical(
            f"Updating market data for tickers: {tickers_to_update} for users: {screen_names}"
        )
        # Send the tickers to the background task to update the market data
        background_tasks.add_task(update_market_data_in_a_thread, tickers_to_update)

    return await calculate_pnl_for_tickers(
        user_mentions=user_mentions
    )


async def get_user_profiles_info(
        screen_names: List[str],
) -> Dict:
    select_query = select(
        TwitterUsers.screen_name,
        TwitterUsers.account_info,
        TwitterUsers.updated_at.label('updated_at'),
    ).where(
        TwitterUsers.screen_name.in_(screen_names)
    )

    account_info = await fetch_all(select_query)
    return {
        account['screen_name']: {
            # Use .get() to safely access 'url' and provide an empty dictionary as a default
            'urls': [url['expanded_url'] for url in
                     account['account_info']['legacy']['entities'].get('url', {}).get('urls', [])],
            'followers_count': account['account_info']['legacy'].get('followers_count', 0),
            'friends_count': account['account_info']['legacy'].get('friends_count', 0),
            'location': account['account_info']['legacy'].get('location', ''),
            'profile_image': account['account_info']['legacy'].get('profile_image_url_https', ''),
            'updated_at': account.get('updated_at', None)
        } for account in account_info if account.get('account_info')
    } if account_info else None


def get_all_tickers_for_which_we_know_the_twitter_handler(
        page: int,
        page_size: int
):
    # Calculate offset based on page number and page size
    offset = (page - 1) * page_size

    market_cap_usd = cast(
        func.coalesce(
            func.json_extract_path_text(CoingeckoMetaData.meta_data, 'market_data', 'market_cap', 'usd'), '0'
        ),
        Float
    ).label("market_cap_usd")

    fdv_usd = cast(
        func.coalesce(
            func.json_extract_path_text(CoingeckoMetaData.meta_data, 'fully_diluted_valuation', 'usd'), '0'
        ),
        Float
    ).label("fdv_usd")

    # Define the query with conditional extraction and ordering
    query = select(
        CoingeckoMetaData.ticker,
        CoingeckoMetaData.twitter_username,
        market_cap_usd,
        fdv_usd
    ).where(
        CoingeckoMetaData.ticker.is_not(None),
        CoingeckoMetaData.twitter_username.is_not(None)
    )

    # Define the ordering condition
    ordering_condition = case(
        (market_cap_usd != 0, market_cap_usd),
        else_=fdv_usd
    ).label("ordering_condition")

    query = query.order_by(ordering_condition.desc())

    # Apply pagination
    query = query.offset(offset).limit(page_size)

    # Execute the combined query using the session and fetch all results
    return fetch_all(query)
