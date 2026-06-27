async def test_healthcheck(client):
    response = await client.get("/healthcheck/")
    data = response.json()

    assert response.status_code == 200
    assert data == {"status": "ok"}
