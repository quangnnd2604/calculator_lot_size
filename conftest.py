# conftest.py — shared pytest configuration
# Đặt tại root project để pytest tìm thấy src/ package không cần cài đặt.

import sys
import os

# Thêm project root vào sys.path để `from src.xxx import ...` hoạt động
sys.path.insert(0, os.path.dirname(__file__))
