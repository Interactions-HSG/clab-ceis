from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock
from time import time
from typing import Any

import requests

from ceis_backend.config import (
    DB_PATH,
    WISER_SP3_API_USER,
    WISER_SP3_API_KEY,
    WISER_AUTH_URL,
    WISER_API_BASE_URL,
)


EMISSION_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60


class WiserClientError(RuntimeError):
    """Raised when the backend cannot complete a Wiser API request."""


class WiserAuthError(WiserClientError):
    """Raised when the backend cannot authenticate with Wiser."""


class WiserClient:
    def __init__(
        self,
        *,
        auth_url: str = WISER_AUTH_URL,
        api_base_url: str = WISER_API_BASE_URL,
        username: str = WISER_SP3_API_USER,
        password: str = WISER_SP3_API_KEY,
        timeout_seconds: float = 30.0,
        token_refresh_margin_seconds: int = 30,
        emission_cache_ttl_seconds: int = EMISSION_CACHE_TTL_SECONDS,
    ) -> None:
        self.auth_url = auth_url
        self.api_base_url = api_base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout_seconds = timeout_seconds
        self.token_refresh_margin_seconds = token_refresh_margin_seconds
        self.emission_cache_ttl_seconds = emission_cache_ttl_seconds
        self._access_token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = Lock()

    def search_activities(self, query: str) -> list[dict[str, Any]]:
        body = self._request_json(
            "POST",
            "/activity/search/",
            headers={"Content-Type": "application/json"},
            json={"query": query},
        )
        search_results = body.get("search_results", [])
        if not isinstance(search_results, list):
            raise WiserClientError("Wiser activity search returned an invalid payload")
        return search_results

    def get_emission_per_unit(self, activity_id: int) -> float | None:
        cache_hit, cached_emission = self._get_cached_emission_per_unit(activity_id)
        if cache_hit:
            return cached_emission

        print(f"Fetching Wiser emission per unit for activity {activity_id}")
        body = self._request_json(
            "GET",
            f"/activity/{activity_id}/",
            headers={"Content-Type": "application/json"},
        )
        lcia_results = body.get("lcia_results", [])
        if not isinstance(lcia_results, list):
            raise WiserClientError(
                f"Wiser activity {activity_id} returned invalid LCIA results"
            )

        for item in lcia_results:
            if item.get("method", {}).get("name") == "IPCC 2021":
                emission_per_unit = item.get("emissions")
                self._cache_emission_per_unit(activity_id, emission_per_unit)
                return emission_per_unit

        self._cache_emission_per_unit(activity_id, None)
        return None

    def _get_cached_emission_per_unit(
        self, activity_id: int
    ) -> tuple[bool, float | None]:
        if not Path(DB_PATH).exists():
            return False, None

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT emission_per_unit, cached_at
                    FROM activity_emission_cache
                    WHERE activity_id = ?
                    """,
                    (activity_id,),
                )
                row = cursor.fetchone()
        except sqlite3.Error:
            return False, None

        if row is None:
            return False, None

        emission_per_unit, cached_at = row
        try:
            cache_age_seconds = time() - float(cached_at)
        except (TypeError, ValueError):
            return False, None

        if cache_age_seconds > self.emission_cache_ttl_seconds:
            return False, None

        return True, emission_per_unit

    def _cache_emission_per_unit(
        self, activity_id: int, emission_per_unit: float | None
    ) -> None:
        if not Path(DB_PATH).exists():
            return

        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    """
                    INSERT INTO activity_emission_cache
                        (activity_id, emission_per_unit, cached_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(activity_id) DO UPDATE SET
                        emission_per_unit = excluded.emission_per_unit,
                        cached_at = excluded.cached_at
                    """,
                    (activity_id, emission_per_unit, time()),
                )
        except sqlite3.Error:
            return

    def _request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.api_base_url}/{path.lstrip('/')}"
        response = self._request(method, url, **kwargs)
        try:
            body = response.json()
        except ValueError as exc:
            raise WiserClientError(
                f"Wiser returned a non-JSON response for {method} {url}"
            ) from exc

        if not isinstance(body, dict):
            raise WiserClientError(
                f"Wiser returned an unexpected JSON payload for {method} {url}"
            )
        return body

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        headers = dict(kwargs.pop("headers", {}))
        initial_headers = {
            **headers,
            "Authorization": f"Bearer {self._get_access_token()}",
        }
        response = self._send_request(method, url, headers=initial_headers, **kwargs)

        if response.status_code == 401:
            retry_headers = {
                **headers,
                "Authorization": (
                    f"Bearer {self._get_access_token(force_refresh=True)}"
                ),
            }
            response = self._send_request(method, url, headers=retry_headers, **kwargs)

        if response.status_code == 401:
            raise WiserAuthError("Wiser authentication failed after token refresh")

        if response.status_code >= 400:
            raise WiserClientError(
                f"Wiser request failed with status {response.status_code} for {method} {url}"
            )

        return response

    def _send_request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        try:
            return requests.request(
                method,
                url,
                timeout=self.timeout_seconds,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise WiserClientError(f"Failed to call Wiser for {method} {url}") from exc

    def _get_access_token(self, force_refresh: bool = False) -> str:
        with self._token_lock:
            if (
                not force_refresh
                and self._access_token is not None
                and time() < self._token_expires_at
            ):
                return self._access_token

            access_token, expires_at = self._fetch_access_token()
            self._access_token = access_token
            self._token_expires_at = expires_at
            return access_token

    def _fetch_access_token(self) -> tuple[str, float]:
        print("Fetching new Wiser access token...")
        payload = {
            "grant_type": "password",
            "client_id": "wiser-api-public",
            "username": self.username,
            "password": self.password,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = requests.post(
                self.auth_url,
                data=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            raise WiserAuthError("Failed to authenticate with Wiser") from exc
        except ValueError as exc:
            raise WiserAuthError("Wiser auth response was not valid JSON") from exc

        access_token = body.get("access_token")
        if not access_token or not isinstance(access_token, str):
            raise WiserAuthError(
                "Wiser auth response did not include a valid access token"
            )

        try:
            expires_in = max(int(body.get("expires_in", 300)), 1)
        except (TypeError, ValueError):
            expires_in = 300

        refresh_margin = min(
            self.token_refresh_margin_seconds,
            max(expires_in - 1, 0),
        )
        return access_token, time() + expires_in - refresh_margin
