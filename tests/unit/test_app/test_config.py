

async def test_simple(app, client):
    response = await client.get("/")

    await response.ok
