import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

# Thêm đường dẫn thư mục backend vào sys.path để import các module nội bộ
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_path)

from database.db import engine, SessionLocal
from database.models import Business
from sqlalchemy import text
from sentence_transformers import SentenceTransformer

def run_migration():
    print("🚀 Starting Database Migration...")
    
    # 1. Kiểm tra xem tiện ích mở rộng pgvector (vector) có sẵn trong PostgreSQL không
    has_pgvector = False
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT * FROM pg_available_extensions WHERE name = 'vector';")).fetchone()
            if res:
                print("✅ pgvector extension is AVAILABLE in PostgreSQL.")
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                print("✅ pgvector extension enabled.")
                has_pgvector = True
            else:
                print("⚠️ pgvector extension is NOT available in PostgreSQL. We will use TEXT column for embeddings (Python fallback mode).")
    except Exception as e:
        print(f"⚠️ Error checking/enabling pgvector extension: {e}")
        print("We will fall back to TEXT column for embeddings.")

    # 2. Thêm các cột cần thiết vào bảng businesses nếu chưa tồn tại
    try:
        with engine.connect() as conn:
            # Thêm cột review_summary để lưu trữ tóm tắt đánh giá
            try:
                conn.execute(text("ALTER TABLE businesses ADD COLUMN review_summary TEXT;"))
                conn.commit()
                print("✅ Added column 'review_summary' (TEXT).")
            except Exception as e:
                # Cột có thể đã tồn tại từ trước
                conn.rollback()
                print("ℹ️ Column 'review_summary' already exists or could not be added.")

            # Thêm cột embedding để phục vụ tìm kiếm vector ngữ nghĩa
            if has_pgvector:
                try:
                    conn.execute(text("ALTER TABLE businesses ADD COLUMN embedding vector(768);"))
                    conn.commit()
                    print("✅ Added column 'embedding' (vector(768)).")
                except Exception as e:
                    conn.rollback()
                    # Kiểm tra xem cột đã tồn tại với kiểu dữ liệu khác chưa
                    print("ℹ️ Column 'embedding' already exists or could not be added as vector(768).")
            else:
                try:
                    conn.execute(text("ALTER TABLE businesses ADD COLUMN embedding TEXT;"))
                    conn.commit()
                    print("✅ Added column 'embedding' (TEXT) for python-native fallback.")
                except Exception as e:
                    conn.rollback()
                    print("ℹ️ Column 'embedding' already exists or could not be added as TEXT.")
    except Exception as e:
        print(f"❌ Migration columns addition failed: {e}")
        sys.exit(1)

    # 3. Tạo vector embedding bổ sung cho những bản ghi cũ đã có tóm tắt đánh giá thực tế
    db = SessionLocal()
    try:
        businesses = db.query(Business).filter(Business.review_summary.isnot(None), Business.embedding.is_(None)).all()
        if not businesses:
            print("ℹ️ All businesses with review summaries already have embeddings.")
            return

        print(f"ℹ️ Found {len(businesses)} businesses needing embeddings. Generating...")
        
        # Tải mô hình sinh embedding cục bộ
        model_name = "keepitreal/vietnamese-sbert"
        print(f"⚡ Loading embedding model '{model_name}'... (This may take a moment on first run)")
        model = SentenceTransformer(model_name)
        print("✅ Embedding model loaded.")

        updated_count = 0
        for biz in businesses:
            print(f"  -> Generating embedding for: {biz.name}")
            embedding_vector = model.encode(biz.review_summary).tolist()
            biz.embedding = embedding_vector
            updated_count += 1

        if updated_count > 0:
            db.commit()
            print(f"✅ Successfully generated embeddings for {updated_count} businesses!")

    except Exception as e:
        db.rollback()
        print(f"❌ Failed to populate data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
