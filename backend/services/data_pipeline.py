import pandas as pd


# ── Step 1: Load ──────────────────────────────────────────────────────────────
def load_to_dataframe(raw_records: list[dict]) -> pd.DataFrame:
    """Convert the raw list of business dicts into a DataFrame."""
    return pd.DataFrame(raw_records)


# ── Step 2: Clean ─────────────────────────────────────────────────────────────
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Drop rows missing both `name` and `address` (unusable records).
    - Strip leading/trailing whitespace from all string columns.
    - Fill missing optional strings with None (not NaN) for clean JSON output.
    """
    if df.empty:
        return df

    # Must-have: name
    df = df.dropna(subset=["name"])

    # Strip whitespace on string columns
    str_cols = df.select_dtypes(include="object").columns
    for col in str_cols:
        df[col] = df[col].str.strip()

    # Replace empty strings with None
    df = df.replace({"": None})

    # Ensure numeric columns have sensible types (coerce bad values to NaN)
    df["rating"]       = pd.to_numeric(df["rating"],       errors="coerce")
    df["review_count"] = pd.to_numeric(df["review_count"], errors="coerce")
    df["latitude"]     = pd.to_numeric(df["latitude"],     errors="coerce")
    df["longitude"]    = pd.to_numeric(df["longitude"],    errors="coerce")

    return df


# ── Step 3: Deduplicate ───────────────────────────────────────────────────────
def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate businesses.
    Primary key: (name, address) — case-insensitive comparison.
    Falls back to name-only dedup when address is missing.
    """
    if df.empty:
        return df

    df["_name_key"]    = df["name"].str.lower().str.strip()
    df["_address_key"] = df["address"].str.lower().str.strip() if "address" in df.columns else ""

    df = df.drop_duplicates(subset=["_name_key", "_address_key"], keep="first")
    df = df.drop(columns=["_name_key", "_address_key"])

    return df


# ── Step 4: Feature Engineering ───────────────────────────────────────────────
def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Round `rating` to 1 decimal place for consistent display.
    - Cast `review_count` to nullable Int64 so it serialises as int (not float).
    - Add `rating_label` convenience column: Poor / Average / Good / Excellent.
    """
    if df.empty:
        return df

    # Round rating
    df["rating"] = df["rating"].round(1)

    # Ensure review_count is a proper integer (pandas nullable Int64 handles NaN)
    df["review_count"] = df["review_count"].astype("Int64")

    # Rating label for dashboard grouping
    def _label(r):
        if pd.isna(r):       return "No Rating"
        if r < 3.0:          return "Poor (< 3)"
        if r < 4.0:          return "Average (3–4)"
        if r < 4.5:          return "Good (4–4.5)"
        return               "Excellent (4.5+)"

    df["rating_label"] = df["rating"].apply(_label)

    return df


# ── Step 5: Finalise ──────────────────────────────────────────────────────────
def to_records(df: pd.DataFrame) -> list[dict]:
    """
    Convert DataFrame back to a list of dicts suitable for Pydantic / SQLAlchemy.
    - Drop the helper `rating_label` column (not in the DB schema).
    - Convert pandas NA → Python None so JSON serialisation works cleanly.
    """
    export_cols = ["name", "address", "phone", "rating",
                   "review_count", "website", "latitude", "longitude"]

    # Keep only columns that exist (guard against empty frames)
    existing = [c for c in export_cols if c in df.columns]
    df = df[existing].copy()

    # pandas NA / NaN → None
    df = df.where(pd.notna(df), other=None)

    # Int64 → plain Python int (JSON-serialisable)
    if "review_count" in df.columns:
        df["review_count"] = df["review_count"].apply(
            lambda x: int(x) if pd.notna(x) else None
        )

    return df.to_dict(orient="records")


# ── Master Pipeline ───────────────────────────────────────────────────────────
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
    Execute all pipeline stages:
    1. Fetch from SerpAPI
    2. Clean with Pandas
    3. AI Scoring with Groq
    4. Generate Insights
    """
    try:
        if task_id:
            set_task_status(task_id, "processing", 10, "Bắt đầu cào dữ liệu từ SerpAPI...")
        
        # 1. Fetch Data
        raw_records = search_businesses(keyword, location, max_results=100)
        if not raw_records:
            if task_id:
                set_task_status(task_id, "completed", 100, "Không tìm thấy dữ liệu.", {"records": [], "insights": []})
            return [], []
            
        if task_id:
            set_task_status(task_id, "processing", 40, f"Đã lấy {len(raw_records)} kết quả. Đang làm sạch dữ liệu...")
            
        # 2. Clean & Deduplicate 
        df = load_to_dataframe(raw_records)
        df = clean_data(df)
        df = deduplicate(df)
        df = feature_engineering(df)
        clean_records = to_records(df)

        # 2.1 Optional rating filter (strictly greater than threshold)
        if min_rating is not None:
            clean_records = [
                r for r in clean_records
                if r.get("rating") is not None and r["rating"] > min_rating
            ]

        # 2.2 Result cap: user-defined limit or default maximum of 100.
        if result_limit is not None:
            clean_records = clean_records[:result_limit]
        else:
            clean_records = clean_records[:100]

        if not clean_records:
            if task_id:
                set_task_status(task_id, "completed", 100, "Không có dữ liệu sau khi lọc.", {"records": [], "insights": []})
            return [], []
        
        if task_id:
            set_task_status(task_id, "processing", 60, f"Đang chấm điểm AI cho {len(clean_records)} doanh nghiệp...")
            
        # 3. AI Scoring
        for record in clean_records:
            ai_result = score_lead(record)
            record["ai_score"] = ai_result.get("score", 0)
            record["ai_reason"] = ai_result.get("reason", "")
            
        if task_id:
            set_task_status(task_id, "processing", 80, "Đang tạo Insights (phân tích tổng quan)...")
            
        # 4. Generate Insights
        insights = generate_insights(clean_records)
        
        if task_id:
            set_task_status(task_id, "completed", 100, "Hoàn tất pipeline!", {"records": clean_records, "insights": insights})
            
        return clean_records, insights
    except Exception as e:
        if task_id:
            set_task_status(task_id, "failed", 0, f"Lỗi: {str(e)}")
        raise e