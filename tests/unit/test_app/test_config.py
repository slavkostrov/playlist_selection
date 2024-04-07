

async def test_simple(client):
    response = await client.get("/")

    await response.ok
