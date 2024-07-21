"""
Service is used for fetching narratives
"""
from typing import Optional

from sqlalchemy import (
    select,
    or_,
    distinct,
    func,
    join,
    and_,
    desc,
    asc,
    text,
    cast,
    Float,
)

from src.database import (
    fetch_one,
    fetch_all
)

from src.twitter.service import (
    TwitterUsers
)

from src.twitter.service_schemas.narratives.schema import (
    Narratives,
    TwitterUsersNarrativesMap
)


async def get_narratives():
    """
    Fetch all narratives
    """
    query = select(Narratives)
    return await fetch_all(query)


async def get_screen_names_narratives_map(
        screen_names: list[str],
        narrative_names: list[str] = None,
        order_by: str = "created_time",
        sort_order: str = "desc"
):
    """
    Fetch narrative map for screen names. Optionally we can filter by narrative names
    """
    query = select(
        TwitterUsers.screen_name,
        TwitterUsers.account_info,
        TwitterUsersNarrativesMap.score,
        TwitterUsersNarrativesMap.custom_score,
        TwitterUsersNarrativesMap.created_time
    ).join(
        TwitterUsers,
        TwitterUsers.id == TwitterUsersNarrativesMap.twitter_user_id
    )

    if screen_names:
        query = query.where(
            TwitterUsers.screen_name.in_(screen_names)
        )

    if narrative_names:
        query = query.add_columns(Narratives.narrative_name).join(
            Narratives,
            Narratives.id == TwitterUsersNarrativesMap.narrative_id
        ).where(
            Narratives.narrative_name.in_(narrative_names)
        )

    if sort_order == "asc":
        query = query.order_by(
            asc(
                getattr(
                    TwitterUsersNarrativesMap,
                    order_by
                )
            )
        )
    else:
        query = query.order_by(
            desc(
                getattr(
                    TwitterUsersNarrativesMap,
                    order_by
                )
            )
        )

    return await fetch_all(query)
