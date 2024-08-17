import asyncio
import requests


async def get_monitored_users():
    url = "http://67.223.117.109:8888/twitter/monitored?page=1&page_size=10000"

    TOKEN = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxN"
             "zExMDY1NDgwLCJpc19hZG1pbiI6ZmFsc2V9.9iKtY9kKx2cfJ_O1xifF9v8uWDjDtus3X3qfNof2HH8")
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    response = requests.get(url, headers=headers)
    print(f"Found: {len(response.json())} monitored users")


if __name__ == "__main__":
    asyncio.run(get_monitored_users())
