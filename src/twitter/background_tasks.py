import logging
import asyncio

from threading import Thread

from sqlalchemy import insert

import src.external.coingecko.coingecko_service as coingecko_service
import src.external.coinmarketcap.coinmarketcap_service as coinmarketcap_service
import src.external.dexscreener.dexscreener_service as dexscreener_service

from src.twitter.helpers import get_current_time
from src.database import execute_multi_queries

from src.twitter.schemas import TickerMarketData


def run_async_in_thread(func, *args):
    """Run an async function func in a separate thread."""
    # Define a function to be run in a new thread that schedules func in the existing event loop
    def thread_target(loop):
        coro = func(*args)
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            # Wait for the future to complete and get its result
            future.result()
        except Exception as exc:
            # Handle exceptions from the coroutine
            print(f"Exception in run_async_in_thread: {exc}")

    # Get the current event loop; assuming this is called in the context where an event loop is running
    current_loop = asyncio.get_running_loop()
    # Start a new thread that schedules the coroutine in the current event loop
    thread = Thread(target=thread_target, args=(current_loop,))
    thread.start()


async def fetch_prices_from_service(service, tickers):
    try:
        response = service.get_tickers_prices(
            tickers=tickers
        )
        return response
    except Exception as e:
        logging.error(f"[fetch_prices_from_service] Error fetching market data for tickers: {tickers}. Error: {e}")
        return {}


async def fetch_market_data(
        tickers: list[str]
):
    tickers = list(set(tickers))
    cnt_tickers_to_update = len(tickers)
    # services = [coinmarketcap_service, coingecko_service, dexscreener_service]
    services = [coinmarketcap_service, dexscreener_service]
    prices = {}

    for service in services:
        logging.debug(f"Fetching market data from service: {service.__name__} for tickers: {tickers}")
        response = await fetch_prices_from_service(service, tickers)
        prices.update(response)

        # Check if we have collected the price for all tickers
        if len(prices) == cnt_tickers_to_update:
            return prices

        # Filter tickers list with the ones we have NOT collected the price
        tickers = [ticker for ticker in tickers if ticker not in prices]

        if not tickers:
            return prices

    # Return what we have collected so far
    return prices


async def update_market_data_in_a_thread(
        tickers: list[str]
):
    run_async_in_thread(update_market_data, tickers)


async def update_market_data(
        tickers: list[str]
) -> bool:
    try:
        tickers_prices = await fetch_market_data(
            tickers=[ticker.replace("$", "") for ticker in tickers]
        )
        logging.debug(f"Updating market data for tickers: {tickers_prices}")

        # After fetching the prices, we need to insert them into the database, but with the "$" symbol infront
        tickers_prices = {f"${ticker}": price for ticker, price in tickers_prices.items()}

        # Create a list of update queries
        insert_queries = [
            insert(TickerMarketData).values(ticker=ticker, price=price, created_time=get_current_time())
            for ticker, price in tickers_prices.items()
        ]

        non_updated_tickers = [ticker for ticker in tickers if ticker not in tickers_prices]
        if non_updated_tickers:
            logging.debug(
                f"[update_market_data] Could not update market data for tickers: {non_updated_tickers}."
            )

        # Execute the update queries in a separate thread
        await execute_multi_queries(
            queries=insert_queries
        )

        return True
    except Exception as error:
        logging.error(
            f"[update_market_data] Error updating market data for tickers: {tickers}. Error: {error}"
        )
        return False
