import sqlite3

from fastapi.testclient import TestClient

from ceis_backend.db_init import init_sqlite_db
from ceis_backend.main import app


def test_workbook_prices_replace_only_legacy_default_prices(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CEIS_DISABLE_DISTANCE_SYNC", "1")
    init_sqlite_db()

    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE garment_types SET price_chf = 100 WHERE name = 'Basic Trousers'"
    )
    cursor.execute(
        "UPDATE garment_types SET price_chf = 111 WHERE name = 'Full Trousers'"
    )
    cursor.execute(
        "DELETE FROM sync_state WHERE key = 'workbook_garment_prices_v1'"
    )
    conn.commit()
    conn.close()

    init_sqlite_db()

    with TestClient(app) as client:
        garments = client.get("/garment-types").json()

    prices = {garment["name"]: garment["price_chf"] for garment in garments}
    assert prices["Basic Trousers"] == 246.70
    assert prices["Full Trousers"] == 111
    assert prices["Elegant cowl neck top"] == 124.00
    assert prices["Cocktail fitted dress"] == 339.20
