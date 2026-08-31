from fastapi.testclient import TestClient

from ceis_backend.db_init import init_sqlite_db
from ceis_backend.main import app


def test_material_area_price_is_persisted_and_editable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CEIS_DISABLE_DISTANCE_SYNC", "1")
    init_sqlite_db()

    with TestClient(app) as client:
        seeded_materials = client.get("/materials")
        update_response = client.post(
            "/materials",
            json={
                "name": "hemp",
                "kg_per_sqm": 0.21,
                "cost_per_sqm_chf": 8.75,
                "activity_id": 276186,
            },
        )
        updated_materials = client.get("/materials")

    assert seeded_materials.status_code == 200
    seeded_hemp = next(
        material
        for material in seeded_materials.json()
        if material["name"] == "hemp"
    )
    assert seeded_hemp["cost_per_sqm_chf"] == 5.04

    assert update_response.status_code == 200
    assert update_response.json()["cost_per_sqm_chf"] == 8.75
    updated_hemp = next(
        material
        for material in updated_materials.json()
        if material["name"] == "hemp"
    )
    assert updated_hemp["cost_per_sqm_chf"] == 8.75
