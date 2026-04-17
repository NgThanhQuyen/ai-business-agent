# AI Business Agent

AI Business Agent la ung dung full-stack ho tro tim kiem, lam sach va cham diem danh sach doanh nghiep tiem nang (lead generation) bang AI.

He thong ket hop:
- Thu thap du lieu doanh nghiep tu Google Maps thong qua SerpAPI.
- Xu ly va chuan hoa du lieu bang Pandas.
- Cham diem lead va tao insight bang Groq LLM.
- Hien thi ket qua qua dashboard React, ho tro xuat CSV/Excel.

## Highlights
- Live business search theo `keyword` + `location`.
- Data cleaning and deduplication pipeline.
- AI lead scoring (`0-100`) va ly do cham diem.
- AI insights de uu tien tiep can lead.
- Export du lieu sang `csv` hoac `excel`.

## System Architecture

```mermaid
flowchart LR
    U[User] --> FE[React Frontend]
    FE -->|POST /api/search| API[FastAPI Backend]
    API --> PIPE[Data Pipeline]
    PIPE --> SERP[SerpAPI Google Maps]
    PIPE --> CLEAN[Pandas Clean + Deduplicate]
    CLEAN --> LLM[Groq LLM Scoring + Insights]
    LLM --> DB[(PostgreSQL)]
    DB --> API
    API --> FE
    FE -->|GET /api/export| API
    API --> OUT[CSV / Excel Streaming]
```

## Tech Stack

### Backend
- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Pandas
- Groq SDK
- SerpAPI (`google-search-results`)

### Frontend
- React 18 + Vite
- TailwindCSS
- Recharts
- Axios

## Project Structure

```text
ai-business-agent/
|- backend/
|  |- main.py
|  |- requirements.txt
|  |- api/routes.py
|  |- core/config.py
|  |- database/
|  |  |- db.py
|  |  |- models.py
|  |  \- schemas.py
|  \- services/
|     |- data_pipeline.py
|     |- groq_service.py
|     |- serpapi_service.py
|     \- google_places.py
|- frontend/
|  |- index.html
|  |- package.json
|  |- tailwind.config.js
|  \- src/
|     |- App.jsx
|     |- api/axiosClient.js
|     \- components/
\- README.md
```

## Quick Start

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+

### 2. Clone Repository

```bash
git clone <your-repo-url>
cd ai-business-agent
```

### 3. Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Tao file `backend/.env`:

```env
DB_URL=postgresql://user:password@localhost:5432/ai_leads_db
SERPAPI_KEY=your_serpapi_key_here
GROQ_API_KEY=your_groq_api_key_here
```

Chay backend:

```bash
uvicorn main:app --reload
```

### 4. Frontend Setup

```bash
cd ../frontend
npm install
```

Tao file `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Chay frontend:

```bash
npm run dev
```

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check API |
| POST | `/api/search` | Chay full pipeline tim kiem + AI scoring + insights |
| GET | `/api/businesses` | Lay danh sach doanh nghiep da luu |
| GET | `/api/export?format=csv\|excel` | Xuat du lieu CSV hoac Excel |
| DELETE | `/api/businesses` | Xoa toan bo du lieu doanh nghiep |

### Sample Request: `POST /api/search`

```json
{
  "keyword": "coffee shop",
  "location": "Ha Noi",
  "min_rating": 4,
  "result_limit": 20
}
```

### Sample Response

```json
{
  "businesses": [
    {
      "id": 1,
      "name": "The Coffee House",
      "address": "123 Street",
      "phone": "0123...",
      "rating": 4.6,
      "review_count": 1520,
      "website": "https://...",
      "latitude": 21.0,
      "longitude": 105.8,
      "ai_score": 88,
      "ai_reason": "Danh gia cao, review on dinh, thong tin day du.",
      "created_at": "2026-04-17T12:00:00Z"
    }
  ],
  "insights": [
    "Nhom doanh nghiep rating tren 4.5 co ti le chuyen doi cao.",
    "Nhieu lead chat luong nhung chua co website."
  ]
}
```

## Data Pipeline
Pipeline xu ly du lieu trong backend duoc thuc hien theo cac buoc:
1. Fetch du lieu tu SerpAPI.
2. Clean du lieu (trim, ep kieu so, xu ly null).
3. Deduplicate theo `name + address`.
4. Feature engineering va ap dung bo loc (`min_rating`, `result_limit`).
5. AI scoring tung record va tong hop insights.
6. Upsert vao PostgreSQL.

## Security Notes
- Khong commit file `.env` len GitHub.
- Rotate API keys ngay lap tuc neu da lo.
- Khi deploy production, can gioi han `CORS allow_origins` theo domain that.

## Roadmap
- Add unit/integration tests.
- Add async queue/caching de giam do tre API ngoai.
- Add observability (structured logs, metrics).
- Nang cap chat luong danh gia AI voi bo tieu chi benchmark.

## License
MIT License
