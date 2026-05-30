from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from database.db import Base, engine
from api.routes import router


# Tạo bảng cơ sở dữ liệu khi khởi chạy ứng dụng (cách tiếp cận đơn giản — nên dùng Alembic cho môi trường production)
Base.metadata.create_all(bind=engine)


# Cấu hình ứng dụng FastAPI
app = FastAPI(
    title="AI Business Lead Generation API",
    description="Search businesses via Google Places, clean & store results.",
    version="1.0.0",
)


# Cấu hình CORS
# Trong môi trường production, hãy thay thế "*" bằng domain frontend thực tế của bạn.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Đăng ký các router chính của API
app.include_router(router, prefix="/api", tags=["Businesses"])


# Endpoint kiểm tra trạng thái hoạt động của hệ thống
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "API is running."}