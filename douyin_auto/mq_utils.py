# -*- coding: utf-8 -*-
"""
RabbitMQ 管理器
提供 RabbitMQ 连接、队列管理、消息发布和消费功能
"""

import pika
import json
import logging
from typing import Optional, Callable, Dict, Any
from .mq_config import MQ_CONFIG, RETRY_CONFIG

logger = logging.getLogger(__name__)


class RabbitMQManager:
    """RabbitMQ 管理器"""

    def __init__(self, mq_config=None):
        """
        初始化 RabbitMQ 管理器

        Args:
            mq_config: RabbitMQ 配置字典，如果为 None 则使用默认配置
        """
        self.config = mq_config or MQ_CONFIG
        self.connection = None
        self.channel = None
        self.dlx_channel = None
        self._connected = False

    def connect(self) -> bool:
        """
        建立 RabbitMQ 连接

        Returns:
            bool: 连接是否成功
        """
        try:
            credentials = pika.PlainCredentials(
                self.config["user"],
                self.config["password"]
            )

            parameters = pika.ConnectionParameters(
                host=self.config["host"],
                port=self.config["port"],
                virtual_host=self.config["virtual_host"],
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.dlx_channel = self.connection.channel()

            self._connected = True
            logger.info(
                "RabbitMQ 连接成功：{}:{}".format(
                    self.config['host'], self.config['port']
                )
            )
            return True

        except Exception as e:
            logger.error("RabbitMQ 连接失败：{}".format(e))
            self._connected = False
            return False

    def disconnect(self):
        """断开 RabbitMQ 连接"""
        try:
            if self.connection and self.connection.is_open:
                self.connection.close()
                self.connection = None
                self.channel = None
                self.dlx_channel = None
                self._connected = False
                logger.info("RabbitMQ 连接已关闭")
        except Exception as e:
            logger.error("断开连接异常：{}".format(e))

    def check_connection(self) -> bool:
        """
        检查连接状态

        Returns:
            bool: 连接是否有效
        """
        if not self._connected:
            return False
        try:
            return self.connection and self.connection.is_open
        except Exception:
            return False

    def reconnect(self) -> bool:
        """重新连接"""
        self.disconnect()
        return self.connect()

    def initialize_queues(self) -> bool:
        """
        初始化队列（主队列 + 死信队列）

        Returns:
            bool: 初始化是否成功
        """
        try:
            if not self.check_connection():
                if not self.reconnect():
                    return False

            # 声明死信交换机
            self.dlx_channel.exchange_declare(
                exchange=self.config["dlx_exchange_name"],
                exchange_type='direct',
                durable=True,
            )

            # 声明死信队列
            dlx_args = {
                'x-message-ttl': RETRY_CONFIG["dlx_ttl"],
            }
            self.dlx_channel.queue_declare(
                queue=self.config["dlx_queue_name"],
                durable=True,
                arguments=dlx_args,
            )

            # 绑定死信队列到死信交换机
            self.dlx_channel.queue_bind(
                queue=self.config["dlx_queue_name"],
                exchange=self.config["dlx_exchange_name"],
                routing_key=self.config["dlx_queue_name"],
            )

            # 声明主队列（设置死信交换机）
            queue_args = {
                'x-dead-letter-exchange': self.config["dlx_exchange_name"],
                'x-dead-letter-routing-key': self.config["dlx_queue_name"],
            }
            self.channel.queue_declare(
                queue=self.config["queue_name"],
                durable=True,
                arguments=queue_args,
            )

            # 声明主交换机
            self.channel.exchange_declare(
                exchange=self.config["exchange_name"],
                exchange_type='direct',
                durable=True,
            )

            # 绑定主队列到主交换机
            self.channel.queue_bind(
                queue=self.config["queue_name"],
                exchange=self.config["exchange_name"],
                routing_key=self.config["queue_name"],
            )

            logger.info("RabbitMQ 队列初始化完成")
            return True

        except Exception as e:
            logger.error("队列初始化失败：{}".format(e))
            return False

    def publish_message(
        self,
        douyin_id: str,
        message: str,
        retry_count: int = 0
    ) -> bool:
        """
        发布消息到队列

        Args:
            douyin_id: 目标用户抖音 ID
            message: 消息内容
            retry_count: 重试次数

        Returns:
            bool: 发布是否成功
        """
        try:
            if not self.check_connection():
                if not self.reconnect():
                    return False

            message_body = {
                "douyin_id": douyin_id,
                "message": message,
                "retry_count": retry_count,
                "created_at": None,
            }

            properties = pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json',
            )

            self.channel.basic_publish(
                exchange=self.config["exchange_name"],
                routing_key=self.config["queue_name"],
                body=json.dumps(message_body, ensure_ascii=False).encode('utf-8'),
                properties=properties,
            )

            logger.info("消息发布成功：{}".format(douyin_id))
            return True

        except Exception as e:
            logger.error("消息发布失败：{}".format(e))
            return False

    def consume_message(
        self,
        callback: Callable[[Dict[str, Any], Callable], None],
        auto_ack: bool = False,
    ):
        """
        消费消息（阻塞式）

        Args:
            callback: 消息处理回调函数，接收 (message_dict, ack_callback)
            auto_ack: 是否自动确认
        """
        try:
            if not self.check_connection():
                if not self.reconnect():
                    return

            def on_message(
                ch,
                method: pika.BasicMethods.Deliver,
                properties: pika.BasicProperties,
                body: bytes
            ):
                try:
                    message = json.loads(body.decode('utf-8'))

                    def ack():
                        """确认消息"""
                        ch.basic_ack(delivery_tag=method.delivery_tag)

                    if auto_ack:
                        ack()

                    callback(message, ack)

                except Exception as e:
                    logger.error("消息处理异常：{}".format(e))
                    if not auto_ack:
                        ch.basic_nack(
                            delivery_tag=method.delivery_tag,
                            requeue=False
                        )

            self.channel.basic_consume(
                queue=self.config["queue_name"],
                on_message_callback=on_message,
                auto_ack=auto_ack,
            )

            logger.info("开始消费消息...")
            self.channel.start_consuming()

        except Exception as e:
            logger.error("消费消息异常：{}".format(e))

    def consume_one(self, auto_ack: bool = False) -> Optional[Dict[str, Any]]:
        """
        消费单条消息（非阻塞）

        Args:
            auto_ack: 是否自动确认

        Returns:
            dict: 消息字典，如果没有消息返回 None
        """
        try:
            if not self.check_connection():
                if not self.reconnect():
                    return None

            method, properties, body = self.channel.basic_get(
                queue=self.config["queue_name"],
                auto_ack=auto_ack,
            )

            if method:
                message = json.loads(body.decode('utf-8'))
                return message
            return None

        except Exception as e:
            logger.error("消费消息失败：{}".format(e))
            return None

    def ack_message(self, delivery_tag: int):
        """
        确认消息

        Args:
            delivery_tag: 消息交付标签
        """
        try:
            if self.channel:
                self.channel.basic_ack(delivery_tag=delivery_tag)
        except Exception as e:
            logger.error("确认消息失败：{}".format(e))

    def nack_message(self, delivery_tag: int, requeue: bool = False):
        """
        拒绝消息

        Args:
            delivery_tag: 消息交付标签
            requeue: 是否重新入队
        """
        try:
            if self.channel:
                self.channel.basic_nack(
                    delivery_tag=delivery_tag,
                    requeue=requeue,
                )
        except Exception as e:
            logger.error("拒绝消息失败：{}".format(e))

    def retry_message(self, message: Dict[str, Any], delivery_tag: int):
        """
        重试消息（发送到死信队列）

        Args:
            message: 消息字典
            delivery_tag: 当前消息的交付标签
        """
        try:
            retry_count = message.get("retry_count", 0) + 1
            message["retry_count"] = retry_count

            if self.dlx_channel:
                self.dlx_channel.basic_publish(
                    exchange=self.config["dlx_exchange_name"],
                    routing_key=self.config["dlx_queue_name"],
                    body=json.dumps(message, ensure_ascii=False).encode('utf-8'),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json',
                    ),
                )
                logger.info("消息已发送到死信队列（重试 {} 次）".format(retry_count))

            self.ack_message(delivery_tag)

        except Exception as e:
            logger.error("重试消息失败：{}".format(e))

    def get_queue_count(self) -> int:
        """
        获取队列中消息数量

        Returns:
            int: 消息数量
        """
        try:
            if not self.check_connection():
                if not self.reconnect():
                    return 0

            queue_info = self.channel.queue_declare(
                queue=self.config["queue_name"],
                passive=True,
            )
            return queue_info.method.message_count

        except Exception as e:
            logger.error("获取队列数量失败：{}".format(e))
            return 0

    def get_dlx_queue_count(self) -> int:
        """
        获取死信队列中消息数量

        Returns:
            int: 消息数量
        """
        try:
            if not self.check_connection():
                if not self.reconnect():
                    return 0

            queue_info = self.dlx_channel.queue_declare(
                queue=self.config["dlx_queue_name"],
                passive=True,
            )
            return queue_info.method.message_count

        except Exception as e:
            logger.error("获取死信队列数量失败：{}".format(e))
            return 0

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        self.initialize_queues()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


