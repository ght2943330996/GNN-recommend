"""
模型模块初始化
"""
from .database import db, User, Rating, Comment, Favorite, init_db

__all__ = ['db', 'User', 'Rating', 'Comment', 'Favorite', 'init_db']
