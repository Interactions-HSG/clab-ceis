"""Sync manufacturer transport distances from CSV into SQLite."""

from __future__ import annotations
import requests

import csv
import hashlib
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from ceis_backend.config import BASE_DIR, DB_PATH

CSV_PATH = BASE_DIR / "data" / "Lake Constance Region Manufacturers.csv"
SYNC_HASH_KEY = "lake_constance_manufacturers_csv_sha256"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
HTTP_HEADERS = {"User-Agent": "clab-ceis/1.0 (distance-sync)"}
NOMINATIM_MIN_INTERVAL_SEC = float(os.getenv("CEIS_NOMINATIM_MIN_INTERVAL_SEC", "1.1"))


@dataclass
class Manufacturer:
    company: str
    role: str
    role_group: str
    location: str


class _RateLimiter:
    def __init__(self, min_interval_sec: float):
        self.min_interval_sec = min_interval_sec
        self._last_call_monotonic = 0.0

    def wait(self) -> None:
        if "PYTEST_CURRENT_TEST" in os.environ:
            return
        now = time.monotonic()
        elapsed = now - self._last_call_monotonic
        if elapsed < self.min_interval_sec:
            time.sleep(self.min_interval_sec - elapsed)
        self._last_call_monotonic = time.monotonic()


_nominatim_limiter = _RateLimiter(NOMINATIM_MIN_INTERVAL_SEC)


def _csv_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_role(role: str) -> str | None:
    role_lower = role.strip().lower()
    if "fabric manufacturer" in role_lower:
        return "fabric"
    if "garment manufacturer" in role_lower:
        return "garment"
    if "finishing" in role_lower:
        return "finishing"
    return None


def _candidate_geocode_queries(location: str) -> list[str]:
    """Build geocoding query fallbacks from a location string."""
    parts = [part.strip() for part in location.split(",") if part.strip()]
    candidates: list[str] = [location]
    if len(parts) > 1:
        # Drop company name and use only the address part first.
        candidates.append(", ".join(parts[1:]))
    if len(parts) > 2:
        # Try street + postal/city/country.
        candidates.append(", ".join(parts[-3:]))
    if len(parts) > 1:
        # Try just postal/city/country.
        candidates.append(", ".join(parts[-2:]))

    # Try postcode+city(+country) extracted from free-form addresses.
    postal_city = None
    country = None
    country_match = re.search(
        r"(Germany|Switzerland|Austria)$", location, flags=re.IGNORECASE
    )
    if country_match:
        country = country_match.group(1)
    postcode_city_match = re.search(
        r"(?:\b[A-Z]{1,2}\s*-\s*)?(\d{4,5})\s+([A-Za-zÀ-ÖØ-öø-ÿ.\- ]+)",
        location,
    )
    if postcode_city_match:
        postcode = postcode_city_match.group(1).strip()
        city = postcode_city_match.group(2).strip().strip(",")
        postal_city = f"{postcode} {city}"
    if postal_city and country:
        candidates.append(f"{postal_city}, {country}")
    elif postal_city:
        candidates.append(postal_city)

    if country:
        city_only_match = re.search(
            r",\s*([A-Za-zÀ-ÖØ-öø-ÿ.\- ]+)\s*,\s*" + re.escape(country) + r"$",
            location,
            flags=re.IGNORECASE,
        )
        if city_only_match:
            candidates.append(f"{city_only_match.group(1).strip()}, {country}")
    # Deduplicate while preserving order.
    seen: set[str] = set()
    result: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
    return result


def _load_geocode_cache_from_db(
    cursor: sqlite3.Cursor,
) -> dict[str, tuple[float, float]]:
    cursor.execute("SELECT address, lat, lon FROM geocode_cache")
    rows = cursor.fetchall()
    return {address: (float(lat), float(lon)) for address, lat, lon in rows}


