

async def test_simple(app, client):
    response = await client.get("/")
    assert 1 == 0
