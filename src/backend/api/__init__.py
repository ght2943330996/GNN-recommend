"""
API 模块初始化
"""
from .user import user_bp
from .recommend import recommend_bp
from .rating import rating_bp
from .item import item_bp

__all__ = ['user_bp', 'recommend_bp', 'rating_bp', 'item_bp']
