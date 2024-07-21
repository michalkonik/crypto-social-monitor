"""
Service is used for fetching KOLs
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

from src.twitter.schemas import (
    TwitterUsers,
    TwitterFollowedUsers
)

from src.twitter.service_schemas.kol.schema import (
    TwitterUserClusters,
    TwitterUserClustersProfiles
)


async def get_kol_clusters(include_cluster_stats: bool = False):
    """
    Fetch all kol categories excluding "koryo_cluster"
    """

    KORYO_CLUSTER_NAME = 'koryo_cluster'

    if not include_cluster_stats:
        query = select(TwitterUserClusters).filter(TwitterUserClusters.cluster_name != KORYO_CLUSTER_NAME)
        return await fetch_all(query)

    # Aggregate cluster stats
    query = select(
        TwitterUserClustersProfiles.twitter_user_id,
        TwitterUserClustersProfiles.cluster_id,
        TwitterUserClusters.cluster_name
    ).join(
        TwitterUserClusters,
        TwitterUserClustersProfiles.cluster_id == TwitterUserClusters.id
    ).group_by(
        TwitterUserClustersProfiles.cluster_id,
        TwitterUserClustersProfiles.twitter_user_id,
        TwitterUserClusters.cluster_name
    )

    kol_profiles = await fetch_all(query)

    # make a cluster map id to name
    cluster_map = {}
    for kol_profile in kol_profiles:
        if kol_profile["cluster_id"] not in cluster_map:
            cluster_map[str(kol_profile["cluster_id"])] = kol_profile["cluster_name"]

    if not kol_profiles:
        return {
            "kol_profiles": [],
            "cluster_stats": []
        }

    profile_ids = [
        kol_profile["twitter_user_id"] for kol_profile in kol_profiles
    ]

    follow_counts_query = select(
        TwitterUserClustersProfiles.cluster_id,
        TwitterFollowedUsers.followed_user_id,
        func.count().label('follower_count')
    ).join(
        TwitterFollowedUsers,
        TwitterFollowedUsers.monitored_user_id == TwitterUserClustersProfiles.twitter_user_id
    ).where(
        TwitterUserClustersProfiles.twitter_user_id.in_(profile_ids)
    ).group_by(
        TwitterUserClustersProfiles.cluster_id,
        TwitterFollowedUsers.followed_user_id
    )

    follow_stats = await fetch_all(follow_counts_query)

    # Group response by cluster
    cluster_stats = {}
    for follow_stat in follow_stats:
        cluster_id = follow_stat["cluster_id"]
        if cluster_id not in cluster_stats:
            cluster_stats[cluster_id] = {
                "cluster_name": cluster_map.get(str(follow_stat["cluster_id"]), None),
                "followed": []
            }
        cluster_stats[cluster_id]["followed"].append(
            {
                "twitter_user_id": follow_stat["followed_user_id"],
                "follower_count": follow_stat["follower_count"]
            }
        )

    return {
        "kol_profiles": kol_profiles,
        "cluster_stats": cluster_stats
    }


async def get_kol_profiles(
        screen_names: list[str] = None,
        cluster_names: list[str] = None,
        order_by: str = "created_time",
        sort_order: str = "desc"
):
    """
    Fetch kol cluster profiles
    """

    query = select(
        TwitterUsers.screen_name,
        TwitterUsers.id,
        TwitterUserClustersProfiles.cluster_id,
        TwitterUserClusters.cluster_name
    ).join(
        TwitterUsers,
        TwitterUserClustersProfiles.twitter_user_id == TwitterUsers.id
    ).join(
        TwitterUserClusters,
        TwitterUserClustersProfiles.cluster_id == TwitterUserClusters.id
    )

    if screen_names:
        query = query.filter(TwitterUsers.screen_name.in_(screen_names))

    if cluster_names:
        query = query.filter(TwitterUserClusters.cluster_name.in_(cluster_names))

    if sort_order == "desc":
        query = query.order_by(desc(getattr(TwitterUsers, order_by)))

    if sort_order == "asc":
        query = query.order_by(asc(getattr(TwitterUsers, order_by)))

    return await fetch_all(query)
