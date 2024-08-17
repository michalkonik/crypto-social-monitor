import asyncio

import pytz

from src.twitter.background_tasks import (
    fetch_market_data
)

from src.twitter.helpers import (
    parse_timeframe_to_hours
)

from datetime import datetime, timedelta


#
# async def test_fetch_market_data():
#     tickers = ["BTC", "ALPH", "LEH", "SILLYCAT"]
#
#     response = await fetch_market_data(tickers=tickers)
#     print(response)
#
#
# async def main():
#     await test_fetch_market_data()


async def get_trending_projects():
    from src.twitter.service import (
        get_trending_projects
    )

    timeframe = "1h"
    # Define the timeframe in which we fetch the results
    hours = parse_timeframe_to_hours(
        timeframe_str=timeframe
    )
    current_time = datetime.now(pytz.timezone('Etc/GMT-3'))  # Adjust 'Etc/GMT-3' to match your specific timezone
    start_time = current_time - timedelta(hours=hours)

    print(f"Current time: {current_time}")
    print(f"Start time: {start_time}")

    response = await get_trending_projects(
        dynamic_field=f"smart_followers_{timeframe}",
        start_search_date=start_time,
        limit=100
    )
    for item in response:
        print(item)


async def get_project_overview():
    from src.twitter.services.overview.overview_service import (
        get_user_overview
    )

    screen_name = "Entanglefi"
    timeframe = "1d"

    # Define the timeframe in which we fetch the results
    hours = parse_timeframe_to_hours(
        timeframe_str=timeframe
    )
    current_time = datetime.now(pytz.timezone('Etc/GMT-3'))  # Adjust 'Etc/GMT-3' to match your specific timezone
    start_time = current_time - timedelta(hours=hours)

    user_overview = await get_user_overview(
        screen_name=screen_name,
        start_time=start_time
    )
    for data_point in user_overview["data"]:
        print(f"----- {data_point} -----")
        print(user_overview["data"][data_point])

if __name__ == "__main__":
    asyncio.run(get_project_overview())
