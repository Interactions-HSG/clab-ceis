from __future__ import annotations

from callbacks import api


class _Response:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_fetch_garment_types_returns_payload(monkeypatch):
    def fake_get(url):
        assert url.endswith("/garment-types")
        return _Response(200, [{"id": 1, "name": "Crop Top"}])

    monkeypatch.setattr(api.requests, "get", fake_get)

    result = api.fetch_garment_types()

    assert result == [{"id": 1, "name": "Crop Top"}]


def test_fetch_fabric_blocks_formats_processes(monkeypatch):
    def fake_get(url):
        assert url.endswith("/fabric-blocks")
        return _Response(
            200,
            [
                {
                    "id": 5,
                    "type": "80x64",
                    "processes": [{"type": "sewing", "amount": 0.42}],
                }
            ],
        )

    monkeypatch.setattr(api.requests, "get", fake_get)

    result = api.fetch_fabric_blocks()

    assert len(result) == 1
    assert result[0]["processes"] == "sewing(0.42)"


def test_fetch_strategy_progress_returns_payload(monkeypatch):
    payload = {
        "aggregates": {
            "circularity_pct": 42.0,
            "fabric_saved_pct": 37.5,
            "environmental_cost_co2eq": 54.0,
        }
    }

    def fake_get(url):
        assert url.endswith("/strategy-progress")
        return _Response(200, payload)

    monkeypatch.setattr(api.requests, "get", fake_get)

    result = api.fetch_strategy_progress()

    assert result == payload