class DLXHandler:
    """死信队列处理器"""

    def __init__(self, mq_manager: RabbitMQManager):
        """
        初始化死信队列处理器

        Args:
            mq_manager: RabbitMQ 管理器实例
        """
        self.mq_manager = mq_manager
        self.logger = logging.getLogger(__name__)

    def process_dlx_messages(
        self,
        retry_callback: Callable[[Dict[str, Any]], bool],
        failure_callback: Callable[[Dict[str, Any]], None],
    ):
        """
        处理死信队列中的消息

        Args:
            retry_callback: 重试回调函数，返回是否成功
            failure_callback: 失败回调函数（达到最大重试次数时调用）
        """
        def on_dlx_message(
            ch,
            method: pika.BasicMethods.Deliver,
            properties: pika.BasicProperties,
            body: bytes
        ):
            try:
                message = json.loads(body.decode('utf-8'))
                retry_count = message.get("retry_count", 0)
                max_retries = RETRY_CONFIG["max_retries"]

                self.logger.info(
                    "处理死信队列消息（重试 {}/{}）: {}".format(
                        retry_count, max_retries, message.get('douyin_id')
                    )
                )

                if retry_count >= max_retries:
                    self.logger.warning(
                        "消息已达最大重试次数，记录失败：{}".format(
                            message.get('douyin_id')
                        )
                    )
                    failure_callback(message)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                else:
                    success = retry_callback(message)
                    if success:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    else:
                        ch.basic_nack(
                            delivery_tag=method.delivery_tag,
                            requeue=False,
                        )

            except Exception as e:
                self.logger.error("处理死信消息异常：{}".format(e))
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        try:
            if not self.mq_manager.check_connection():
                if not self.mq_manager.reconnect():
                    return

            self.mq_manager.dlx_channel.basic_consume(
                queue=self.mq_manager.config["dlx_queue_name"],
                on_message_callback=on_dlx_message,
                auto_ack=False,
            )

            self.logger.info("开始处理死信队列...")
            self.mq_manager.connection.add_timeout(
                1,
                lambda: self.mq_manager.connection.sleep(0.1)
            )

        except Exception as e:
            self.logger.error("处理死信队列异常：{}".format(e))

    def consume_dlx_one(self) -> Optional[Dict[str, Any]]:
        """
        从死信队列消费单条消息

        Returns:
            dict: 消息字典，如果没有消息返回 None
        """
        try:
            if not self.mq_manager.check_connection():
                if not self.mq_manager.reconnect():
                    return None

            method, properties, body = self.mq_manager.dlx_channel.basic_get(
                queue=self.mq_manager.config["dlx_queue_name"],
                auto_ack=False,
            )

            if method:
                message = json.loads(body.decode('utf-8'))
                message['_delivery_tag'] = method.delivery_tag
                return message
            return None

        except Exception as e:
            self.logger.error("从死信队列消费失败：{}".format(e))
            return None