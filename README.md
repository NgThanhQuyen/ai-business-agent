# LeadSpyAI - AI Business Agent & Lead Analyzer

**LeadSpyAI** là một hệ thống thông minh hỗ trợ thu thập, phân tích dữ liệu doanh nghiệp địa phương và tìm kiếm thông tin bằng trí tuệ nhân tạo (AI). Hệ thống tích hợp khả năng cào dữ liệu từ Google Maps (qua SerpAPI), làm sạch và tối ưu hóa tập tin leads, lưu trữ vào cơ sở dữ liệu PostgreSQL, tạo vector hóa đánh giá của khách hàng (Embeddings) để thực hiện tìm kiếm ngữ nghĩa chuyên sâu và cung cấp trợ lý ảo phân tích số liệu bằng ngôn ngữ tự nhiên (SQL Agent).

---

## 🚀 Các Tính Năng Cốt Lõi

### 1. Pipeline Cào Dữ Liệu & Làm Sạch Tự Động
- **Cào dữ liệu địa điểm**: Tích hợp SerpAPI Google Maps để thu thập thông tin doanh nghiệp (Tên, địa chỉ, số điện thoại, đánh giá, số lượng reviews, website, tọa độ GPS).
- **Quy trình ETL với Pandas**: Tự động chuẩn hóa dữ liệu, xóa khoảng trắng thừa, điền giá trị thiếu và loại bỏ trùng lặp theo cặp `name + address`.
- **Tải Review thực tế**: Tự động quét và tải các review thực tế từ người dùng để làm cơ sở cho phân tích chất lượng ngữ nghĩa.

### 2. Tìm Kiếm Ngữ Nghĩa (/ai Semantic Search)
- **Vector Embeddings cục bộ**: Sử dụng mô hình `keepitreal/vietnamese-sbert` để vector hóa các bản tóm tắt đánh giá thực tế của doanh nghiệp.
- **Tìm kiếm tương đồng**: Thực hiện tìm kiếm khoảng cách Cosine trên PostgreSQL (hoặc dự phòng tính toán trực tiếp bằng Python-native) giúp tìm các doanh nghiệp khớp với các mô tả cảm quan (ví dụ: *"quán cà phê yên tĩnh để học bài"*, *"cửa hàng đồng hồ uy tín chính hãng"*).
- **Tóm tắt thông tin trung thực**: Groq LLM đọc các review thực tế và tạo phản hồi tư vấn có trích dẫn rõ ràng, tuân thủ nghiêm ngặt nguyên tắc không tự bịa đặt thông tin (Anti-hallucination).

### 3. Trợ Lý SQL Ngôn Ngữ Tự Nhiên (SQL Agent)
- **LangChain SQL Agent**: Cho phép người dùng trò chuyện, hỏi các câu hỏi thống lai phức tạp (ví dụ: *"Có bao nhiêu quán cafe trên 4.5 sao ở Gò Vấp?"*, *"Quán nào có AI score cao nhất?"*).
- **Tự động chuyển ngữ tự nhiên sang SQL**: Tự động sinh truy vấn SQL tối ưu trên CSDL PostgreSQL và trả về kết quả tiếng Việt ngắn gọn.

### 4. So Sánh Đối Thủ Chi Tiết (Competitor Comparison)
- **So sánh đối đầu**: Cho phép chọn chính xác 2 doanh nghiệp từ danh sách để tiến hành so sánh thông số và review thực tế.
- **AI Agent phân tích**: Endpoint `/api/compare` sử dụng Groq LLM `llama-3.3-70b-versatile` để tổng hợp, liệt kê chi tiết tối đa 3 điểm mạnh, 3 điểm yếu của từng quán cùng phân tích đối chiến lược và phán quyết khuyên dùng của chuyên gia.
- **Tự động cào review on-the-fly**: Nếu doanh nghiệp được chọn chưa có sẵn tóm tắt review trong DB, hệ thống tự động kích hoạt SerpAPI để cào thông tin review trực tiếp (hỗ trợ cả trường hợp redirect của single place result).

