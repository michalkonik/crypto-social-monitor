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


async def get_activity():
    """
    Get CT activity
    :return:
    """
    # posts_activity = await get_posts_activity()
    overview_data = await get_overview_data(
        timeframe="1m"
    )
    return {
        "posts_activity": json.loads(overview_data['posts_activity']),
        "followings_activity": json.loads(overview_data['follows_activity'])
    }


async def get_user_overview(
        start_time: datetime,
        screen_name: str = None,
        twitter_user_id: int = None,
):
    """
    Get an overview of a user's information.
    :param twitter_user_id:
    :param start_time:
    :param screen_name: Get an overview of a user's information.
    :return:
    """

    response = {
        "status": False,
        "data": ""
    }

    twitter_user_query = select(
        TwitterUsers.id,
        TwitterUsers.screen_name,
        TwitterUsers.account_info
    )

    if screen_name:
        twitter_user_query = twitter_user_query.filter(
            func.lower(TwitterUsers.screen_name) == str(screen_name).lower()
        )
    elif twitter_user_id:
        twitter_user_query = twitter_user_query.filter(
            TwitterUsers.id == twitter_user_id
        )

    twitter_user = await fetch_one(twitter_user_query)

    if not twitter_user:
        response["data"] = "User not found."
        return response

    # Get the Twitter user ID
    twitter_user_id = twitter_user["id"]

    # Fetch the Twitter user information for the specified timeframe
    timeframe_user_data_query = (
        select(
            PreCalculatedDataStore.total_followers,
            PreCalculatedDataStore.total_smart_followers,
            PreCalculatedDataStore.score,
            PreCalculatedDataStore.potential_ticker,
            PreCalculatedDataStore.created_time,
            PreCalculatedDataStore.category_tag.label("category")
        )
        .filter(
            and_(
                PreCalculatedDataStore.twitter_user_id == twitter_user_id,
                PreCalculatedDataStore.created_time <= start_time
            )
        )
        .order_by(PreCalculatedDataStore.created_time.desc())
        .limit(1)
    )
    timeframe_user_data = await fetch_one(timeframe_user_data_query) or []

    # Fetch the current "total_smart_followers"
    current_user_data_query = (
        select(
            PreCalculatedDataStore.total_followers,
            PreCalculatedDataStore.total_smart_followers,
            PreCalculatedDataStore.score,
            PreCalculatedDataStore.potential_ticker,
            PreCalculatedDataStore.created_time,
            PreCalculatedDataStore.category_tag.label("category")
        )
        .filter(PreCalculatedDataStore.twitter_user_id == twitter_user_id)
        .order_by(PreCalculatedDataStore.created_time.desc())
        .limit(1)
    )
    current_user_data = await fetch_one(current_user_data_query)

    # Twitter user smart followers plot since discovery
    smart_followers_plot_query = (
        select(
            func.min(TwitterFollowedUsers.created_time).label('first_followed_time'),
            func.count().label('count')
        ).filter(
            TwitterFollowedUsers.followed_user_id == twitter_user_id
        ).group_by(
            func.date(TwitterFollowedUsers.created_time)
        ).order_by('first_followed_time')
    )
    smart_followers_plot = await fetch_all(smart_followers_plot_query)

    # Ticker smart mentions plot since discovery if a potential ticker is found
    ticker_mentions_plot = []
    project_ticker = (
            (current_user_data and current_user_data["potential_ticker"])
            or (timeframe_user_data and timeframe_user_data["potential_ticker"])
            or None
    )
    if project_ticker:
        ticker_mentions_plot_query = (
            select(
                func.min(Tickers.created_time).label('first_followed_time'),
                func.count().label('count')
            ).filter(
                or_(
                    func.lower(Tickers.ticker) == str(project_ticker).lower(),
                    func.lower(Tickers.ticker) == str(f"${project_ticker}").lower()
                )
            ).group_by(
                func.date(Tickers.created_time)
            ).order_by('first_followed_time')
        )
        ticker_mentions_plot = await fetch_all(ticker_mentions_plot_query)

    response["status"] = True
    response["data"] = {
        "twitter_user": twitter_user,
        "timeframe_user_data": timeframe_user_data,
        "current_user_data": current_user_data,
        "smart_followers_plot": smart_followers_plot,
        "ticker_mentions_plot": ticker_mentions_plot
    }

    # TODO:
    # Plot of sentiment over time
    # Plot of twitter project name mentions over time
    # Plot of Mind share index strength over time

    # - Get top KOLs following this user ( by followers count ) ?

    return response


