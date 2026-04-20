# -*- coding: utf-8 -*-
"""
测试配置文件
"""

from douyin_auto.send_config import SEARCH_CONFIG, RATE_LIMIT_CONFIG

print("=" * 60)
print("发送私信配置测试")
print("=" * 60)
print()

print("搜索流程时间配置：")
for key, value in SEARCH_CONFIG.items():
    print(f"  {key}: {value}秒")

print()
print("频率控制配置：")
print(f"  发送间隔：{RATE_LIMIT_CONFIG['send_interval']}秒/条")
print(f"  每日上限：{RATE_LIMIT_CONFIG['daily_limit']}条/天")

print()
print("=" * 60)
print("配置加载成功！")
print("=" * 60)
