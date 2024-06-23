from typing import Optional
from sqlmodel import (
    SQLModel,
    Field,
    UniqueConstraint,
    ForeignKeyConstraint,
    Index
)
from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    func
)

from sqlalchemy.dialects.postgresql import JSON as PGJSON


class TickerMarketData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str
    price: float
    volume_24h: Optional[float]
    volume_change_24h: Optional[float]
    percent_change_1h: Optional[float]
    percent_change_24h: Optional[float]
    percent_change_7d: Optional[float]
    percent_change_30d: Optional[float]
    percent_change_60d: Optional[float]
    percent_change_90d: Optional[float]
    market_cap: Optional[float]
    market_cap_dominance: Optional[float]
    fully_diluted_market_cap: Optional[float]
    coinmarketcap: PGJSON = Field(sa_column=Column(PGJSON), default=None)
    dextools: PGJSON = Field(sa_column=Column(PGJSON), default=None)
    created_time: datetime = Field(default=func.now(), sa_column=Column(DateTime(timezone=True)))

    class Config:
        arbitrary_types_allowed = True


class TwitterUsers(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("screen_name"),
        Index('idx_twitter_users_is_crypto_project', 'is_crypto_project'),  # Index for filtering
        Index('idx_twitter_users_followers_count', 'followers_count'),  # Index for sorting/filtering
        Index('idx_twitter_users_statuses_count', 'statuses_count'),  # Index for sorting/filtering
        Index('idx_twitter_users_created_time', 'created_time'),  # Index for sorting/filtering
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    screen_name: str
    profile_id: str
    account_info: PGJSON = Field(sa_column=Column(PGJSON), default=None)
    followers_count: int = Field(default=0)  # Extracted for better performance
    statuses_count: int = Field(default=0)  # Extracted for better performance
    monitor_following: bool = Field(default=False)
    monitor_posts: bool = Field(default=False)
    is_crypto_project: bool = Field(default=False)
    monitor_profile_or_banner_image: bool = Field(default=False)
    created_time: datetime = Field(default=func.now(), sa_column=Column(DateTime(timezone=True)))
    updated_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    class Config:
        arbitrary_types_allowed = True


class TwitterFollowedUsers(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("monitored_user_id", "followed_user_id"),
        ForeignKeyConstraint(["monitored_user_id"], ["twitterusers.id"]),
        ForeignKeyConstraint(["followed_user_id"], ["twitterusers.id"]),
        Index('idx_twitter_followed_users_monitored_user_id', 'monitored_user_id'),
        Index('idx_twitter_followed_users_followed_user_id', 'followed_user_id'),
        Index('idx_twitter_followed_users_followers_count', 'followers_count'),  # Index for sorting/filtering
        Index('idx_twitter_followed_users_statuses_count', 'statuses_count'),  # Index for sorting/filtering
        Index('idx_twitter_followed_users_created_time', 'created_time'),  # Index for sorting/filtering
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    monitored_user_id: int
    followed_user_id: int
    followed_user_meta_data: PGJSON = Field(sa_column=Column(PGJSON), default=None)
    followers_count: int = Field(default=0)  # Extracted for better performance
    statuses_count: int = Field(default=0)  # Extracted for better performance
    created_time: datetime = Field(default=func.now(), sa_column=Column(DateTime(timezone=True)))

    class Config:
        arbitrary_types_allowed = True


class TwitterSuggestedUsers(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("monitored_user_id", "suggested_user_id"),
        ForeignKeyConstraint(["monitored_user_id"], ["twitterusers.id"]),
        ForeignKeyConstraint(["suggested_user_id"], ["twitterusers.id"])
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    monitored_user_id: int
    suggested_user_id: int
    created_time: datetime = Field(default=func.now(), sa_column=Column(DateTime(timezone=True)))

    class Config:
        arbitrary_types_allowed = True


class Posts(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("post_id"),
        ForeignKeyConstraint(["user_id"], ["twitterusers.id"])
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    post: str
    post_id: str
    profile_image: str
    post_time: datetime
    post_meta_data: PGJSON = Field(sa_column=Column(PGJSON), default=None)
    created_time: datetime = Field(default=func.now(), sa_column=Column(DateTime(timezone=True)))

    class Config:
        arbitrary_types_allowed = True


class Tickers(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("ticker", "post_id"),
        ForeignKeyConstraint(["post_id"], ["posts.id"])
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str
    post_id: int  # not the same as "post_id" field in "Posts" table
    created_time: datetime = Field(default=func.now(), sa_column=Column(DateTime(timezone=True)))


class CoinMarketCapMetaData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str
    twitter_username: str
    meta_data: PGJSON = Field(sa_column=Column(PGJSON), default=None)
    created_time: datetime = Field(default=func.now(), sa_column=Column(DateTime(timezone=True)))

    class Config:
        arbitrary_types_allowed = True


class CoingeckoMetaData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str
    twitter_username: str
    meta_data: PGJSON = Field(sa_column=Column(PGJSON), default=None)
    created_time: datetime = Field(default=func.now(), sa_column=Column(DateTime(timezone=True)))

    class Config:
        arbitrary_types_allowed = True


class GeckoTerminalMetaData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str
    twitter_username: str
    meta_data: PGJSON = Field(sa_column=Column(PGJSON), default=None)
    created_time: datetime = Field(default=func.now(), sa_column=Column(DateTime(timezone=True)))

    class Config:
        arbitrary_types_allowed = True


class PreCalculatedDataStore(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(["twitter_user_id"], ["twitterusers.id"]),
        ForeignKeyConstraint(["narrative_id"], ["narratives.id"]),
        Index('idx_precalculated_data_store_twitter_user_id', 'twitter_user_id'),
        Index('idx_precalculated_data_store_created_time', 'created_time'),
        Index('idx_precalculated_data_store_potential_ticker', 'potential_ticker'),

        Index('idx_precalculated_data_store_smart_followers_1h', 'smart_followers_1h'),
        Index('idx_precalculated_data_store_smart_followers_4h', 'smart_followers_4h'),
        Index('idx_precalculated_data_store_smart_followers_6h', 'smart_followers_6h'),
        Index('idx_precalculated_data_store_smart_followers_12h', 'smart_followers_12h'),
        Index('idx_precalculated_data_store_smart_followers_1d', 'smart_followers_1d'),
        Index('idx_precalculated_data_store_smart_followers_3d', 'smart_followers_3d'),
        Index('idx_precalculated_data_store_smart_followers_7d', 'smart_followers_7d'),
        Index('idx_precalculated_data_store_smart_followers_14d', 'smart_followers_14d'),
        Index('idx_precalculated_data_store_smart_followers_1m', 'smart_followers_1m'),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    twitter_user_id: int
    narrative_id: Optional[int] = Field(default=None, nullable=True)
    category_tag: str = Field(default="Other")
    potential_ticker: Optional[str] = Field(default=None, nullable=True)
    # Smart follows trends
    smart_followers_1h: int = Field(default=0)
    smart_followers_4h: int = Field(default=0)
    smart_followers_6h: int = Field(default=0)
    smart_followers_12h: int = Field(default=0)
    smart_followers_1d: int = Field(default=0)
    smart_followers_3d: int = Field(default=0)
    smart_followers_7d: int = Field(default=0)
    smart_followers_14d: int = Field(default=0)
    smart_followers_1m: int = Field(default=0)
    total_smart_followers: int = Field(default=0)
    total_followers: int = Field(default=0)
    # Smart mentions of projects "screen_name"
    smart_mentions_project_1h: int = Field(default=0)
    smart_mentions_project_4h: int = Field(default=0)
    smart_mentions_project_6h: int = Field(default=0)
    smart_mentions_project_12h: int = Field(default=0)
    smart_mentions_project_1d: int = Field(default=0)
    smart_mentions_project_7d: int = Field(default=0)
    smart_mentions_project_14d: int = Field(default=0)
    smart_mentions_project_1m: int = Field(default=0)
    total_smart_mentions_project: int = Field(default=0)
    # Potential ticker mentions
    smart_mentions_ticker_1h: int = Field(default=0)
    smart_mentions_ticker_4h: int = Field(default=0)
    smart_mentions_ticker_6h: int = Field(default=0)
    smart_mentions_ticker_12h: int = Field(default=0)
    smart_mentions_ticker_1d: int = Field(default=0)
    smart_mentions_ticker_7d: int = Field(default=0)
    smart_mentions_ticker_14d: int = Field(default=0)
    smart_mentions_ticker_1m: int = Field(default=0)
    total_smart_mentions_ticker: int = Field(default=0)
    # Calculated scores
    score: int = Field(default=0)
    custom_score: int = Field(default=0)
    created_time: datetime = Field(
        default=func.now(),
        sa_column=Column(DateTime(timezone=True))
    )


class PostLabels(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("post_id"),
        ForeignKeyConstraint(["post_id"], ["posts.id"]),
        Index('idx_post_labels_post_id', 'post_id')
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int
    sentiment_label: str
    created_time: datetime = Field(default=func.now(), sa_column=Column(DateTime(timezone=True)))

class PreCalculatedOverviewData1h(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    hourly_changes_follows: Optional[str] = Field(default=None)
    hourly_changes_ticker_mentions: Optional[str] = Field(default=None)
    word_cloud: Optional[str] = Field(default=None)
    posts_activity: Optional[str] = Field(default=None)
    follows_activity: Optional[str] = Field(default=None)
    sentiment_activity: Optional[str] = Field(default=None)
    projects_mind_share_activity: Optional[str] = Field(default=None)
    category_mind_share_activity: Optional[str] = Field(default=None)

    created_time: datetime = Field(
        default=func.now(),
        sa_column=Column(DateTime(timezone=True))
    )


class PreCalculatedOverviewData4h(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    hourly_changes_follows: Optional[str] = Field(default=None)
    hourly_changes_ticker_mentions: Optional[str] = Field(default=None)
    word_cloud: Optional[str] = Field(default=None)
    posts_activity: Optional[str] = Field(default=None)
    follows_activity: Optional[str] = Field(default=None)
    sentiment_activity: Optional[str] = Field(default=None)
    projects_mind_share_activity: Optional[str] = Field(default=None)
    category_mind_share_activity: Optional[str] = Field(default=None)

    created_time: datetime = Field(
        default=func.now(),
        sa_column=Column(DateTime(timezone=True))
    )


class PreCalculatedOverviewData6h(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    hourly_changes_follows: Optional[str] = Field(default=None)
    hourly_changes_ticker_mentions: Optional[str] = Field(default=None)
    word_cloud: Optional[str] = Field(default=None)
    posts_activity: Optional[str] = Field(default=None)
    follows_activity: Optional[str] = Field(default=None)
    sentiment_activity: Optional[str] = Field(default=None)
    projects_mind_share_activity: Optional[str] = Field(default=None)
    category_mind_share_activity: Optional[str] = Field(default=None)

    created_time: datetime = Field(
        default=func.now(),
        sa_column=Column(DateTime(timezone=True))
    )


class PreCalculatedOverviewData12h(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    hourly_changes_follows: Optional[str] = Field(default=None)
    hourly_changes_ticker_mentions: Optional[str] = Field(default=None)
    word_cloud: Optional[str] = Field(default=None)
    posts_activity: Optional[str] = Field(default=None)
    follows_activity: Optional[str] = Field(default=None)
    sentiment_activity: Optional[str] = Field(default=None)
    projects_mind_share_activity: Optional[str] = Field(default=None)
    category_mind_share_activity: Optional[str] = Field(default=None)

    created_time: datetime = Field(
        default=func.now(),
        sa_column=Column(DateTime(timezone=True))
    )


class PreCalculatedOverviewData1d(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    hourly_changes_follows: Optional[str] = Field(default=None)
    hourly_changes_ticker_mentions: Optional[str] = Field(default=None)
    word_cloud: Optional[str] = Field(default=None)
    posts_activity: Optional[str] = Field(default=None)
    follows_activity: Optional[str] = Field(default=None)
    sentiment_activity: Optional[str] = Field(default=None)
    projects_mind_share_activity: Optional[str] = Field(default=None)
    category_mind_share_activity: Optional[str] = Field(default=None)

    created_time: datetime = Field(
        default=func.now(),
        sa_column=Column(DateTime(timezone=True))
    )

class PreCalculatedOverviewData3d(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    hourly_changes_follows: Optional[str] = Field(default=None)
    hourly_changes_ticker_mentions: Optional[str] = Field(default=None)
    word_cloud: Optional[str] = Field(default=None)
    posts_activity: Optional[str] = Field(default=None)
    follows_activity: Optional[str] = Field(default=None)
    sentiment_activity: Optional[str] = Field(default=None)
    projects_mind_share_activity: Optional[str] = Field(default=None)
    category_mind_share_activity: Optional[str] = Field(default=None)

    created_time: datetime = Field(
        default=func.now(),
        sa_column=Column(DateTime(timezone=True))
    )


class PreCalculatedOverviewData7d(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    hourly_changes_follows: Optional[str] = Field(default=None)
    hourly_changes_ticker_mentions: Optional[str] = Field(default=None)
    word_cloud: Optional[str] = Field(default=None)
    posts_activity: Optional[str] = Field(default=None)
    follows_activity: Optional[str] = Field(default=None)
    sentiment_activity: Optional[str] = Field(default=None)
    projects_mind_share_activity: Optional[str] = Field(default=None)
    category_mind_share_activity: Optional[str] = Field(default=None)

    created_time: datetime = Field(
        default=func.now(),
        sa_column=Column(DateTime(timezone=True))
    )


class PreCalculatedOverviewData14d(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    hourly_changes_follows: Optional[str] = Field(default=None)
    hourly_changes_ticker_mentions: Optional[str] = Field(default=None)
    word_cloud: Optional[str] = Field(default=None)
    posts_activity: Optional[str] = Field(default=None)
    follows_activity: Optional[str] = Field(default=None)
    sentiment_activity: Optional[str] = Field(default=None)
    projects_mind_share_activity: Optional[str] = Field(default=None)
    category_mind_share_activity: Optional[str] = Field(default=None)

    created_time: datetime = Field(
        default=func.now(),
        sa_column=Column(DateTime(timezone=True))
    )


class PreCalculatedOverviewData1m(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    hourly_changes_follows: Optional[str] = Field(default=None)
    hourly_changes_ticker_mentions: Optional[str] = Field(default=None)
    word_cloud: Optional[str] = Field(default=None)
    posts_activity: Optional[str] = Field(default=None)
    follows_activity: Optional[str] = Field(default=None)
    sentiment_activity: Optional[str] = Field(default=None)
    projects_mind_share_activity: Optional[str] = Field(default=None)
    category_mind_share_activity: Optional[str] = Field(default=None)

    created_time: datetime = Field(
        default=func.now(),
        sa_column=Column(DateTime(timezone=True))
    )