### 5. Báo cáo PDF Tích Hợp Insights AI (PDF Market Report)
- **AI Report Generator**: Endpoint `/api/report-insights` gọi Groq LLM phân tích tổng quan thị trường, tìm ra các cơ hội & khoảng trống (Market Gaps) và đề xuất 3 kịch bản Telesales phù hợp cho danh sách Lead.
- **Hộp thoại (Modal) báo cáo trực quan**: Tích hợp số liệu thống kê chính, các biểu đồ phân bổ điểm đánh giá & review (Recharts), bảng Lead chi tiết và các nhận xét chiến lược từ AI.
- **Hai chế độ xuất file PDF chuyên nghiệp**:
  - **Tải PDF**: Client-side rendering sử dụng `html2pdf.js` (sửa lỗi lệch/trắng trang khi màn hình đang cuộn bằng cách ép gốc tọa độ scrollX/Y về 0).
  - **In / Lưu PDF**: Tạo luồng tài liệu vector sắc nét, tự động mở hộp thoại in của hệ điều hành để lưu PDF chất lượng cao.

### 6. Cơ Chế Quay Vòng API Keys (API Key Rotation) & Fallback
- **Tự động xoay vòng khóa**: Cho phép nhập danh sách nhiều khóa API trong các biến `.env` (ngăn cách bằng dấu phẩy). Hệ thống tự động bắt các lỗi rate limit (429) hoặc sai khóa (401) để chuyển sang khóa tiếp theo của SerpAPI và Groq.
- **Hạ cấp mô hình dự phòng (Model Fallback)**: Khi mô hình Groq chính gặp sự cố, hệ thống tự động hạ cấp xuống `llama-3.1-8b-instant` để tiếp tục thực hiện tác vụ mà không bị gián đoạn.

### 7. Dashboard Hiện Đại, Trực Quan & Việt Hóa Chú Thích
- Giao diện chia màn hình **7/3** tối ưu với thiết kế Glassmorphism hiện đại, biểu đồ tương tác Recharts, bản đồ Leaflet ghim tọa độ thực địa.
- Hỗ trợ xuất dữ liệu ra file **CSV** hoặc **Excel** tùy biến (cho phép tải toàn bộ hoặc lọc theo danh sách ID cụ thể).
- **Việt hóa chú thích**: Toàn bộ chú thích mã nguồn trong các tệp `.py` và `.jsx` đều được Việt hóa có dấu chuẩn chỉ, không dùng icon/emoji, giúp mã nguồn luôn sạch đẹp, dễ bảo trì.

---

## 📐 Kiến Trúc Hệ Thống

```mermaid
flowchart TD
    U[User / Khách hàng] -->|Yêu cầu tìm kiếm / Hỏi đáp| FE[React Frontend]
    FE -->|POST /api/search| API[FastAPI Backend]
    
    subgraph Backend Services
        API -->|Khởi chạy Task nền| PIPE[Data Pipeline]
        PIPE -->|Scraping| SERP[SerpAPI Google Maps]
        PIPE -->|Làm sạch dữ liệu| PD[Pandas Clean & Deduplicate]
        PIPE -->|Chấm điểm AI & Insights| Groq[Groq Service Fallback]
        
        API -->|Yêu cầu /ai| SEM[Semantic Agent]
        SEM -->|Tạo vector| SBERT[SentenceTransformer Local]
        
        API -->|Hỏi đáp SQL| SQL[LangChain SQL Agent]
    end
    
    PD & Groq & SEM -->|Đồng bộ dữ liệu| DB[(PostgreSQL)]
    SQL -->|Truy vấn dữ liệu| DB
    
    API -->|Cập nhật trạng thái| REDIS[(Redis Cache & Task Status)]
    REDIS <.-> FE
    
    API -->|Xuất báo cáo| EXP[CSV / Excel Writer]
    EXP -->|Tải xuống| U
```

---

## 📂 Cấu Trúc Thư Mục Dự Án

