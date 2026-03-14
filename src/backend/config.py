"""
配置管理
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Config:
    """基础配置"""
    # Flask 配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{BASE_DIR / "src" / "data" / "database" / "tourism.db"}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 推荐系统配置
    MODEL_PATH = BASE_DIR / "src" / "data" / "models"
    DATASET_PATH = BASE_DIR / "dataset" / "yelp_tourism"
    
    # API 配置
    JSON_AS_ASCII = False  # 支持中文
    CORS_ORIGINS = ['http://localhost:8080', 'http://127.0.0.1:8080']
    
    # 分页配置
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    
    # 生产环境的 SECRET_KEY（仅在实际使用生产配置时检查）
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'CHANGE-THIS-IN-PRODUCTION'


class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """获取配置对象"""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    
    config_class = config.get(env, config['default'])
    
    # 仅在生产环境时检查 SECRET_KEY
    if env == 'production' and not os.environ.get('SECRET_KEY'):
        raise ValueError("生产环境必须设置 SECRET_KEY 环境变量")
    
    return config_class
