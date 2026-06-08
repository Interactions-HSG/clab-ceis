import sqlite3
from unittest.mock import MagicMock, patch

from ceis_backend.db_init import create_tables
from ceis_backend.wiser_bridge import WiserClient


def _auth_response(access_token: str, expires_in: int = 300) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "access_token": access_token,
        "expires_in": expires_in,
    }
    return response


def _activity_response(status_code: int, emissions: float | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = {
        "lcia_results": []
        if emissions is None
        else [{"method": {"name": "IPCC 2021"}, "emissions": emissions}]
    }
    return response


def test_reuses_cached_access_token_for_multiple_requests(tmp_path, monkeypatch):
    monkeypatch.setattr("ceis_backend.wiser_bridge.DB_PATH", str(tmp_path / "test.db"))
    client = WiserClient(
        auth_url="https://auth.example", api_base_url="https://api.example"
    )

    with patch(
        "ceis_backend.wiser_bridge.requests.post",
        return_value=_auth_response("cached-token"),
    ) as mocked_post:
        with patch(
            "ceis_backend.wiser_bridge.requests.request",
            side_effect=[_activity_response(200, 0.5), _activity_response(200, 0.8)],
        ) as mocked_request:
            assert client.get_emission_per_unit(1001) == 0.5
            assert client.get_emission_per_unit(1002) == 0.8

    assert mocked_post.call_count == 1
    assert mocked_request.call_count == 2
    first_headers = mocked_request.call_args_list[0].kwargs["headers"]
    second_headers = mocked_request.call_args_list[1].kwargs["headers"]
    assert first_headers["Authorization"] == "Bearer cached-token"
    assert second_headers["Authorization"] == "Bearer cached-token"


def test_refreshes_token_once_after_unauthorized_response(tmp_path, monkeypatch):
    monkeypatch.setattr("ceis_backend.wiser_bridge.DB_PATH", str(tmp_path / "test.db"))
    client = WiserClient(
        auth_url="https://auth.example", api_base_url="https://api.example"
    )

    with patch(
        "ceis_backend.wiser_bridge.requests.post",
        side_effect=[_auth_response("stale-token"), _auth_response("fresh-token")],
    ) as mocked_post:
        with patch(
            "ceis_backend.wiser_bridge.requests.request",
            side_effect=[_activity_response(401), _activity_response(200, 1.5)],
        ) as mocked_request:
            assert client.get_emission_per_unit(2001) == 1.5

    assert mocked_post.call_count == 2
    assert mocked_request.call_count == 2
    first_headers = mocked_request.call_args_list[0].kwargs["headers"]
    second_headers = mocked_request.call_args_list[1].kwargs["headers"]
    assert first_headers["Authorization"] == "Bearer stale-token"
    assert second_headers["Authorization"] == "Bearer fresh-token"


def test_reuses_fresh_database_emission_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("ceis_backend.wiser_bridge.time", lambda: 1_000_000)

    conn = sqlite3.connect("ceis_backend.db")
    create_tables(conn.cursor())
    conn.execute(
        """
        INSERT INTO activity_emission_cache
            (activity_id, emission_per_unit, cached_at)
        VALUES (?, ?, ?)
        """,
        (3001, 2.75, 1_000_000),
    )
    conn.commit()
    conn.close()

    client = WiserClient(
        auth_url="https://auth.example", api_base_url="https://api.example"
    )

    with patch("ceis_backend.wiser_bridge.requests.post") as mocked_post:
        with patch("ceis_backend.wiser_bridge.requests.request") as mocked_request:
            assert client.get_emission_per_unit(3001) == 2.75

    mocked_post.assert_not_called()
    mocked_request.assert_not_called()


def test_refreshes_stale_database_emission_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    now = 1_000_000
    eight_days_ago = now - (8 * 24 * 60 * 60)
    monkeypatch.setattr("ceis_backend.wiser_bridge.time", lambda: now)

    conn = sqlite3.connect("ceis_backend.db")
    create_tables(conn.cursor())
    conn.execute(
        """
        INSERT INTO activity_emission_cache
            (activity_id, emission_per_unit, cached_at)
        VALUES (?, ?, ?)
        """,
        (4001, 1.25, eight_days_ago),
    )
    conn.commit()
    conn.close()

    client = WiserClient(
        auth_url="https://auth.example", api_base_url="https://api.example"
    )

    with patch(
        "ceis_backend.wiser_bridge.requests.post",
        return_value=_auth_response("fresh-token"),
    ):
        with patch(
            "ceis_backend.wiser_bridge.requests.request",
            return_value=_activity_response(200, 3.5),
        ) as mocked_request:
            assert client.get_emission_per_unit(4001) == 3.5

    assert mocked_request.call_count == 1

    conn = sqlite3.connect("ceis_backend.db")
    row = conn.execute(
        """
        SELECT emission_per_unit, cached_at
        FROM activity_emission_cache
        WHERE activity_id = ?
        """,
        (4001,),
    ).fetchone()
    conn.close()

    assert row == (3.5, now)
