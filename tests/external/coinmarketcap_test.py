import asyncio

import src.external.coinmarketcap.coinmarketcap_service as coinmarketcap_service


async def historical_price_test():
    prices = coinmarketcap_service.get_tickers_historical_prices(
        tickers=["BTC"],
        start_date="2024-02-13 01:09:19.507 +0200",
        end_date="2024-02-13 02:09:19.507 +0200"
    )
    print(prices)


if __name__ == "__main__":
    asyncio.run(historical_price_test())
