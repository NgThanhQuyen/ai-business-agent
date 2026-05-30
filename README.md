# LeadSpyAI - AI Business Agent & Lead Analyzer

**LeadSpyAI** là một hệ thống thông minh hỗ trợ thu thập, phân tích dữ liệu doanh nghiệp địa phương và tìm kiếm thông tin bằng trí tuệ nhân tạo (AI). Hệ thống tích hợp khả năng cào dữ liệu từ Google Maps (qua SerpAPI), làm sạch và tối ưu hóa tập tin leads, lưu trữ vào cơ sở dữ liệu PostgreSQL, tạo vector hóa đánh giá của khách hàng (Embeddings) để thực hiện tìm kiếm ngữ nghĩa chuyên sâu và cung cấp trợ lý ảo phân tích số liệu bằng ngôn ngữ tự nhiên (SQL Agent).

---

## 🚀 Các Tính Năng Cốt Lõi

### 1. Pipeline Cào Dữ Liệu & Làm Sạch Tự Động
- **Cào dữ liệu địa điểm**: Tích hợp SerpAPI Google Maps để thu thập thông tin doanh nghiệp (Tên, địa chỉ, số điện thoại, đánh giá, số lượng reviews, website, tọa độ GPS).
- **Quy trình ETL với Pandas**: Tự động chuẩn hóa dữ liệu, xóa khoảng trắng thừa, điền giá trị thiếu và loại bỏ trùng lặp theo cặp `name + address`.
- **Tải Review & Phân Tích**: Tự động quét và tải các review thực tế từ người dùng để làm cơ sở phân tích chất lượng.

### 2. Tìm Kiếm Ngữ Nghĩa (/ai Semantic Search)
- **Vector Embeddings cục bộ**: Sử dụng mô hình `keepitreal/vietnamese-sbert` để vector hóa các bản tóm tắt đánh giá thực tế của doanh nghiệp.
- **Tìm kiếm tương đồng**: Thực hiện tìm kiếm khoảng cách Cosine trên PostgreSQL (hoặc fallback tính toán trực tiếp bằng Python-native) giúp tìm các doanh nghiệp khớp với các mô tả cảm quan (ví dụ: *"quán cà phê yên tĩnh để học bài"*, *"cửa hàng đồng hồ uy tín chính hãng"*).
- **Tóm tắt thông tin trung thực**: Groq LLM đọc các review thực tế và tạo phản hồi tư vấn có trích dẫn rõ ràng, tuân thủ nghiêm ngặt nguyên tắc không bịa đặt thông tin (Anti-hallucination).

### 3. Trợ Lý SQL Ngôn Ngữ Tự Nhiên (SQL Agent)
- **LangChain SQL Agent**: Cho phép người dùng trò chuyện, hỏi các câu hỏi thống kê phức tạp (ví dụ: *"Có bao nhiêu quán cafe trên 4.5 sao ở Gò Vấp?"*, *"Quán nào có AI score cao nhất?"*).
- **Tự động chuyển ngữ tự nhiên sang SQL**: Tự động sinh truy vấn SQL tối ưu trên CSDL PostgreSQL và trả về kết quả tiếng Việt ngắn gọn.

### 4. Đánh Giá Chất Lượng Lead & Insights Chuyên Sâu
- **Lead Scoring (0-100)**: Groq AI tự động chấm điểm chất lượng của từng lead dựa trên điểm đánh giá, số lượng review và việc có/không có website chính thức.
- **Market Insights**: Tự động tổng hợp và đưa ra 3-5 phân tích chiến lược về tập dữ liệu đã cào để hỗ trợ hoạt động sales/telesales.

### 5. Cơ Chế Dự Phòng Groq API (Model Fallback)
- **Tự động chuyển đổi mô hình (Fallback 429)**: Khi mô hình chính `llama-3.3-70b-versatile` đạt giới hạn lượt dùng trong ngày (Rate Limit TPD), hệ thống sẽ tự động bắt lỗi và chuyển hướng cuộc gọi API sang mô hình dự phòng `llama-3.1-8b-instant`.
- Cơ chế này cũng được tích hợp trực tiếp vào LangChain thông qua thuộc tính `.with_fallbacks()` cho SQL Agent, đảm bảo dịch vụ AI luôn hoạt động ổn định 24/7.

### 6. Caching & Quản Lý Tiến Trình Thời Gian Thực
- **Redis Cache**: Lưu trữ cache các kết quả cào và truy vấn để giảm độ trễ API và tiết kiệm chi phí SerpAPI.
- **Hệ thống Task không đồng bộ**: Cập nhật tiến trình cào dữ liệu thời gian thực (%) hiển thị trên giao diện người dùng.

### 7. Dashboard Hiện Đại & Trực Quan
- Giao diện chia màn hình **7/3** tối ưu: 7 phần là khung chat & dữ liệu trực quan, 3 phần là hướng dẫn sử dụng chi tiết.
- Hiển thị danh sách doanh nghiệp dưới dạng bảng tương tác và biểu đồ thống kê trực quan (Recharts).
- Tích hợp bản đồ Leaflet đánh dấu các vị trí doanh nghiệp trực quan.
- Hỗ trợ xuất dữ liệu ra file **CSV** hoặc **Excel** trực tiếp từ Dashboard.

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
   DB_URL=postgresql://postgres:yourpassword@localhost:5432/ai_leads_db
   SERPAPI_KEY=your_serpapi_api_key
   GROQ_API_KEY=your_groq_api_key
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
| **GET** | `/api/export?format=csv\|excel` | Trích xuất toàn bộ cơ sở dữ liệu doanh nghiệp và tải về dưới dạng file CSV/Excel. |
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
