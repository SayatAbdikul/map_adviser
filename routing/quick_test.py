import httpx
import asyncio

async def test_api():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            'https://catalog.api.2gis.com/3.0/items',
            params={
                'q': 'restaurant',
                'key': 'ed1537b1-4397-4542-9633-97f7585cb789',
                'page_size': 3
            }
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:1000]}")

asyncio.run(test_api())