```text
ai-business-agent/
├── backend/
│   ├── main.py                  # Điểm khởi chạy ứng dụng FastAPI
│   ├── requirements.txt         # Các thư viện Python cần thiết
│   ├── api/
│   │   └── routes.py            # Định nghĩa các API endpoints (/search, /chat-agent, /export,...)
│   ├── core/
│   │   └── config.py            # Cấu hình biến môi trường và cài đặt dự án
│   ├── database/
│   │   ├── db.py                # Thiết lập kết nối SQLAlchemy engine & session
│   │   ├── db_migration.py      # Script khởi tạo database và cập nhật embeddings review thực tế
│   │   ├── models.py            # Định nghĩa các bảng ORM (hỗ trợ SafeVector cho pgvector/text)
│   │   ├── redis_client.py      # Tích hợp Redis cache và quản lý task status
│   │   └── schemas.py           # Pydantic schemas kiểm tạo dữ liệu vào/ra
│   └── services/
│       ├── data_pipeline.py     # Master pipeline xử lý ETL (Tải, lọc, chấm điểm, lưu DB)
│       ├── groq_service.py      # Tích hợp Groq API, thiết lập hàm safe_groq_chat_completion dự phòng
│       ├── semantic_agent.py    # Xử lý Vector Similarity Search, trích xuất tham số và đề xuất tư vấn
│       ├── serpapi_service.py   # Kết nối SerpAPI tìm kiếm địa điểm và cào reviews của doanh nghiệp
│       ├── smart_chat_service.py# Router chính của hội thoại, điều hướng truy vấn SQL và phân loại Intent
│       └── sql_agent.py         # Cấu hình SQL Agent cơ bản kết nối với database
├── frontend/
│   ├── index.html               # Trang HTML chính của ứng dụng
│   ├── package.json             # Danh sách thư viện và scripts npm
│   ├── tailwind.config.js       # Cấu hình giao diện TailwindCSS
│   ├── vite.config.js           # Cấu hình công cụ bundler Vite
│   └── src/
│       ├── App.jsx              # Entry component chính, căn chỉnh bố cục rộng và responsive
│       ├── index.css            # File chứa các tùy biến CSS toàn cục
│       ├── main.jsx             # Render React app vào DOM
│       ├── api/
│       │   └── axiosClient.js   # Cấu hình Axios gọi API backend
│       ├── components/
│       │   ├── AIInsights.jsx   # Card hiển thị các đề xuất phân tích thông minh từ AI
│       │   ├── BusinessMap.jsx  # Bản đồ Leaflet tương tác ghim các doanh nghiệp trên thực địa
│       │   ├── ChatAgent.jsx    # Khung chat chia 7/3, hỗ trợ xem hội thoại rộng và hướng dẫn sử dụng
│       │   ├── Dashboard.jsx    # Dashboard chính gồm biểu đồ phân tích và bảng số liệu
│       │   ├── DataTable.jsx    # Bảng dữ liệu doanh nghiệp, hỗ trợ phân trang và tìm kiếm nhanh
│       │   └── SearchForm.jsx   # Form thiết lập cào dữ liệu Google Maps
│       └── utils/
│           └── mapHelpers.js    # Tiện ích bổ trợ tính toán cho bản đồ
└── README.md                    # Tài liệu hướng dẫn sử dụng dự án
```

---

## 🛠️ Hướng Dẫn Cài Đặt & Chạy Dự Án

### Yêu Cầu Hệ Thống
- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL 14+** (Nếu có tiện ích mở rộng `pgvector` sẽ tối ưu hơn, nếu không hệ thống tự động fallback sang tính khoảng cách Cosine bằng Python-native).
- **Redis Server** (để quản lý cache và tiến trình bất đồng bộ).

---

### 1. Thiết Lập Backend

1. Di chuyển vào thư mục backend:
   ```bash
   cd backend
   ```

