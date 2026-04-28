# -*- coding: utf-8 -*-
"""
数据库工具类
提供 MySQL 数据库连接和操作功能
"""

import pymysql
from pymysql.cursors import DictCursor
from .db_config import MYSQL_DB_CONFIG
import logging
import os

logger = logging.getLogger(__name__)


class MySQLDBManager:
    """MySQL 数据库管理器"""

    def __init__(self, db_config=None):
        """
        初始化数据库管理器

        Args:
            db_config: 数据库配置字典，如果为 None 则使用默认配置
        """
        self.config = db_config or MYSQL_DB_CONFIG
        self.connection = None
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 3306)
        self.user = self.config.get("user", "root")
        self.password = self.config.get("password", "")
        self.db_name = self.config.get("db_name", "DY_database")

    def connect(self):
        """
        建立数据库连接

        Returns:
            bool: 连接是否成功
        """
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.db_name,
                charset="utf8mb4",
                cursorclass=DictCursor,
                autocommit=True,
            )
            logger.info(f"数据库连接成功：{self.host}:{self.port}/{self.db_name}")
            return True
        except pymysql.Error as e:
            logger.error(f"数据库连接失败：{e}")
            return False

    def disconnect(self):
        """断开数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("数据库连接已关闭")

    def check_connection(self):
        """
        检查数据库连接状态

        Returns:
            bool: 连接是否有效
        """
        if self.connection is None:
            return False
        try:
            self.connection.ping(reconnect=False)
            return True
        except pymysql.Error:
            return False

    def reconnect(self):
        """重新连接数据库"""
        self.disconnect()
        return self.connect()

    def execute_query(self, sql, params=None):
        """
        执行查询语句

        Args:
            sql: SQL 查询语句
            params: 参数元组或字典

        Returns:
            list: 查询结果列表
        """
        if not self.check_connection():
            if not self.reconnect():
                return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchall()
                return result
        except pymysql.Error as e:
            logger.error(f"查询执行失败：{sql}, 错误：{e}")
            return []

    def execute_update(self, sql, params=None):
        """
        执行更新语句（INSERT, UPDATE, DELETE）

        Args:
            sql: SQL 更新语句
            params: 参数元组或字典

        Returns:
            int: 受影响的行数
        """
        if not self.check_connection():
            if not self.reconnect():
                return 0

        try:
            with self.connection.cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
                self.connection.commit()
                return affected_rows
        except pymysql.Error as e:
            logger.error(f"更新执行失败：{sql}, 错误：{e}")
            self.connection.rollback()
            return 0

    def initialize_database(self):
        """
        初始化数据库和表
        如果数据库不存在则创建，如果表不存在则创建

        Returns:
            bool: 初始化是否成功
        """
        try:
            temp_conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                charset="utf8mb4",
                cursorclass=DictCursor,
            )

            try:
                with temp_conn.cursor() as cursor:
                    cursor.execute(
                        f"CREATE DATABASE IF NOT EXISTS `{self.db_name}` "
                        "DEFAULT CHARACTER SET utf8mb4 "
                        "COLLATE utf8mb4_unicode_ci"
                    )
                    logger.info(f"数据库检查完成：{self.db_name}")
            finally:
                temp_conn.close()

            if not self.connect():
                return False

            create_log_table_sql = """
            CREATE TABLE IF NOT EXISTS message_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                douyin_id VARCHAR(50) NOT NULL COMMENT '目标用户抖音 ID',
                message TEXT NOT NULL COMMENT '发送的消息内容',
                send_status TINYINT DEFAULT 0 COMMENT '发送状态：0-失败，1-成功',
                retry_count TINYINT DEFAULT 0 COMMENT '重试次数',
                error_message VARCHAR(500) COMMENT '错误信息',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
                INDEX idx_douyin_id (douyin_id),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息发送日志'
            """
            self.execute_update(create_log_table_sql)
            logger.info("数据表 message_logs 检查完成")

            return True

        except pymysql.Error as e:
            logger.error(f"数据库初始化失败：{e}")
            return False

    def log_message(
        self, douyin_id, message, send_status, retry_count=0, error_message=None
    ):
        """
        记录消息发送日志

        Args:
            douyin_id: 目标用户抖音 ID
            message: 消息内容
            send_status: 发送状态（0-失败，1-成功）
            retry_count: 重试次数
            error_message: 错误信息

        Returns:
            bool: 记录是否成功
        """
        sql = """
        INSERT INTO message_logs (douyin_id, message, send_status, retry_count, error_message)
        VALUES (%s, %s, %s, %s, %s)
        """
        affected_rows = self.execute_update(
            sql, (douyin_id, message, send_status, retry_count, error_message)
        )
        return affected_rows > 0

    def get_today_send_count(self):
        """
        获取今日已发送的消息数量

        Returns:
            int: 今日发送数量
        """
        sql = """
        SELECT COUNT(*) as count 
        FROM message_logs 
        WHERE DATE(created_at) = CURDATE() AND send_status = 1
        """
        result = self.execute_query(sql)
        if result and len(result) > 0:
            return result[0]["count"]
        return 0

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()
