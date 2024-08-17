import pytest
import httpx
from httpx import Response
from unittest.mock import patch, AsyncMock

from src.twitter.background_tasks import (
    fetch_market_data,
    update_market_data
)


@pytest.mark.asyncio
async def test_fetch_market_data_actual_response():
    # Call the function with a sample ticker
    result = await fetch_market_data('btc')
    print(result)
    # Check that the function returns the expected result
    assert 'id' in result
    assert 'symbol' in result
    assert 'name' in result


@pytest.mark.asyncio
@patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock)
async def test_fetch_market_data(mock_get):
    # Mock the response from the CoinGecko API
    mock_get.return_value = Response(200, json={'id': 'bitcoin', 'symbol': 'btc', 'name': 'Bitcoin'})

    # Call the function with a sample ticker
    result = await fetch_market_data('btc')

    # Check that the function returns the expected result
    assert result == {'id': 'bitcoin', 'symbol': 'btc', 'name': 'Bitcoin'}


@pytest.mark.asyncio
@patch('src.twitter.background_tasks.execute', new_callable=AsyncMock)
@patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock)
async def test_update_market_data(mock_get, mock_execute):
    # Mock the response from the API service
    mock_get.return_value = Response(200, json={'price': 50000, 'date': '2022-01-01T00:00:00Z'})

    # Call the function with a sample list of tickers
    await update_market_data(['btc'])

    # Check that the execute function was called with the expected arguments
    mock_execute.assert_called_once()
    query = mock_execute.call_args[0][0]
    assert str(query) == 'UPDATE "MarketData" SET price=:price, date=:date WHERE "MarketData".ticker = :ticker_1'
    assert query.compile().params == {'price': 50000, 'date': '2022-01-01T00:00:00Z', 'ticker_1': 'btc'}
