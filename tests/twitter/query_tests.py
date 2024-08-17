import asyncio

import datetime

from src.twitter.service import (
    get_tickers_mentioned_by_users,
    calculate_pnl_for_tickers
)


async def ticker_mentions_by_users():
    async def test_simple_tickers_mentioned_by_users():
        mentions = await get_tickers_mentioned_by_users(
            screen_names=["ElonTrades", "CryptoKoryo"],
            limit=None
        )
        print(mentions)

    async def test_get_tickers_most_mentioned_by_users():
        mentions = await get_tickers_mentioned_by_users(
            screen_names=["ElonTrades", "CryptoKoryo"],
            most_mentioned=True
        )
        for user in mentions:
            print(user)
            print(mentions[user])
            print("-----")

    async def test_get_all_tickers_mentioned_by_users():
        mentions = await get_tickers_mentioned_by_users(
            screen_names=["ElonTrades", "CryptoKoryo"],
            all_ticker_mentions=True
        )
        for user in mentions:
            print(user)
            print(mentions[user])
            print("-----")

    await test_simple_tickers_mentioned_by_users()


# ###########################################################
async def calculate_pnl_for_tickers_test():
    user_mentions = {
        'ElonTrades': [
            {'ticker': '$EMC',
             'first_mention': datetime.datetime(2024, 2, 16, 3, 11, 35, 380276, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 988371,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$RNDR',
             'first_mention': datetime.datetime(2024, 2, 16, 3, 11, 35, 380276, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 989362,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$EMC',
             'first_mention': datetime.datetime(2024, 2, 16, 3, 9, 28, 65233, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 988371,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$RNDR',
             'first_mention': datetime.datetime(2024, 2, 16, 3, 9, 28, 65233, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 989362,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$ATOR',
             'first_mention': datetime.datetime(2024, 2, 15, 7, 33, 5, 29175, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 987369,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$OPSEC',
             'first_mention': datetime.datetime(2024, 2, 15, 7, 33, 5, 29175, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 988371,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$OPSEC',
             'first_mention': datetime.datetime(2024, 2, 14, 20, 52, 57, 742181, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 988371,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$WIFI',
             'first_mention': datetime.datetime(2024, 2, 14, 20, 52, 57, 742181, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 989362,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$MINER',
             'first_mention': datetime.datetime(2024, 2, 13, 22, 49, 56, 182407, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 988371,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$NOIA',
             'first_mention': datetime.datetime(2024, 2, 13, 20, 54, 49, 801184, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 988371,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$LIZA',
             'first_mention': datetime.datetime(2024, 2, 13, 3, 20, 34, 899172, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 988371,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$WIFI',
             'first_mention': datetime.datetime(2024, 2, 13, 0, 33, 39, 36694, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 989362,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$ALPH',
             'first_mention': datetime.datetime(2024, 2, 12, 23, 33, 2, 928918, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 986344,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$BTC',
             'first_mention': datetime.datetime(2024, 2, 12, 23, 33, 2, 928918, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 987369,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$BTC',
             'first_mention': datetime.datetime(2024, 2, 12, 23, 9, 19, 507996, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 11, 49, 50, 987369,
                                                          tzinfo=datetime.timezone.utc)}],
        'CryptoKoryo': [
            {'ticker': '$ORDI',
             'first_mention': datetime.datetime(2024, 2, 15, 14, 33, 47, 224191, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 19, 22, 35, 655991,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$DYM',
             'first_mention': datetime.datetime(2024, 2, 15, 9, 45, 41, 738145, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 19, 22, 35, 655991,
                                                          tzinfo=datetime.timezone.utc)},
            {'ticker': '$GNO',
             'first_mention': datetime.datetime(2024, 2, 14, 9, 56, 2, 166612, tzinfo=datetime.timezone.utc),
             'market_data_last_update': datetime.datetime(2024, 2, 16, 19, 22, 35, 655991,
                                                          tzinfo=datetime.timezone.utc)}
        ]
    }

    pnl_data = await calculate_pnl_for_tickers(
        user_mentions=user_mentions
    )
    print(pnl_data)


# ###########################################################
async def get_tickers_info_test():
    from src.twitter.service import get_tickers_market_info
    tickers_info = await get_tickers_market_info(
        tickers=["$BTC", "$ETH", "$ADA"],
    )
    for ticker in tickers_info:
        print(ticker)


async def get_categories_for_screen_names():
    print("----------------------------")
    from src.twitter.service import (
        fetch_categories_for_screen_names
    )

    tickers_info = await fetch_categories_for_screen_names(
        screen_names=["solana", "TatsuEcosystem", "zero1_labs"]
    )
    for ticker in tickers_info:
        print(tickers_info[ticker])

# ###########################################################

if __name__ == "__main__":
    asyncio.run(get_categories_for_screen_names())
