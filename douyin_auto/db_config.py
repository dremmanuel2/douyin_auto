# -*- coding: utf-8 -*-
"""
数据库配置文件
"""

# 数据库配置
MYSQL_DB_CONFIG = {
    "user": "root",
    "password": "chatbi123",
    "host": "8.136.195.32",
    "port": 3306,
    "db_name": "DY_database",
}

# 频率控制配置
RATE_LIMIT_CONFIG = {
    "send_interval": 30,  # 每条消息间隔（秒）
    "daily_limit": 100,  # 每日发送上限
}

# 重试配置
RETRY_CONFIG = {
    "max_retries": 3,  # 最大重试次数
    "retry_interval": 2,  # 重试间隔（秒）
}

# 监听配置
LISTEN_CONFIG = {
    "check_interval": 5,  # 监听循环间隔（秒）
}

# 日志配置
LOG_CONFIG = {
    "log_dir": "logs",
    "log_level": "INFO",
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}
