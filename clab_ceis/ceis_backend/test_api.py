# docker compose run --entrypoint="poetry run pytest" ceis-backend

from fastapi.testclient import TestClient
from .main import app

client = TestClient(app)

# def test_read_book():
#     response = client.get("/books/1")
#     assert response.status_code == 200
#     assert response.json() == {
#         "id": 1,
#         "title": "1984",
#         "author": "George Orwell",
#         "availability": True
#     }


def test_get_info_croptop():
    response = client.get("/croptop")
    assert response.status_code == 200

    assert response.json() == {
        "alternatives": [
            {
                "price": 25,
                "co2eq": 33,
                "timestamp": 1707985660,
            },
            {
                "price": 40,
                "co2eq": 20,
                "timestamp": 1708985660,
            },
        ]
    }
