"""
API reference: https://docs.dexscreener.com/api/reference
"""
import logging
from dexscreener import DexscreenerClient

dexscreener_service_handler = None


def get_tickers_prices(
        tickers: list[str]
) -> dict[str, float]:
    prices = {}
    for ticker in tickers:
        try:
            response = get_dexscreener_service().search_pairs(ticker)
            # The most likely pair is the first one
            if not response:
                continue
            token_info = response[0]
            if token_info and token_info.price_usd is not None:
                prices[ticker] = token_info.price_usd
        except Exception as error:
            logging.debug(
                f"[DexScreener] Error getting ticker data for {ticker}: {error}"
            )
    return prices


def get_dexscreener_service():
    global dexscreener_service_handler
    if dexscreener_service_handler is None:
        dexscreener_service_handler = DexscreenerClient()
    return dexscreener_service_handler
