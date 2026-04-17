from serpapi import GoogleSearch
from core.config import settings

def search_businesses(keyword: str, location: str, max_results: int = 100) -> list[dict]:
    """
    Search for businesses using Google Maps with SerpAPI.
    Attempts pagination via `start` to collect up to `max_results`.
    """
    max_results = max(1, min(max_results, 100))

    businesses = []
    seen_keys = set()
    start = 0

    while len(businesses) < max_results:
        params = {
            "engine": "google_maps",
            "q": f"{keyword} in {location}",
            "api_key": settings.SERPAPI_KEY,
            "type": "search",
            "start": start,
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        local_results = results.get("local_results", [])
        if not local_results:
            break

        added_this_page = 0
        for place in local_results:
            key = place.get("place_id") or f"{place.get('title')}|{place.get('address')}"
            if key in seen_keys:
                continue
            seen_keys.add(key)

            gps = place.get("gps_coordinates", {})
            businesses.append({
                "name": place.get("title"),
                "address": place.get("address"),
                "phone": place.get("phone"),
                "rating": place.get("rating"),
                "review_count": place.get("reviews"),
                "website": place.get("website"),
                "latitude": gps.get("latitude"),
                "longitude": gps.get("longitude"),
            })
            added_this_page += 1

            if len(businesses) >= max_results:
                break

        # Prevent infinite loops if pagination returns duplicates.
        if added_this_page == 0 or len(local_results) < 20:
            break

        start += 20

    return businesses
