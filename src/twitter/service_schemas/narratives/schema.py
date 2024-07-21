from typing import Optional
from datetime import datetime

from sqlmodel import (
    SQLModel,
    Field,
    UniqueConstraint,
    ForeignKeyConstraint
)
from sqlalchemy import (
    Column,
    DateTime,
    func
)


class Narratives(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("narrative_name"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    narrative_name: str
    keywords: str
    created_time: datetime = Field(default=func.now(), sa_column=Column(DateTime(timezone=True)))
    updated_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), onupdate=func.now()))


class TwitterUsersNarrativesMap(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("narrative_id", "twitter_user_id"),
        ForeignKeyConstraint(["narrative_id"], ["narratives.id"]),
        ForeignKeyConstraint(["twitter_user_id"], ["twitterusers.id"]),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    narrative_id: int
    twitter_user_id: int
    score: int = Field(default=0)
    custom_score: int = Field(default=0)
    created_time: datetime = Field(default=func.now(), sa_column=Column(DateTime(timezone=True)))
    updated_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), onupdate=func.now()))
