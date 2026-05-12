import redis
import json
from typing import Optional, Union, Any

# Khởi tạo kết nối tới Redis server
# Thiết lập decode_responses=True giúp tự động chuyển đổi định dạng bytes sang string khi đọc dữ liệu
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

def get_cache(key: str) -> Optional[dict]:
    """
    Lấy dữ liệu từ Redis cache dựa vào key.
    
    Args:
        key (str): Khóa (key) của dữ liệu cần lấy trong Redis.
        
    Returns:
        Optional[dict]: Trả về dictionary chứa dữ liệu nếu tìm thấy và parse JSON thành công, 
                        ngược lại trả về None.
    """
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"Lỗi khi lấy cache từ Redis với key '{key}': {e}")
        return None

def set_cache(key: str, data: Union[dict, list, Any], expire_time: int = 86400):
    """
    Lưu dữ liệu vào Redis cache với thời gian sống (TTL).
    
    Args:
        key (str): Khóa (key) dùng để lưu dữ liệu.
        data (Union[dict, list, Any]): Dữ liệu cần lưu. Có thể là dictionary, danh sách, 
                                       hoặc danh sách chứa các Pydantic models.
        expire_time (int): Thời gian sống của cache tính bằng giây. Mặc định là 86400 (24 giờ).
    """
    try:
        # Hàm hỗ trợ custom_encoder để chuyển đổi các object phức tạp thành định dạng JSON có thể đọc được
        def custom_encoder(obj):
            # Xử lý cho Pydantic V2
            if hasattr(obj, 'model_dump'):
                return obj.model_dump()
            # Xử lý cho Pydantic V1
            elif hasattr(obj, 'dict'):
                return obj.dict()
            # Dự phòng ép kiểu sang string cho các loại object không xác định khác (như datetime, UUID, v.v...)
            return str(obj)

        # Chuyển đổi an toàn dữ liệu đầu vào sang chuỗi JSON
        json_data = json.dumps(data, default=custom_encoder, ensure_ascii=False)
        
        # Lưu vào Redis sử dụng setex để thiết lập cả giá trị lẫn thời gian sống cùng lúc
        redis_client.setex(key, expire_time, json_data)
    except Exception as e:
        print(f"Lỗi khi lưu cache vào Redis với key '{key}': {e}")

def set_task_status(task_id: str, status: str, progress: int, message: str, data: dict = None):
    """
    Cập nhật trạng thái của task vào Redis.
    TTL mặc định là 3600 giây (1 giờ).
    """
    task_data = {
        "status": status,
        "progress": progress,
        "message": message,
        "data": data
    }
    set_cache(f"task:{task_id}", task_data, expire_time=3600)

def get_task_status(task_id: str) -> Optional[dict]:
    """
    Lấy trạng thái của task từ Redis.
    """
    return get_cache(f"task:{task_id}")
