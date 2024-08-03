"""
Service is used global search functionality
"""
from sqlalchemy import (
    select
)

from src.database import (
    fetch_all
)

from src.twitter.service import (
    TwitterUsers,
    PreCalculatedDataStore
)


async def search_project(
        search_term: str,
        limit: int
):
    """
    Search for a project by name or ticker.
    First, check the PrecalculatedDataStore for ticker matches,
    if no exact matches are found, then check the TwitterUsers by screen names.
    """
    # Remove '%' wildcards for exact matching in sorting later
    search_term_wildcard = f"%{search_term}%"

    # First check for potential tickers and collect matching Twitter user IDs
    ticker_query = (select(
        PreCalculatedDataStore.potential_ticker,
        PreCalculatedDataStore.twitter_user_id,
        PreCalculatedDataStore.score,
        PreCalculatedDataStore.custom_score,
        PreCalculatedDataStore.total_followers
    ).filter(
        PreCalculatedDataStore.potential_ticker.ilike(search_term_wildcard)
    ).order_by(
        PreCalculatedDataStore.score.desc()
    ).distinct().limit(limit))

    ticker_matches = await fetch_all(ticker_query)

    # If there are matches based on tickers, find corresponding Twitter user info
    if ticker_matches:
        user_ids = list(set([match["twitter_user_id"] for match in ticker_matches]))
        user_query = select(
            TwitterUsers.screen_name,
            TwitterUsers.id
        ).filter(TwitterUsers.id.in_(user_ids))

        user_results = await fetch_all(user_query)
        if not user_results:
            return []
        results = []
        ticker_info_map = {ticker["twitter_user_id"]: ticker for ticker in ticker_matches}
        for user in user_results:
            user.update({
                "potential_ticker": ticker_info_map[user["id"]]["potential_ticker"],
                "score": ticker_info_map[user["id"]]["score"],
                "custom_score": ticker_info_map[user["id"]]["custom_score"],
                "total_followers": ticker_info_map[user["id"]]["total_followers"]
            })
            results.append(user)
        # Sort by ticker presence, exact match, and then by score
        results = sorted(
            results,
            key=lambda x: (
                x.get("potential_ticker") is not None,  # True for non-null tickers, False for null
                str(x.get("potential_ticker", "")).lower() == str(search_term).lower(),
                str(x["screen_name"]).lower() == str(search_term).lower(),
                x.get("score", float('-inf'))
            ),
            reverse=True
        )
        return results

    # If no ticker matches, search for user screen names
    else:
        user_query = select(
            TwitterUsers.screen_name,
            TwitterUsers.id
        ).filter(
            TwitterUsers.screen_name.ilike(search_term_wildcard)
        ).limit(limit)

        user_results = await fetch_all(user_query)

        if user_results:
            user_ids = list(set([user["id"] for user in user_results]))
            ticker_query = select(
                PreCalculatedDataStore.potential_ticker,
                PreCalculatedDataStore.twitter_user_id,
                PreCalculatedDataStore.score,
                PreCalculatedDataStore.custom_score,
                PreCalculatedDataStore.total_followers
            ).filter(
                PreCalculatedDataStore.twitter_user_id.in_(user_ids)
            ).distinct()

            ticker_results = await fetch_all(ticker_query)
            ticker_map = {ticker["twitter_user_id"]: ticker for ticker in ticker_results}

            # Map tickers to users
            for user in user_results:
                ticker = ticker_map.get(user["id"])
                if ticker:
                    user.update({
                        "potential_ticker": ticker["potential_ticker"],
                        "score": ticker["score"],
                        "custom_score": ticker["custom_score"],
                        "total_followers": ticker["total_followers"]
                    })

            # Now sort by exact match on screen name and then by score
            user_results = sorted(
                user_results,
                key=lambda x: (
                    x.get("potential_ticker") is not None,  # True for non-null tickers, False for null
                    str(x.get("potential_ticker", "")).lower() == str(search_term).lower(),
                    str(x["screen_name"]).lower() == str(search_term).lower(),
                    x.get("score", float('-inf'))
                ),
                reverse=True
            )
            return user_results

        return []
