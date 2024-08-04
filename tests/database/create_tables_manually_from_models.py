import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.twitter.schemas import TickerMarketData
from src.twitter.service_schemas.narratives.schema import (
    TwitterUsersNarrativesMap
)
from src.database import engine, metadata

# Create an asynchronous session
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def create_table():
    # Use `run_sync` to run the synchronous operation
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all, tables=[TwitterUsersNarrativesMap.__table__])



# Run the function
asyncio.run(create_table())
