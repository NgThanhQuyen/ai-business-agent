import pandas as pd


# Bước 1: Tải dữ liệu vào Pandas DataFrame
def load_to_dataframe(raw_records: list[dict]) -> pd.DataFrame:
    """Chuyển đổi danh sách dữ liệu thô (dicts) của các doanh nghiệp thành DataFrame."""
    return pd.DataFrame(raw_records)


# Bước 2: Làm sạch dữ liệu
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Loại bỏ các hàng thiếu trường tên (tên là bắt buộc).
    - Cắt bỏ khoảng trắng dư thừa ở đầu/cuối của các cột dữ liệu chuỗi.
    - Thay thế các chuỗi trống bằng None (không dùng NaN) để JSON đầu ra được sạch.
    """
    if df.empty:
        return df

    # Bắt buộc phải có tên
    df = df.dropna(subset=["name"])

    # Loại bỏ khoảng trắng ở các cột kiểu dữ liệu chuỗi (object)
    str_cols = df.select_dtypes(include="object").columns
    for col in str_cols:
        df[col] = df[col].str.strip()

    # Thay thế chuỗi rỗng bằng giá trị None
    df = df.replace({"": None})

    # Chuyển đổi các cột số về kiểu số hợp lệ (ép các giá trị sai định dạng về NaN)
    df["rating"]       = pd.to_numeric(df["rating"],       errors="coerce")
    df["review_count"] = pd.to_numeric(df["review_count"], errors="coerce")
    df["latitude"]     = pd.to_numeric(df["latitude"],     errors="coerce")
    df["longitude"]    = pd.to_numeric(df["longitude"],    errors="coerce")

    return df


# Bước 3: Loại bỏ trùng lặp dữ liệu
def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Loại bỏ các doanh nghiệp bị trùng lặp.
    Khóa chính để đối chiếu: cặp (tên, địa chỉ) - không phân biệt chữ hoa chữ thường.
    """
    if df.empty:
        return df

    df["_name_key"]    = df["name"].str.lower().str.strip()
    df["_address_key"] = df["address"].str.lower().str.strip() if "address" in df.columns else ""

    df = df.drop_duplicates(subset=["_name_key", "_address_key"], keep="first")
    df = df.drop(columns=["_name_key", "_address_key"])

    return df


