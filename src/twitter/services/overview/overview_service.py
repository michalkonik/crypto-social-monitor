"""
Twitter user overview page.
This is an individual user's page that shows all the information we have on them.
"""

import json

from datetime import (
    datetime,
    timedelta
)

from sqlalchemy import (
    select,
    func,
    and_,
    or_,
    case,
    text
)

from sqlalchemy.orm import (
    aliased
)

from src.database import (
    fetch_one,
    fetch_all
)

from src.twitter.schemas import (
    TwitterUsers,
    TwitterFollowedUsers,
    Tickers,
    PreCalculatedDataStore,
    Posts,
    PostLabels
)

from src.twitter.schemas import (
    PreCalculatedOverviewData1h,
    PreCalculatedOverviewData4h,
    PreCalculatedOverviewData6h,
    PreCalculatedOverviewData12h,
    PreCalculatedOverviewData1d,
    PreCalculatedOverviewData3d,
    PreCalculatedOverviewData7d,
    PreCalculatedOverviewData14d,
    PreCalculatedOverviewData1m
)


async def get_posts_activity():
    """
    Fetch daily posts activity with comparison to the previous day.
    !NOTE!: We have a hard-coded date here. This should be changed to a dynamic date.
    """
    # Define the CTE for daily posts count
    daily_posts = select(
        func.date(Posts.post_time).label('post_date'),
        func.count().label('posts')
    ).group_by(func.date(Posts.post_time)).cte('daily_posts')

    # Create aliases for the CTE
    dp1 = aliased(daily_posts, name='dp1')
    dp2 = aliased(daily_posts, name='dp2')

    # Define the CTE for comparison of posts
    posts_comparison = select(
        dp1.c.post_date,
        dp1.c.posts.label('posts_today'),
        func.coalesce(dp2.c.posts, 0).label('posts_yesterday'),
        case(
            (func.coalesce(dp2.c.posts, 0) > 0,
             (dp1.c.posts - func.coalesce(dp2.c.posts, 0)) * 100.0 / func.coalesce(dp2.c.posts, 1)),
            else_=100.0
        ).label('percent_increase')
    ).select_from(
        dp1.join(dp2, dp1.c.post_date == func.date(dp2.c.post_date + timedelta(days=1)), isouter=True)
    ).cte('posts_comparison')

    # Final SELECT query using the CTE directly
    final_query = (select(
        posts_comparison.c.post_date,
        posts_comparison.c.posts_today,
        posts_comparison.c.posts_yesterday,
        posts_comparison.c.percent_increase
    ).where(
        posts_comparison.c.post_date >= func.date('2023-12-22')
    ).order_by(posts_comparison.c.post_date.desc()))

    return await fetch_all(final_query)


def get_precalculated_overview_database_model(timeframe: str):
    """
    Get the precalculated overview database model for the specified timeframe.
    :param timeframe:
    :return:
    """
    if timeframe == "1h":
        return PreCalculatedOverviewData1h
    elif timeframe == "4h":
        return PreCalculatedOverviewData4h
    elif timeframe == "6h":
        return PreCalculatedOverviewData6h
    elif timeframe == "12h":
        return PreCalculatedOverviewData12h
    elif timeframe == "1d":
        return PreCalculatedOverviewData1d
    elif timeframe == "3d":
        return PreCalculatedOverviewData3d
    elif timeframe == "7d":
        return PreCalculatedOverviewData7d
    elif timeframe == "14d":
        return PreCalculatedOverviewData14d
    elif timeframe == "1m":
        return PreCalculatedOverviewData1m
    return None


async def get_precalculated_overview_data_for_timeframe(
        timeframe: str
):
    database_model = get_precalculated_overview_database_model(
        timeframe=timeframe
    )
    if not database_model:
        return []
    query = select(
        database_model.hourly_changes_follows,
        database_model.hourly_changes_ticker_mentions,
        database_model.word_cloud,
        database_model.follows_activity,
        database_model.posts_activity,
        database_model.sentiment_activity,
        database_model.projects_mind_share_activity,
        database_model.category_mind_share_activity
    ).order_by(database_model.created_time.desc()).limit(1)
    return await fetch_one(query)


async def get_followings_activity():
    """
    Get CT followings activity
    """
    # Define the CTE for daily followers count
    daily_follows = select(
        func.date(TwitterFollowedUsers.created_time).label('follow_date'),
        func.count().label('follows')
    ).group_by(func.date(TwitterFollowedUsers.created_time)).cte('DailyFollows')

    # Create an aliased version for joining
    df1 = aliased(daily_follows, name='df1')
    df2 = aliased(daily_follows, name='df2')

    # Define the CTE for comparison of follows
    follows_comparison = select(
        df1.c.follow_date,
        df1.c.follows.label('follows_today'),
        func.coalesce(df2.c.follows, 0).label('follows_yesterday'),
        case(
            (func.coalesce(df2.c.follows, 0) > 0,
             (df1.c.follows - func.coalesce(df2.c.follows, 0)) * 100.0 / func.coalesce(df2.c.follows, 1)),
            else_=100.0
        ).label('percent_increase')
    ).select_from(
        df1.join(df2, df1.c.follow_date == func.date(df2.c.follow_date + timedelta(days=1)), isouter=True)
    ).cte('FollowsComparison')

    # Final SELECT query
    final_query = select(
        follows_comparison.c.follow_date,
        follows_comparison.c.follows_today,
        follows_comparison.c.follows_yesterday,
        follows_comparison.c.percent_increase
    ).order_by(follows_comparison.c.follow_date.desc())

    return await fetch_all(final_query)


async def get_overview_data(timeframe: str):
    """
    Overview page data
    :param timeframe: 
    :return: 
    """
    return await get_precalculated_overview_data_for_timeframe(
        timeframe=timeframe
    )


