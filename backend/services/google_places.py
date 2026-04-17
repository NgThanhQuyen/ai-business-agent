import requests
from core.config import settings

# ── Constants ────────────────────────────────────────────────────────────────
TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL     = "https://maps.googleapis.com/maps/api/place/details/json"
DETAIL_FIELDS   = "name,formatted_address,formatted_phone_number,rating,user_ratings_total,website,geometry"


# ── Helpers ───────────────────────────────────────────────────────────────────
def _text_search(query: str) -> list[dict]:
    """
    Call the Places Text Search endpoint.
    Handles up to 3 pages (60 results) via next_page_token.
    Returns a flat list of raw place stubs.
    """
    params  = {"query": query, "key": settings.GOOGLE_API_KEY}
    results = []

    for _ in range(3):                          # max 3 pages × 20 results = 60
        resp = requests.get(TEXT_SEARCH_URL, params=params, timeout=10)
        resp.raise_for_status()
        body = resp.json()

        results.extend(body.get("results", []))

        next_token = body.get("next_page_token")
        if not next_token:
            break

        # Google requires a short delay before next_page_token becomes valid
        import time
        time.sleep(2)
        params = {"pagetoken": next_token, "key": settings.GOOGLE_API_KEY}

    return results


def _get_place_details(place_id: str) -> dict:
    """
    Fetch enriched details for a single place_id.
    Returns the 'result' sub-dict from the API response.
    """
    params = {
        "place_id": place_id,
        "fields":   DETAIL_FIELDS,
        "key":      settings.GOOGLE_API_KEY,
    }
    resp = requests.get(DETAILS_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("result", {})


def _parse_place(detail: dict) -> dict:
    """
    Normalize a Place Details response into a flat dict
    that maps 1-to-1 with our BusinessCreate schema.
    """
    geo = detail.get("geometry", {}).get("location", {})
    return {
        "name":         detail.get("name"),
        "address":      detail.get("formatted_address"),
        "phone":        detail.get("formatted_phone_number"),
        "rating":       detail.get("rating"),
        "review_count": detail.get("user_ratings_total"),
        "website":      detail.get("website"),
        "latitude":     geo.get("lat"),
        "longitude":    geo.get("lng"),
    }


# ── Public API ────────────────────────────────────────────────────────────────
def fetch_businesses(keyword: str, location: str) -> list[dict]:
    """
    End-to-end fetch:
      1. Text-search for `keyword` in `location`.
      2. Retrieve details for each place.
      3. Return a list of normalised business dicts.

    Raises requests.HTTPError on any non-2xx API response.
    """
    query  = f"{keyword} in {location}"
    stubs  = _text_search(query)

    businesses = []
    for stub in stubs:
        place_id = stub.get("place_id")
        if not place_id:
            continue
        try:
            detail   = _get_place_details(place_id)
            parsed   = _parse_place(detail)
            businesses.append(parsed)
        except requests.HTTPError:
            # Skip individual places that fail — don't abort the whole batch
            continue

    return businesses