2. Tạo môi trường ảo và cài đặt thư viện:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate

   pip install -r requirements.txt
   ```

3. Tạo file cấu hình biến môi trường `backend/.env` với nội dung:
   ```env
    # Cấu hình CSDL PostgreSQL
    DB_URL=postgresql://postgres:yourpassword@localhost:5432/ai_leads_db
    
    # Hỗ trợ danh sách API Keys phân tách bằng dấu phẩy để tự động quay vòng khi hết hạn mức
    SERPAPI_KEY=serpapi_key1,serpapi_key2
    GROQ_API_KEY=groq_key1,groq_key2
    
    # Cấu hình Redis
    REDIS_HOST=localhost
    REDIS_PORT=6379
   ```

4. Khởi tạo cơ sở dữ liệu và sinh vector embeddings mẫu cho reviews thực tế:
   ```bash
   python database/db_migration.py
   ```

5. Khởi chạy server backend FastAPI:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   *Tài liệu API Swagger tự động sẽ khả dụng tại: `http://localhost:8000/docs`*

---

### 2. Thiết Lập Frontend

1. Di chuyển vào thư mục frontend:
   ```bash
   cd ../frontend
   ```

2. Cài đặt các gói phụ thuộc:
   ```bash
   npm install
   ```

3. Tạo file cấu hình biến môi trường `frontend/.env`:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```

4. Khởi chạy máy chủ phát triển frontend:
   ```bash
   npm run dev
   ```
   *Ứng dụng web sẽ khả dụng tại địa chỉ: `http://localhost:5173` (hoặc `http://localhost:5174` nếu cổng mặc định bị chiếm).*

---

## 🔌 Danh Sách API Endpoints

| Phương thức | Endpoint | Mô tả |
| :--- | :--- | :--- |
| **POST** | `/api/search` | Bắt đầu tác vụ cào dữ liệu Google Maps không đồng bộ (nhận về `task_id`). |
| **GET** | `/api/tasks/{task_id}` | Kiểm tra trạng thái (%) và kết quả của tác vụ cào dữ liệu từ Redis. |
| **POST** | `/api/chat-agent` | Điểm nhận tin nhắn chat (Tự động định tuyến tìm kiếm ngữ nghĩa `/ai` hoặc SQL Agent). |
| **GET** | `/api/businesses` | Lấy danh sách toàn bộ doanh nghiệp đang được lưu trữ trong CSDL. |
| **GET** | `/api/export?format=csv\|excel&ids=1,2` | Trích xuất toàn bộ hoặc theo danh sách ID doanh nghiệp và tải về dưới dạng file CSV/Excel. |
| **POST** | `/api/compare` | So sánh đối đầu chi tiết 2 đối thủ cạnh tranh bằng AI Agent. |
| **POST** | `/api/report-insights` | Tạo insights báo cáo phân tích thị trường tổng quan và đề xuất telesales. |
| **DELETE** | `/api/businesses` | Xóa sạch dữ liệu doanh nghiệp trong cơ sở dữ liệu để cào mới. |

---

## 💡 Hướng Dẫn Sử Dụng Trên Giao Diện Chat

Trên ô chat của **LeadSpyAI**, bạn có thể sử dụng các cú pháp sau để tương tác với kho dữ liệu:

1. **Tìm kiếm ngữ nghĩa (Semantic Vector Search)**: Bắt đầu tin nhắn bằng tiền tố `/ai` để tìm kiếm thông minh bám sát theo review thực tế.
   - *Ví dụ:* `/ai quán cà phê có không gian yên tĩnh thích hợp học tập học bài`
   - *Ví dụ:* `/ai cửa hàng đồng hồ uy tín chính hãng nhân viên nhiệt tình`
2. **Kích hoạt cào dữ liệu qua ô Chat**:
   - *Ví dụ:* `tìm kiếm google map quán cafe ở Quận 1`
   - *Ví dụ:* `bật tìm kiếm cào dữ liệu spa ở Gò Vấp`
3. **Thống kê / Phân tích số liệu (SQL Agent)**:
   - *Ví dụ:* `Có bao nhiêu doanh nghiệp có rating trên 4.5 sao ở Quận 3?`
   - *Ví dụ:* `Quán cafe nào có điểm AI score cao nhất tại Bình Thạnh?`

---

## 🛡️ Bản quyền & Giấy phép
Hệ thống được phát hành dưới giấy phép **MIT License**.
