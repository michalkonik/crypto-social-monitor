import os
import logging
import time
from coinmarketcapapi import CoinMarketCapAPI

coinmarketcap_service_handler = None


class CoinMarketCapRateLimitExceeded(Exception):
    """Exception raised when the CoinMarketCap API rate limit is exceeded."""
    pass


last_call_time = None
RATE_LIMIT_WAIT_SECONDS = 30  # Adjust based on CoinMarketCap's rate limit
MAX_RETRIES = 3  # Maximum number of retries for a request
RETRY_BACKOFF_FACTOR = 2  # Factor by which the wait time increases with each retry


def get_api_ticker_data(tickers: list[str]):
    global last_call_time
    try:
        # Concatenate ticker symbols into a comma-separated string
        ticker_string = ','.join(tickers)

        # Rate Limiting: Ensure enough time has passed since the last API call
        current_time = time.time()
        if last_call_time is not None and (current_time - last_call_time < RATE_LIMIT_WAIT_SECONDS):
            time.sleep(RATE_LIMIT_WAIT_SECONDS - (current_time - last_call_time))

        # Attempt the API call for multiple tickers
        response = get_coinmarketcap_service().cryptocurrency_quotes_latest(symbol=ticker_string)
        last_call_time = time.time()  # Update the time of the last successful call

        if response.error:
            logging.error(f"[CoinMarketCap] Error getting ticker data: {response.status.error_message}")
            return None
        return response.data
    except Exception as e:
        logging.error(f"[CoinMarketCap] Exception when calling API: {e}")
        return None


def get_tickers_prices(tickers: list[str]):
    """
    Get prices for multiple tickers in a single API call.
    """
    prices = {}
    try:
        logging.info(f"[CoinMarketCap] API Call: Getting ticker data for {','.join(tickers)}")
        data = get_api_ticker_data(tickers)
        if data:
            for symbol, details in data.items():
                # Assuming details is a dict with the structure: {'quote': {'USD': {'price': value}}}
                if details:
                    price = details[0].get('quote', {}).get('USD', {}).get('price')
                    if price is not None:
                        prices[symbol] = price
    except Exception as error:
        logging.error(f"[CoinMarketCap] Error getting ticker data: {error}")

    return prices


def get_tickers_historical_prices(
        tickers: list[str],
        start_date: str,
        end_date: str
):
    """
    Get historical prices for tickers
    """
    historical_prices = {}

    for ticker in tickers:
        try:
            logging.info(f"[CoinMarketCap] API Call: Getting historical data for {ticker}")
            data = get_coinmarketcap_service().cryptocurrency_ohlcv_historical(
                symbol=ticker,
                time_start=start_date,
                time_end=end_date
            )
            if data:
                for symbol, details in data.items():
                    if 'quotes' in details:
                        historical_prices[symbol] = details['quotes']
        except CoinMarketCapRateLimitExceeded as error:
            print(error)
            logging.critical(f"[CoinMarketCap] Error getting historical data for {ticker}: {error}")
            # If we had hit the rate limit we should stop making requests,  so we return what we have so far
            return historical_prices
        except Exception as error:
            logging.debug(f"[CoinMarketCap] Error getting historical data for {ticker}: {error}")
            print(error)

    return historical_prices


def get_coinmarketcap_service():
    global coinmarketcap_service_handler
    if coinmarketcap_service_handler is None:
        coinmarketcap_service_handler = CoinMarketCapAPI(api_key=os.getenv("COINMARKETCAP_API_KEY"))
    return coinmarketcap_service_handler
