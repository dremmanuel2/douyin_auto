# -*- coding: utf-8 -*-
"""
数据库连接测试脚本
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from douyin_auto.db_utils import MySQLDBManager
from douyin_auto.db_config import MYSQL_DB_CONFIG


def test_database():
    """测试数据库连接和初始化"""
    print("=" * 60)
    print("数据库连接测试")
    print("=" * 60)

    print(f"\n数据库配置:")
    print(f"  主机：{MYSQL_DB_CONFIG['host']}:{MYSQL_DB_CONFIG['port']}")
    print(f"  数据库：{MYSQL_DB_CONFIG['db_name']}")
    print(f"  用户：{MYSQL_DB_CONFIG['user']}")
    print()

    db_manager = MySQLDBManager()

    print("正在初始化数据库...")
    if db_manager.initialize_database():
        print("[OK] 数据库初始化成功")
    else:
        print("[FAIL] 数据库初始化失败")
        return False

    print("\n正在测试添加消息...")
    message_id = db_manager.add_message("test_user_123", "这是一条测试消息")
    if message_id:
        print(f"[OK] 消息添加成功，ID: {message_id}")
    else:
        print("[FAIL] 消息添加失败")
        return False

    print("\n正在查询待执行消息...")
    pending_messages = db_manager.get_pending_messages()
    if pending_messages:
        print(f"[OK] 查询到 {len(pending_messages)} 条待执行消息:")
        for msg in pending_messages:
            print(
                f"  - ID: {msg['id']}, 抖音 ID: {msg['douyin_id']}, "
                f"消息：{msg['message'][:20]}..."
            )
    else:
        print("  没有待执行消息")

    print("\n正在删除测试消息...")
    if db_manager.delete_message(message_id):
        print(f"[OK] 消息 {message_id} 已删除")
    else:
        print(f"[FAIL] 消息 {message_id} 删除失败")

    print("\n正在查询今日发送数量...")
    today_count = db_manager.get_today_send_count()
    print(f"  今日已发送：{today_count} 条")

    print("\n正在查询队列数量...")
    queue_count = db_manager.get_queue_count()
    print(f"  队列待执行：{queue_count} 条")

    db_manager.disconnect()

    print("\n" + "=" * 60)
    print("数据库测试完成！")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = test_database()
        if success:
            print("\n[OK] 所有测试通过")
            sys.exit(0)
        else:
            print("\n[FAIL] 部分测试失败")
            sys.exit(1)
    except Exception as e:
        print(f"\n测试异常：{e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
