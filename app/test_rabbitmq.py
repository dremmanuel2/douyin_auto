# -*- coding: utf-8 -*-
"""
RabbitMQ 测试脚本
测试 RabbitMQ 连接、队列、消息发布和消费功能
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from douyin_auto.mq_utils import RabbitMQManager, DLXHandler
from douyin_auto.mq_config import MQ_CONFIG, RETRY_CONFIG
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("TestRabbitMQ")


def test_connection():
    """测试连接"""
    print("\n" + "=" * 60)
    print("测试 1: RabbitMQ 连接")
    print("=" * 60)
    
    mq_manager = RabbitMQManager()
    
    try:
        if mq_manager.connect():
            print("OK RabbitMQ 连接成功")
            print("  主机：{}:{}".format(MQ_CONFIG['host'], MQ_CONFIG['port']))
            print("  虚拟主机：{}".format(MQ_CONFIG['virtual_host']))
            mq_manager.disconnect()
            return True
        else:
            print("FAIL RabbitMQ 连接失败")
            return False
    except Exception as e:
        print("FAIL 连接异常：{}".format(e))
        return False


def test_queue_initialization():
    """测试队列初始化"""
    print("\n" + "=" * 60)
    print("测试 2: 队列初始化")
    print("=" * 60)
    
    mq_manager = RabbitMQManager()
    
    try:
        if mq_manager.connect():
            if mq_manager.initialize_queues():
                print("OK 队列初始化成功")
                print("  主队列：{}".format(MQ_CONFIG['queue_name']))
                print("  死信队列：{}".format(MQ_CONFIG['dlx_queue_name']))
                mq_manager.disconnect()
                return True
            else:
                print("FAIL 队列初始化失败")
                return False
        else:
            print("FAIL 连接失败")
            return False
    except Exception as e:
        print("FAIL 初始化异常：{}".format(e))
        return False


def test_publish_message():
    """测试消息发布"""
    print("\n" + "=" * 60)
    print("测试 3: 消息发布")
    print("=" * 60)
    
    mq_manager = RabbitMQManager()
    
    try:
        if mq_manager.connect() and mq_manager.initialize_queues():
            test_messages = [
                ("test_user_001", "你好，这是一条测试消息"),
                ("test_user_002", "测试消息 2"),
                ("test_user_003", "测试消息 3"),
            ]
            
            success_count = 0
            for douyin_id, message in test_messages:
                if mq_manager.publish_message(douyin_id, message):
                    success_count += 1
                    print("OK 消息发布成功：{}".format(douyin_id))
                else:
                    print("FAIL 消息发布失败：{}".format(douyin_id))
            
            mq_manager.disconnect()
            
            if success_count == len(test_messages):
                print("\nOK 所有消息发布成功 ({}/{})".format(success_count, len(test_messages)))
                return True
            else:
                print("\nFAIL 部分消息发布失败 ({}/{})".format(success_count, len(test_messages)))
                return False
        else:
            print("FAIL 连接或初始化失败")
            return False
    except Exception as e:
        print("FAIL 发布异常：{}".format(e))
        return False


def test_consume_message():
    """测试消息消费"""
    print("\n" + "=" * 60)
    print("测试 4: 消息消费")
    print("=" * 60)
    
    mq_manager = RabbitMQManager()
    
    try:
        if mq_manager.connect() and mq_manager.initialize_queues():
            consume_count = 0
            max_consume = 5
            
            print("开始消费消息（最多 {} 条）...".format(max_consume))
            
            while consume_count < max_consume:
                msg = mq_manager.consume_one(auto_ack=True)
                
                if msg:
                    consume_count += 1
                    print("OK 消费到消息 {}: {} - {}".format(
                        consume_count, msg['douyin_id'], msg['message'][:30]))
                else:
                    print("OK 队列已空，共消费 {} 条消息".format(consume_count))
                    break
            
            mq_manager.disconnect()
            
            if consume_count > 0:
                print("\nOK 消息消费测试成功")
                return True
            else:
                print("\nWARN 队列为空，没有消息可消费")
                return True
        else:
            print("FAIL 连接或初始化失败")
            return False
    except Exception as e:
        print("FAIL 消费异常：{}".format(e))
        return False


def test_dlx():
    """测试死信队列"""
    print("\n" + "=" * 60)
    print("测试 5: 死信队列")
    print("=" * 60)
    
    mq_manager = RabbitMQManager()
    
    try:
        if mq_manager.connect() and mq_manager.initialize_queues():
            print("发布测试消息到死信队列...")
            
            if mq_manager.publish_message("dlx_test_user", "死信队列测试消息"):
                print("OK 消息发布成功")
                
                msg = mq_manager.consume_one(auto_ack=False)
                
                if msg:
                    print("OK 消费到消息：{}".format(msg['douyin_id']))
                    
                    print("模拟消息处理失败，发送到死信队列...")
                    mq_manager.retry_message(msg, 0)
                    print("OK 消息已发送到死信队列")
                    
                    time.sleep(1)
                    
                    dlx_count = mq_manager.get_dlx_queue_count()
                    print("死信队列消息数量：{}".format(dlx_count))
                    
                    if dlx_count > 0:
                        print("OK 死信队列测试成功")
                        mq_manager.disconnect()
                        return True
                    else:
                        print("FAIL 死信队列中没有消息")
                        mq_manager.disconnect()
                        return False
                else:
                    print("FAIL 没有消费到消息")
                    mq_manager.disconnect()
                    return False
            else:
                print("FAIL 消息发布失败")
                mq_manager.disconnect()
                return False
        else:
            print("FAIL 连接或初始化失败")
            return False
    except Exception as e:
        print("FAIL 死信队列测试异常：{}".format(e))
        return False


def test_queue_count():
    """测试队列数量查询"""
    print("\n" + "=" * 60)
    print("测试 6: 队列数量查询")
    print("=" * 60)
    
    mq_manager = RabbitMQManager()
    
    try:
        if mq_manager.connect() and mq_manager.initialize_queues():
            queue_count = mq_manager.get_queue_count()
            dlx_count = mq_manager.get_dlx_queue_count()
            
            print("OK 主队列消息数量：{}".format(queue_count))
            print("OK 死信队列消息数量：{}".format(dlx_count))
            
            mq_manager.disconnect()
            return True
        else:
            print("FAIL 连接或初始化失败")
            return False
    except Exception as e:
        print("FAIL 查询异常：{}".format(e))
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  RabbitMQ 测试脚本")
    print("=" * 60)
    print("\n配置信息:")
    print("  主机：{}:{}".format(MQ_CONFIG['host'], MQ_CONFIG['port']))
    print("  用户：{}".format(MQ_CONFIG['user']))
    print("  虚拟主机：{}".format(MQ_CONFIG['virtual_host']))
    print("  主队列：{}".format(MQ_CONFIG['queue_name']))
    print("  死信队列：{}".format(MQ_CONFIG['dlx_queue_name']))
    
    results = {
        "连接测试": test_connection(),
        "队列初始化": test_queue_initialization(),
        "消息发布": test_publish_message(),
        "消息消费": test_consume_message(),
        "死信队列": test_dlx(),
        "队列数量": test_queue_count(),
    }
    
    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "OK 通过" if result else "FAIL 失败"
        print("  {}: {}".format(test_name, status))
    
    passed = sum(results.values())
    total = len(results)
    
    print("\n总计：{}/{} 测试通过".format(passed, total))
    
    if passed == total:
        print("\nOK 所有测试通过！RabbitMQ 配置正确")
        return 0
    else:
        print("\nFAIL {} 个测试失败，请检查配置".format(total - passed))
        return 1


if __name__ == "__main__":
    sys.exit(main())