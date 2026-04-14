"""
抖音私信发送工具

使用方法：
    python scripts/send_message.py

每一步的点击间隔可自定义修改底部的 INTERVAL 配置
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from douyin_auto import Douyin
from douyin_auto.positions import POSITIONS
from douyin_auto.utils import SetClipboardText, SendKey, Keys


# ============ 可调整的参数 ============
USER_ID = "56283084690"          # 搜索的用户ID，留空则运行时输入
MESSAGE = "yibb"          # 发送的消息内容，留空则运行时输入
INTERVAL = 3.0        # 每步之间等待的秒数（可根据需要调整）
NEED_FOLLOW = False    # 是否先关注再发消息
# ====================================


def input_text_via_clipboard(text, hwnd):
    """通过剪贴板输入文本"""
    SetClipboardText(text)
    time.sleep(0.1)
    import win32gui
    import win32api
    import win32con
    win32gui.SetForegroundWindow(hwnd)
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.keybd_event(0x56, 0, 0, 0)
    time.sleep(0.05)
    win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(0.2)


def send_message(user_id, message, need_follow=True, interval=1.0):
    """
    发送私信完整流程

    Args:
        user_id: 目标用户ID
        message: 消息内容
        need_follow: 是否先关注
        interval: 每步间隔（秒）
    """
    dy = Douyin.open()
    print(f"窗口大小: {dy.width}x{dy.height}")
    print()

    # 检查必要点位
    required = ['点击搜索框', '点击用户头像']
    if need_follow:
        required.append('点击头像内部的关注')
    required.extend(['点击头像里面的私信', '点击发送消息框'])

    missing = [r for r in required if r not in POSITIONS]
    if missing:
        print(f"[错误] 缺少必要点位: {missing}")
        print(f"请先运行 calibrate_position.py 校准以上点位")
        return

    print(f"目标用户: {user_id}")
    print(f"消息内容: {message}")
    print(f"先关注: {'是' if need_follow else '否'}")
    print(f"间隔时间: {interval}s")
    print("=" * 50)

    try:
        # 1. 搜索
        print(f"\n[1/6] 点击搜索框")
        dy.Click(*POSITIONS['点击搜索框'])
        time.sleep(interval)

        # 先全选删除原有内容
        import win32gui
        import win32api
        import win32con
        win32gui.SetForegroundWindow(dy.hwnd)
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(0x41, 0, 0, 0)  # A
        time.sleep(0.05)
        win32api.keybd_event(0x41, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.1)
        win32api.keybd_event(win32con.VK_DELETE, 0, 0, 0)
        win32api.keybd_event(win32con.VK_DELETE, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.2)

        print(f"[1/6] 输入用户ID: {user_id}")
        input_text_via_clipboard(user_id, dy.hwnd)
        time.sleep(interval)

        print(f"[2/6] 点击搜索")
        if '点击搜索' in POSITIONS:
            dy.Click(*POSITIONS['点击搜索'])
        else:
            SendKey(Keys.ENTER, dy.hwnd)
        time.sleep(interval)

        # 2. 点击头像
        print(f"[3/6] 点击用户头像")
        dy.Click(*POSITIONS['点击用户头像'])
        time.sleep(interval)

        # 3. 关注
        if need_follow:
            print(f"[4/6] 点击关注")
            dy.Click(*POSITIONS['点击头像内部的关注'])
            time.sleep(interval)

        # 4. 私信
        print(f"[5/6] 点击头像里面的私信")
        dy.Click(*POSITIONS['点击头像里面的私信'])
        time.sleep(interval)

        # 5. 发消息
        print(f"[6/6] 点击发送消息框")
        dy.Click(*POSITIONS['点击发送消息框'])
        time.sleep(0.5)

        print(f"[6/6] 输入消息: {message}")
        input_text_via_clipboard(message, dy.hwnd)
        time.sleep(0.3)

        print(f"[6/6] 发送")
        SendKey(Keys.ENTER, dy.hwnd)
        time.sleep(0.5)

        print("\n" + "=" * 50)
        print("发送完成！")
        print("=" * 50)

    except Exception as e:
        print(f"\n执行出错: {e}")


def main():
    print("=" * 50)
    print("  抖音私信发送工具")
    print("=" * 50)

    # 填充用户ID和消息
    user_id = USER_ID.strip()
    message = MESSAGE.strip()

    if not user_id:
        user_id = input("\n请输入用户ID: ").strip()
    if not user_id:
        print("用户ID不能为空")
        return

    if not message:
        message = input("请输入消息内容: ").strip()
    if not message:
        print("消息内容不能为空")
        return

    send_message(user_id, message, need_follow=NEED_FOLLOW, interval=INTERVAL)


if __name__ == '__main__':
    main()
