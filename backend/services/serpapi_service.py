from serpapi import GoogleSearch
from core.config import settings

def clean_and_localize_location(location_str: str) -> str:
    if not location_str:
        return ""
    loc_lower = location_str.lower().strip()
    
    tphcm_aliases = {"tphcm", "tp.hcm", "tp hcm", "sai gon", "saigon", "ho chi minh", "hồ chí minh", "thành phố hồ chí minh"}
    if loc_lower in tphcm_aliases:
        return "Hồ Chí Minh, Việt Nam"
        
    hcm_districts = {
        "quan 1": "Quận 1", "quan 2": "Quận 2", "quan 3": "Quận 3", "quan 4": "Quận 4",
        "quan 5": "Quận 5", "quan 6": "Quận 6", "quan 7": "Quận 7", "quan 8": "Quận 8",
        "quan 9": "Quận 9", "quan 10": "Quận 10", "quan 11": "Quận 11", "quan 12": "Quận 12",
        "binh tan": "Bình Tân", "binh thanh": "Bình Thạnh", "go vap": "Gò Vấp",
        "phu nhuan": "Phú Nhuận", "tan binh": "Tân Bình", "tan phu": "Tân Phú",
        "thu duc": "Thủ Đức", "binh chanh": "Bình Chánh", "can gio": "Cần Giờ",
        "cu chi": "Củ Chi", "hoc mon": "Hóc Môn", "nha be": "Nhà Bè"
    }
    
    for key, val in hcm_districts.items():
        if key in loc_lower or val.lower() in loc_lower:
            return f"{val}, Hồ Chí Minh, Việt Nam"
            
    if "vietnam" not in loc_lower and "việt nam" not in loc_lower:
        return f"{location_str}, Việt Nam"
    return location_str

def search_businesses(keyword: str, location: str, max_results: int = 100) -> list[dict]:
    """
    Search for businesses using Google Maps with SerpAPI.
    Attempts pagination via `start` to collect up to `max_results`.
    """
    max_results = max(1, min(max_results, 100))

    businesses = []
    seen_keys = set()
    start = 0
    
    localized_location = clean_and_localize_location(location)

    while len(businesses) < max_results:
        params = {
            "engine": "google_maps",
            "q": f"{keyword} in {localized_location}",
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
                "place_id": place.get("place_id"),
                "data_id": place.get("data_id"),
            })
            added_this_page += 1

            if len(businesses) >= max_results:
                break

        # Prevent infinite loops if pagination returns duplicates.
        if added_this_page == 0 or len(local_results) < 20:
            break

        start += 20

    return businesses

def fetch_reviews_for_place(data_id: str, place_id: str = None) -> list[str]:
    """
    Fetch up to 5 real reviews for a place using SerpAPI.
    """
    if not data_id and not place_id:
        return []
    try:
        params = {
            "engine": "google_maps_reviews",
            "api_key": settings.SERPAPI_KEY,
        }
        if data_id:
            params["data_id"] = data_id
        else:
            params["place_id"] = place_id
            
        search = GoogleSearch(params)
        results = search.get_dict()
        reviews_data = results.get("reviews", [])
        
        review_texts = []
        for r in reviews_data:
            text = r.get("text")
            if text and len(text.strip()) >= 15:
                review_texts.append(text.strip().replace("\n", " "))
        return review_texts[:5]
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to fetch reviews for place (data_id={data_id}, place_id={place_id}): {e}")
        return []

