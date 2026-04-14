"""
抖音自动化运行器 - 按点位名称执行自动化

使用方法：
    python scripts/run_automation.py
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from douyin_auto import Douyin
from douyin_auto.positions import POSITIONS


def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_config(config):
    """保存配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


def list_positions():
    """列出所有可用的点位"""
    print("\n" + "=" * 50)
    print("可用点位列表:")
    print("=" * 50)
    if not POSITIONS:
        print("  (暂无校准点位，请先运行 calibrate_position.py 校准)")
    else:
        for i, (name, (x, y)) in enumerate(sorted(POSITIONS.items()), 1):
            print(f"  {i}. {name}: ({x:.4f}, {y:.4f})")
    print()


def run_automation(dy, steps, interval=1.0, repeat=1):
    """
    执行自动化流程

    Args:
        dy: Douyin 实例
        steps: 点位名称列表，顺序执行
        interval: 每步间隔时间（秒）
        repeat: 重复次数
    """
    for r in range(repeat):
        if repeat > 1:
            print(f"\n--- 第 {r + 1}/{repeat} 轮 ---")

        for i, step_name in enumerate(steps, 1):
            if step_name not in POSITIONS:
                print(f"  [警告] 点位 '{step_name}' 不存在，跳过")
                continue

            x, y = POSITIONS[step_name]
            print(f"  [{i}/{len(steps)}] 点击: {step_name} ({x:.4f}, {y:.4f})")
            dy.Click(x, y)
            time.sleep(interval)


def run_sequence(dy, interval=1.0, repeat=1):
    """
    按点位名称排序顺序执行所有点位

    Args:
        dy: Douyin 实例
        interval: 每步间隔时间（秒）
        repeat: 重复次数
    """
    if not POSITIONS:
        print("没有可用的点位！")
        return

    # 按名称排序
    sorted_positions = sorted(POSITIONS.keys())
    print(f"\n将按以下顺序执行 {len(sorted_positions)} 个点位:")
    for name in sorted_positions:
        print(f"  - {name}")

    run_automation(dy, sorted_positions, interval, repeat)


def main():
    print("=" * 60)
    print("  抖音自动化运行器")
    print("=" * 60)

    config = load_config()
    interval = config.get('interval', 1.0)
    repeat = config.get('repeat', 1)

    print(f"\n当前配置:")
    print(f"  间隔时间: {interval} 秒")
    print(f"  重复次数: {repeat}")

    list_positions()

    # 连接抖音并固定窗口
    print("\n正在连接抖音窗口并固定大小...")
    try:
        dy = Douyin.open()
        print(f"连接成功！窗口大小: {dy.width}x{dy.height}")
    except Exception as e:
        print(f"连接失败: {e}")
        return

    print("\n" + "=" * 60)
    print("选择运行模式:")
    print("  1. 按顺序执行所有点位 (按名称排序)")
    print("  2. 自定义点位顺序执行")
    print("  3. 列出所有点位")
    print("  4. 修改配置 (间隔/重复)")
    print("  0. 退出")
    print("=" * 60)

    while True:
        choice = input("\n请选择 (0-4): ").strip()

        if choice == '1':
            print(f"\n将按名称顺序执行所有点位，间隔 {interval} 秒")
            confirm = input("确认执行? (y/n): ").strip().lower()
            if confirm == 'y':
                run_sequence(dy, interval=interval, repeat=repeat)

        elif choice == '2':
            list_positions()
            names_input = input("\n输入点位名称（逗号分隔，如: 点击搜索框,点击搜索）: ").strip()
            if names_input:
                steps = [s.strip() for s in names_input.split(',')]
                run_automation(dy, steps, interval=interval, repeat=repeat)

        elif choice == '3':
            list_positions()

        elif choice == '4':
            new_interval = input(f"间隔时间 (当前 {interval}s): ").strip()
            new_repeat = input(f"重复次数 (当前 {repeat}): ").strip()
            if new_interval:
                config['interval'] = float(new_interval)
            if new_repeat:
                config['repeat'] = int(new_repeat)
            save_config(config)
            interval = config.get('interval', 1.0)
            repeat = config.get('repeat', 1)
            print(f"已保存: 间隔 {interval}s, 重复 {repeat} 次")

        elif choice == '0':
            print("退出")
            break


if __name__ == '__main__':
    main()
