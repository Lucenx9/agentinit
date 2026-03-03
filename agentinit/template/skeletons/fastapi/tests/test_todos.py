def test_create_and_list_todos(client):
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []

    created = client.post("/todos", json={"title": "Ship CLI polish"})
    assert created.status_code == 201
    assert created.json()["title"] == "Ship CLI polish"

    listed = client.get("/todos")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["title"] == "Ship CLI polish"