def _persist_geocode_cache_to_db(
    cursor: sqlite3.Cursor,
    geocode_cache: dict[str, tuple[float, float] | None],
) -> None:
    valid_rows = [
        (address, coords[0], coords[1])
        for address, coords in geocode_cache.items()
        if coords is not None
    ]
    if not valid_rows:
        return
    cursor.executemany(
        """
        INSERT INTO geocode_cache (address, lat, lon)
        VALUES (?, ?, ?)
        ON CONFLICT(address) DO UPDATE SET lat = excluded.lat, lon = excluded.lon
        """,
        valid_rows,
    )


def _load_manufacturers(csv_path: Path) -> list[Manufacturer]:
    manufacturers: list[Manufacturer] = []
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            company = (row.get("COMPANY") or "").strip()
            role = (row.get("ROLE") or "").strip()
            location = (row.get("LOCATION") or "").strip()
            role_group = _normalize_role(role)
            if not company or not role_group or not location:
                continue
            manufacturers.append(
                Manufacturer(
                    company=company,
                    role=role,
                    role_group=role_group,
                    location=location,
                )
            )
    return manufacturers


def _geocode(
    address: str,
    cache: dict[str, tuple[float, float] | None],
    errors: dict[str, str],
) -> tuple[float, float] | None:
    if address in cache:
        return cache[address]

    for query in _candidate_geocode_queries(address):
        for attempt in range(3):
            try:
                _nominatim_limiter.wait()
                response = requests.get(
                    NOMINATIM_URL,
                    params={
                        "q": query,
                        "format": "jsonv2",
                        "limit": 1,
                        "accept-language": "en",
                    },
                    headers=HTTP_HEADERS,
                    timeout=20,
                )
                if response.status_code == 429:
                    errors[address] = f"429 rate-limited for query={query}"
                    if "PYTEST_CURRENT_TEST" not in os.environ:
                        time.sleep(2 + attempt)
                    continue
                response.raise_for_status()
                result = response.json()
                if not result:
                    break
                lat = float(result[0]["lat"])
                lon = float(result[0]["lon"])
                cache[address] = (lat, lon)
                errors.pop(address, None)
                return (lat, lon)
            except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
                errors[address] = str(exc)
                if "PYTEST_CURRENT_TEST" not in os.environ:
                    time.sleep(1 + attempt)
                continue

    cache[address] = None
    errors.setdefault(address, "No results from geocoder")
    return None


def _distance_km(
    source: tuple[float, float], destination: tuple[float, float]
) -> float | None:
    lat1, lon1 = source
    lat2, lon2 = destination
    try:
        response = requests.get(
            f"{OSRM_URL}/{lon1},{lat1};{lon2},{lat2}",
            params={"overview": "false"},
            headers=HTTP_HEADERS,
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            return None
        routes = body.get("routes", [])
        if not routes:
            return None
        meters = routes[0].get("distance")
        if meters is None:
            return None
        return round(float(meters) / 1000, 2)
    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError):
        return None


def _build_distance_rows(
    manufacturers: list[Manufacturer],
    initial_geocode_cache: dict[str, tuple[float, float]] | None = None,
) -> tuple[
    list[tuple[str, str, str, str, str, str, float]],
    dict[str, tuple[float, float] | None],
    dict[str, str],
]:
    geocode_cache: dict[str, tuple[float, float] | None] = dict(
        initial_geocode_cache or {}
    )
    geocode_errors: dict[str, str] = {}

    fabrics = [m for m in manufacturers if m.role_group == "fabric"]
    garments = [m for m in manufacturers if m.role_group == "garment"]
    finishing = [m for m in manufacturers if m.role_group == "finishing"]

    rows: list[tuple[str, str, str, str, str, str, float]] = []

    # fabric -> garment
    for src in fabrics:
        src_coords = _geocode(src.location, geocode_cache, geocode_errors)
        if src_coords is None:
            continue
        for dst in garments:
            dst_coords = _geocode(dst.location, geocode_cache, geocode_errors)
            if dst_coords is None:
                continue
            distance = _distance_km(src_coords, dst_coords)
            if distance is None:
                continue
            rows.append(
                (
                    src.company,
                    src.role_group,
                    src.location,
                    dst.company,
                    dst.role_group,
                    dst.location,
                    distance,
                )
            )

    # garment -> finishing
    for src in garments:
        src_coords = _geocode(src.location, geocode_cache, geocode_errors)
        if src_coords is None:
            continue
        for dst in finishing:
            dst_coords = _geocode(dst.location, geocode_cache, geocode_errors)
            if dst_coords is None:
                continue
            distance = _distance_km(src_coords, dst_coords)
            if distance is None:
                continue
            rows.append(
                (
                    src.company,
                    src.role_group,
                    src.location,
                    dst.company,
                    dst.role_group,
                    dst.location,
                    distance,
                )
            )

    return rows, geocode_cache, geocode_errors


