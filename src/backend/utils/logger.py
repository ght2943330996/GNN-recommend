"""
日志工具
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logger(app):
    """配置日志系统"""

    # 创建日志目录
    # log_dir = Path(app.root_path).parent.parent / 'logs'
    # log_dir.mkdir(exist_ok=True)

    # 设置日志级别
    if app.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # 日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )

    # 文件处理器（自动轮转） - 已禁用
    # file_handler = RotatingFileHandler(
    #     log_dir / 'app.log',
    #     maxBytes=10 * 1024 * 1024,  # 10MB
    #     backupCount=10
    # )
    # file_handler.setFormatter(formatter)
    # file_handler.setLevel(log_level)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # 配置 Flask 应用日志
    # app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)

    # 配置 Werkzeug 日志（Flask 开发服务器）
    werkzeug_logger = logging.getLogger('werkzeug')
    # werkzeug_logger.addHandler(file_handler)
    werkzeug_logger.setLevel(log_level)

    app.logger.info('日志系统初始化完成')
