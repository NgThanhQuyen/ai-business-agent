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
def get_all_serpapi_keys() -> list[str]:
    keys = []
    # 1. Thử lấy danh sách API keys từ settings.SERPAPI_KEYS (ngăn cách bằng dấu phẩy)
    if hasattr(settings, "SERPAPI_KEYS") and settings.SERPAPI_KEYS:
        for k in settings.SERPAPI_KEYS.split(","):
            val = k.strip()
            if val and val not in keys:
                keys.append(val)
                
    # 2. Thử lấy từ settings.SERPAPI_KEY
    if settings.SERPAPI_KEY:
        for k in settings.SERPAPI_KEY.split(","):
            val = k.strip()
            if val and val not in keys:
                keys.append(val)
        
    return keys


def safe_serpapi_search(params: dict) -> dict:
    """
    Thực hiện truy vấn SerpAPI sử dụng GoogleSearch.
    Hỗ trợ cơ chế tự động quay vòng API keys khi có key bị giới hạn lượt gọi (rate limit) hoặc lỗi.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    keys = get_all_serpapi_keys()
    if not keys:
        raise RuntimeError("No SerpAPI keys configured. Please configure SERPAPI_KEY or SERPAPI_KEYS.")
        
    last_error_msg = ""
    for k in keys:
        try:
            # Ẩn bớt ký tự API key để đảm bảo an toàn bảo mật khi ghi log
            masked_key = k[:10] + "..." if k else "None"
            logger.info(f"Attempting SerpAPI query with key: {masked_key} on engine: {params.get('engine')}")
            
            # Sao chép tham số để tránh thay đổi trực tiếp trên dictionary gốc truyền vào
            query_params = dict(params)
            query_params["api_key"] = k
            
            search = GoogleSearch(query_params)
            results = search.get_dict()
            
            # Nếu kết quả phản hồi chứa lỗi, ném ra ngoại lệ để chuyển sang thử key tiếp theo
            if "error" in results:
                err_msg = results["error"]
                logger.warning(f"SerpAPI returned error using key {masked_key}: {err_msg}")
                last_error_msg = err_msg
                continue
                
            return results
        except Exception as e:
            logger.warning(f"SerpAPI query failed using key {k[:10]}...: {e}")
            last_error_msg = str(e)
            continue
            
    raise RuntimeError(f"All SerpAPI keys failed to execute query. Last error: {last_error_msg}")


def search_businesses(keyword: str, location: str, max_results: int = 100) -> list[dict]:
    """
    Tìm kiếm các doanh nghiệp sử dụng Google Maps thông qua SerpAPI.
    Sử dụng phân trang (start) để thu thập đủ số lượng kết quả yêu cầu.
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
            "type": "search",
            "start": start,
        }

        try:
            results = safe_serpapi_search(params)
        except Exception as err:
            import logging
            logging.getLogger(__name__).error(f"SerpAPI search failed: {err}")
            break

        if "place_results" in results:
            place = results["place_results"]
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
            break

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

        # Ngăn chặn vòng lặp vô hạn nếu phân trang trả về kết quả trùng lặp hoặc hết trang dữ liệu.
        if added_this_page == 0 or len(local_results) < 20:
            break

        start += 20

    return businesses

def fetch_reviews_for_place(data_id: str, place_id: str = None) -> list[str]:
    """
    Thu thập tối đa 5 đánh giá thực tế từ người dùng cho một địa điểm thông qua SerpAPI.
    """
    if not data_id and not place_id:
        return []
    try:
        params = {
            "engine": "google_maps_reviews",
        }
        if data_id:
            params["data_id"] = data_id
        else:
            params["place_id"] = place_id
            
        results = safe_serpapi_search(params)
        reviews_data = results.get("reviews", [])
        
        review_texts = []
        for r in reviews_data:
            text = r.get("snippet") or r.get("text")
            if text and len(text.strip()) >= 15:
                review_texts.append(text.strip().replace("\n", " "))
        return review_texts[:5]
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to fetch reviews for place (data_id={data_id}, place_id={place_id}): {e}")
        return []