def sync_manufacturer_distances_if_changed() -> dict:
    """Recompute and store manufacturer distances if CSV changed."""
    if not CSV_PATH.exists():
        return {"updated": False, "reason": "csv_missing"}

    csv_hash = _csv_sha256(CSV_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM sync_state WHERE key = ?", (SYNC_HASH_KEY,))
    existing = cursor.fetchone()
    if existing and existing[0] == csv_hash:
        cursor.execute("SELECT COUNT(*) FROM manufacturer_distances")
        existing_count = int(cursor.fetchone()[0])
        if existing_count > 0:
            conn.close()
            return {"updated": False, "reason": "unchanged"}

    manufacturers = _load_manufacturers(CSV_PATH)
    fabrics = [m for m in manufacturers if m.role_group == "fabric"]
    garments = [m for m in manufacturers if m.role_group == "garment"]
    finishing = [m for m in manufacturers if m.role_group == "finishing"]
    expected_pairs = (len(fabrics) * len(garments)) + (len(garments) * len(finishing))
    db_geocode_cache = _load_geocode_cache_from_db(cursor)
    distance_rows, geocode_cache, geocode_errors = _build_distance_rows(
        manufacturers, initial_geocode_cache=db_geocode_cache
    )
    _persist_geocode_cache_to_db(cursor, geocode_cache)
    unresolved_locations = [
        location for location, coords in geocode_cache.items() if coords is None
    ]

    cursor.execute("DELETE FROM manufacturers")
    cursor.executemany(
        """
        INSERT INTO manufacturers (company, role, role_group, location)
        VALUES (?, ?, ?, ?)
        """,
        [(m.company, m.role, m.role_group, m.location) for m in manufacturers],
    )

    cursor.execute("DELETE FROM manufacturer_distances")
    if expected_pairs > 0 and not distance_rows:
        conn.commit()
        conn.close()
        return {
            "updated": False,
            "reason": "distance_resolution_failed",
            "manufacturers": len(manufacturers),
            "expected_pairs": expected_pairs,
            "geocoded_locations": len(geocode_cache) - len(unresolved_locations),
            "unresolved_locations": unresolved_locations[:5],
            "geocode_errors": {
                loc: geocode_errors.get(loc, "unknown")
                for loc in unresolved_locations[:3]
            },
        }

    if distance_rows:
        cursor.executemany(
            """
            INSERT INTO manufacturer_distances (
                source_company,
                source_role_group,
                source_location,
                destination_company,
                destination_role_group,
                destination_location,
                distance_km
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            distance_rows,
        )

    cursor.execute(
        """
        INSERT INTO sync_state (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (SYNC_HASH_KEY, csv_hash),
    )
    conn.commit()
    conn.close()

    return {
        "updated": True,
        "manufacturers": len(manufacturers),
        "distances": len(distance_rows),
        "geocoded_locations": len(geocode_cache) - len(unresolved_locations),
        "unresolved_locations": unresolved_locations[:5],
        "geocode_errors": {
            loc: geocode_errors.get(loc, "unknown") for loc in unresolved_locations[:3]
        },
    }