# Bước 4: Chuẩn hóa và làm giàu thuộc tính (Feature Engineering)
def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Làm tròn rating đến 1 chữ số thập phân để hiển thị đồng nhất.
    - Ép kiểu cột review_count về Int64 của pandas (hỗ trợ giá trị rỗng/NaN) để tuần tự hóa JSON chuẩn.
    - Thêm cột phân loại rating_label hỗ trợ vẽ biểu đồ.
    """
    if df.empty:
        return df

    # Làm tròn điểm đánh giá (rating)
    df["rating"] = df["rating"].round(1)

    # Đảm bảo cột số review là kiểu số nguyên
    df["review_count"] = df["review_count"].astype("Int64")

    # Nhãn phân loại đánh giá để nhóm dữ liệu trên dashboard
    def _label(r):
        if pd.isna(r):       return "No Rating"
        if r < 3.0:          return "Poor (< 3)"
        if r < 4.0:          return "Average (3–4)"
        if r < 4.5:          return "Good (4–4.5)"
        return               "Excellent (4.5+)"

    df["rating_label"] = df["rating"].apply(_label)

    return df


# Bước 5: Hoàn tất cấu trúc bản ghi
def to_records(df: pd.DataFrame) -> list[dict]:
    """
    Chuyển đổi DataFrame trở lại danh sách các dictionary phù hợp để lưu DB hoặc trả về API.
    - Giữ lại các trường dữ liệu có trong cấu trúc DB.
    - Chuyển đổi các giá trị trống NA/NaN của pandas thành None của Python để tuần tự hóa JSON hoạt động tốt.
    """
    export_cols = ["name", "address", "phone", "rating",
                   "review_count", "website", "latitude", "longitude",
                   "place_id", "data_id"]

    # Chỉ giữ lại các cột thực tế tồn tại trong dataframe
    existing = [c for c in export_cols if c in df.columns]
    df = df[existing].copy()

    # Chuyển đổi các kiểu rỗng của pandas (NA, NaN) về giá trị None
    df = df.where(pd.notna(df), other=None)

    # Chuyển đổi kiểu Int64 của pandas về kiểu số nguyên thuần Python để JSON hóa tốt
    if "review_count" in df.columns:
        df["review_count"] = df["review_count"].apply(
            lambda x: int(x) if pd.notna(x) else None
        )

    return df.to_dict(orient="records")


# Quy trình xử lý dữ liệu chính (Master Pipeline)
from services.serpapi_service import search_businesses
from services.groq_service import score_lead, generate_insights
from database.redis_client import set_task_status

def run_pipeline(
    keyword: str,
    location: str,
    min_rating: float | None = None,
    result_limit: int | None = None,
    task_id: str | None = None,
) -> tuple[list[dict], list[str]]:
    """
    Khởi chạy toàn bộ quy trình:
    1. Gọi SerpAPI tìm kiếm địa điểm trên Google Maps.
    2. Sử dụng Pandas làm sạch dữ liệu và lọc trùng lặp.
    3. Sử dụng LLM Groq để phân tích chấm điểm từng địa điểm.
    4. Tạo insights phân tích thị trường tổng quan.
    """
    try:
        if task_id:
            set_task_status(task_id, "processing", 10, "Bắt đầu cào dữ liệu từ SerpAPI...")
        
        # 1. Gọi API thu thập dữ liệu doanh nghiệp
        raw_records = search_businesses(keyword, location, max_results=100)
        if not raw_records:
            if task_id:
                set_task_status(task_id, "completed", 100, "Không tìm thấy dữ liệu.", {"businesses": [], "insights": []})
            return [], []
            
        if task_id:
            set_task_status(task_id, "processing", 40, f"Đã lấy {len(raw_records)} kết quả. Đang làm sạch dữ liệu...")
            
        # 2. Thực hiện làm sạch dữ liệu, chuẩn hóa cấu trúc và loại bỏ trùng lặp
        df = load_to_dataframe(raw_records)
        df = clean_data(df)
        df = deduplicate(df)
        df = feature_engineering(df)
        clean_records = to_records(df)

        # 2.1 Lọc theo điểm đánh giá tối thiểu (chỉ giữ lại các doanh nghiệp có rating lớn hơn min_rating)
        if min_rating is not None:
            clean_records = [
                r for r in clean_records
                if r.get("rating") is not None and r["rating"] > min_rating
            ]

        # 2.2 Giới hạn số lượng bản ghi trả về theo yêu cầu của người dùng (mặc định lấy 100)
        if result_limit is not None:
            clean_records = clean_records[:result_limit]
        else:
            clean_records = clean_records[:100]

        if not clean_records:
            if task_id:
                set_task_status(task_id, "completed", 100, "Không có dữ liệu sau khi lọc.", {"businesses": [], "insights": []})
            return [], []
        
        if task_id:
            set_task_status(task_id, "processing", 60, f"Đang chấm điểm AI cho {len(clean_records)} doanh nghiệp...")
            
        # 3. Sử dụng AI để chấm điểm tiềm năng (AI Scoring)
        for record in clean_records:
            ai_result = score_lead(record)
            record["ai_score"] = ai_result.get("score", 0)
            record["ai_reason"] = ai_result.get("reason", "")
            
        if task_id:
            set_task_status(task_id, "processing", 80, "Đang tạo Insights (phân tích tổng quan)...")
            
        # 4. Sử dụng AI để tạo các nhận xét phân tích thị trường (Market Insights)
        insights = generate_insights(clean_records)
        
        if task_id:
            set_task_status(task_id, "processing", 80, "Đang đồng bộ cơ sở dữ liệu và tải review...", {"records": clean_records, "insights": insights})
            
        return clean_records, insights
    except Exception as e:
        if task_id:
            set_task_status(task_id, "failed", 0, f"Lỗi: {str(e)}")
        raise e