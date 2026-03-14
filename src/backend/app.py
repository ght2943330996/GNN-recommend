"""
Flask 应用入口
"""
import os
import sys
from pathlib import Path
from flask import Flask
from flask_cors import CORS

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.backend.config import get_config
from src.backend.models.database import db, init_db
from src.backend.utils.logger import setup_logger
from src.backend.services.recommender import recommender_service


def create_app(config_name=None):
    """应用工厂函数"""
    
    app = Flask(__name__)
    
    # 加载配置
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    config = get_config(config_name)
    app.config.from_object(config)
    
    # 确保数据库目录存在
    db_path = Path(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 初始化扩展
    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # 设置日志
    setup_logger(app)
    
    # 注册蓝图
    from src.backend.api.user import user_bp
    from src.backend.api.recommend import recommend_bp
    from src.backend.api.rating import rating_bp
    from src.backend.api.item import item_bp
    
    app.register_blueprint(user_bp)
    app.register_blueprint(recommend_bp)
    app.register_blueprint(rating_bp)
    app.register_blueprint(item_bp)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
        app.logger.info("✓ 数据库初始化完成")
    
    # 预加载推荐模型
    app.logger.info("正在加载推荐模型...")
    _ = recommender_service.recommender
    app.logger.info(f"✓ 推荐模型加载完成 (用户: {recommender_service.num_users}, 景点: {recommender_service.num_items})")
    
    return app


if __name__ == '__main__':
    app = create_app()
    
    print("\n" + "="*60)
    print("  🚀 旅游景点推荐系统 - 后端服务")
    print("="*60)
    print(f"  环境: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"  地址: http://localhost:5000")
    print(f"  健康检查: http://localhost:5000/api/health")
    print("="*60 + "\n")
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        use_reloader=False  # 避免重复加载模型
    )
