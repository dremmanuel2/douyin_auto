# -*- coding: utf-8 -*-
"""
RabbitMQ 配置文件
"""

# RabbitMQ 连接配置
MQ_CONFIG = {
    "host": "8.136.195.32",
    "port": 5672,
    "user": "admin",
    "password": "FBREkFRESAGCffA",
    "virtual_host": "/",
    "queue_name": "douyin_message_queue",
    "dlx_queue_name": "douyin_message_dlx",
    "exchange_name": "douyin_message_exchange",
    "dlx_exchange_name": "douyin_message_dlx_exchange",
}

# 重试配置
RETRY_CONFIG = {
    "max_retries": 3,
    "retry_delay": 2,
    "dlx_ttl": 5000,
}

# 日志配置
LOG_CONFIG = {
    "log_dir": "logs",
    "log_level": "INFO",
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}