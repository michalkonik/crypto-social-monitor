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


