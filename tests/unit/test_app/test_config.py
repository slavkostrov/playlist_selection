

async def test_main_page_accessible(client):
    response = await client.get("/")

    assert 200 == response.status_code
