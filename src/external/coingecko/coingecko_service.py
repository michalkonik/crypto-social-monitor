import datetime
from pycoingecko import CoinGeckoAPI

coingecko_service_handler = None


def get_tickers_prices(
        tickers: list[str],
        vs_currencies: str = 'usd'
) -> dict[str, dict[str, float]]:
    """
    Fetches the current price of specified cryptocurrencies in the specified currency.

    This function uses the CoinGecko API to fetch the current price of the cryptocurrencies
    specified in the `tickers` parameter. The prices are returned in the currency specified
    by the `vs_currencies` parameter.

    Parameters:
    tickers (list[str]): A list of strings representing the ticker symbols of the cryptocurrencies
                         for which to fetch the current price. For example, ['bitcoin', 'ethereum'].
    vs_currencies (str): A string representing the currency in which to return the prices.
                         Defaults to 'usd'.

    Returns:
    dict[str, dict[str, float]]: A dictionary where the keys are the ticker symbols of the
                                  cryptocurrencies and the values are dictionaries where the keys
                                  are the `vs_currencies` and the values are the current prices
                                  of the cryptocurrencies in those currencies.

    Example:
    >>> get_tickers_price(['bitcoin', 'ethereum'], 'usd')
    {'bitcoin': {'usd': 50000}, 'ethereum': {'usd': 4000}}
    """
    coingecko_service = get_coingecko_service()
    return coingecko_service.get_price(
        ids=tickers,
        vs_currencies=vs_currencies
    )


def get_historical_data(coin_id: str, date: datetime.date):
    """
    Fetch historical data for a specific coin on a specific date using the CoinGecko API.
    """
    # Convert the date to the format required by the API (dd-mm-yyyy)
    date_str = date.strftime("%d-%m-%Y")

    data = get_coingecko_service().get_coin_history_by_id(
        id=coin_id,
        date=date_str
    )

    return data


def get_coingecko_service():
    global coingecko_service_handler
    if coingecko_service_handler is None:
        coingecko_service_handler = CoinGeckoAPI()
    return coingecko_service_handler
