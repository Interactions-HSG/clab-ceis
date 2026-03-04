import os
import requests


def get_wiser_token():
    url = (
        "https://auth.wiser.ehealth.hevs.ch/realms/wiser/protocol/openid-connect/token"
    )
    payload = {
        "grant_type": "password",
        "client_id": "wiser-api-public",
        "username": os.getenv("WISER_SP3_API_USER", ""),
        "password": os.getenv("WISER_SP3_API_KEY", ""),
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        json = response.json()
        print(json["access_token"])
        return json["access_token"]
    except Exception as e:
        return str(e)


def get_emission_per_unit(token: str, activity_id: int) -> float | None:
    """
    Fetch emission per unit from Wiser for a given activity ID.

    Args:
        token: Bearer token for Wiser authentication.
        activity_id: The activity ID to fetch emissions for.

    Returns:
        Emission per unit in kg CO2eq, or None if unavailable.
    """
    activity_url = "https://api.wiser.ehealth.hevs.ch/ecoinvent/3.12-cutoff/activity/"
    url = f"{activity_url}{activity_id}/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        json_response = response.json()
    except Exception as e:
        print(f"Error fetching activity {activity_id}: {str(e)}")
        return None

    for item in json_response.get("lcia_results", []):
        if item.get("method", {}).get("name") == "IPCC 2021":
            return item.get("emissions")
    return None
