from typing import Optional
from datetime import datetime

from sqlmodel import (
    SQLModel,
    Field,
    UniqueConstraint,
)

from sqlalchemy import (
    Column,
    DateTime,
    func
)

from sqlalchemy.dialects.postgresql import JSON as PGJSON


class TwitterUserClusters(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("cluster_name"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    cluster_name: str
    cluster_priority: int
    cluster_data: PGJSON = Field(sa_column=Column(PGJSON), default=None)
    created_time: datetime = Field(default=func.now(), sa_column=Column(DateTime(timezone=True)))

    class Config:
        arbitrary_types_allowed = True


class TwitterUserClustersProfiles(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("twitter_user_id", "cluster_id"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    twitter_user_id: int
    cluster_id: int
    priority: int
    created_time: datetime = Field(
        default=func.now(), sa_column=Column(DateTime(timezone=True))
    )

    class Config:
        arbitrary_types_allowed = True