async def get_sentiment_overview():
    """
    Get sentiment overview
    :return:
    """
    query = (
        select(
            func.date(Posts.created_time).label('date'),
            func.sum(
                case(
                    (PostLabels.sentiment_label == 'positive', 1),
                    (PostLabels.sentiment_label == 'negative', -1),
                    else_=0
                )
            ).label('net_sentiment')
        )
        .select_from(PostLabels)  # Explicitly specify to start from PostLabels
        .join(Posts, PostLabels.post_id == Posts.id)  # Use correct join syntax
        .filter(PostLabels.sentiment_label != 'neutral')
        .group_by(func.date(Posts.created_time))
        .order_by(func.date(Posts.created_time).desc())
    )
    return await fetch_all(query)


async def get_sentiment_overview_with_smoothening():
    """
    Get sentiment overview with smoothening
    :return:
    """
    query_text = text("""
    WITH SentimentAnalysis AS (
        SELECT
            DATE(p.created_time) AS date,
            100.0 * (SUM(CASE WHEN pl.sentiment_label = 'positive' THEN 1 ELSE 0 END) - 
                     SUM(CASE WHEN pl.sentiment_label = 'negative' THEN 1 ELSE 0 END)) / 
            COUNT(pl.sentiment_label) * LOG(1 + COUNT(t.id)) AS raw_sentiment
        FROM 
            PostLabels AS pl
        INNER JOIN 
            POSTS AS p ON pl.post_id = p.id
        LEFT JOIN 
            Tickers AS t ON p.id = t.post_id
        GROUP BY 
            DATE(p.created_time)
    ),
    SmoothedSentiment AS (
        SELECT
            date,
            AVG(raw_sentiment) OVER (
                ORDER BY date
                ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
            ) AS smoothed_percent
        FROM 
            SentimentAnalysis
    ),
    RateOfChange AS (
        SELECT
            date,
            smoothed_percent,
            LAG(smoothed_percent, 1) OVER (ORDER BY date) AS previous_smoothed_percent,
            (smoothed_percent - LAG(smoothed_percent, 1) OVER (ORDER BY date)) /
            NULLIF(LAG(smoothed_percent, 1) OVER (ORDER BY date), 0) * 100 AS percent_change
        FROM 
            SmoothedSentiment
    ),
    DynamicThreshold AS (
        SELECT
            date,
            smoothed_percent,
            percent_change,
            STDDEV(percent_change) OVER (
                ORDER BY date
                ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
            ) * 2 AS threshold
        FROM 
            RateOfChange
    ),
    TrendDetection AS (
        SELECT
            date,
            smoothed_percent,
            percent_change,
            threshold,
            CASE
                WHEN LAG(percent_change, 1) OVER (ORDER BY date) < 0 AND
                     LAG(percent_change, 2) OVER (ORDER BY date) < 0 AND
                     LAG(percent_change, 3) OVER (ORDER BY date) < 0 AND
                     percent_change < 0 THEN 'DOWN'
                WHEN LAG(percent_change, 1) OVER (ORDER BY date) > 0 AND
                     LAG(percent_change, 2) OVER (ORDER BY date) > 0 AND
                     LAG(percent_change, 3) OVER (ORDER BY date) > 0 AND
                     percent_change > 0 THEN 'UP'
                ELSE 'NO TREND'
            END AS trend,
            CASE 
                WHEN ABS(percent_change) >= threshold THEN 'Sharp Change'
                ELSE 'Normal'
            END AS change_flag
        FROM 
            DynamicThreshold
    ),
    ActionDetermination AS (
        SELECT
            *,
            MAX(CASE WHEN trend IN ('UP', 'DOWN') AND change_flag = 'Sharp Change' THEN date ELSE NULL END) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS last_significant_date
        FROM 
            TrendDetection
    ),
    LastSignificantActions AS (
        SELECT
            A.date,
            A.smoothed_percent,
            A.percent_change,
            A.threshold,
            A.trend,
            A.change_flag,
            B.trend AS prev_trend,
            B.change_flag AS prev_change_flag
        FROM 
            ActionDetermination A
        LEFT JOIN 
            ActionDetermination B ON A.last_significant_date = B.date
    ),
    FinalActions AS (
        SELECT
            date,
            smoothed_percent,
            percent_change,
            threshold,
            trend,
            change_flag,
            CASE 
                WHEN trend = 'UP' AND change_flag = 'Sharp Change' AND prev_trend = 'DOWN' THEN 'SELL'
                WHEN trend = 'UP' AND change_flag = 'Sharp Change' AND prev_trend = 'UP' THEN 'BUY'
                WHEN trend = 'DOWN' AND change_flag = 'Sharp Change' AND prev_trend = 'UP' THEN 'LOAD'
                WHEN trend = 'DOWN' AND change_flag = 'Sharp Change' AND prev_trend = 'DOWN' THEN 'PULLBACK'
                WHEN trend = 'NO TREND' AND change_flag = 'Normal' THEN 'HOLD'
                ELSE 'DO NOTHING'
            END AS action
        FROM 
            LastSignificantActions
    )
    SELECT
        date,
        percent_change,
        threshold
    FROM 
        FinalActions
    ORDER BY 
        date DESC;

    """)
    return await fetch_all(query_text)
