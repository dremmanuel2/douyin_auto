"""
抖音私信发送工具

使用方法：
    python scripts/send_message.py

每一步的点击间隔可自定义修改底部的 INTERVAL 配置

支持两种私信入口：
1. 通过搜索用户进入用户界面的私信按钮
2. 程序屏幕上方的私信入口
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from douyin_auto import Douyin
from douyin_auto.positions import POSITIONS
from douyin_auto.utils import SetClipboardText, SendKey, Keys
from douyin_auto.vision import (
    verify_search_result,
    verify_private_message_button,
    verify_message_input,
    expand_image_for_ocr,
    recognize_text,
)
import cv2
import numpy as np
from PIL import ImageGrab


# ============ 可调整的参数 ============
USER_ID = "86759655452"  # 搜索的用户ID，留空则运行时输入
MESSAGE = "你好"  # 发送的消息内容，留空则运行时输入
INTERVAL = 3.0  # 每步之间等待的秒数（可根据需要调整）
NEED_FOLLOW = False  # 是否先关注再发消息
MESSAGE_ENTRY = "search_result"  # 私信入口类型: "search_result" 或 "top_screen"
# ====================================


def load_config():
    """加载配置文件"""
    import json
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"interval": 1.0, "validation_repeat": 5}


def wait_and_verify(dy, verify_func, position_key, stage_name=""):
    """
    等待并验证页面状态
    
    Args:
        dy: Douyin 实例
        verify_func: 验证函数
        position_key: 位置配置键名
        stage_name: 阶段名称
    
    Returns:
        success: bool
    """
    config = load_config()
    max_retries = config.get("validation_repeat", 5)
    interval = config.get("interval", 1.0)
    
    print("    正在验证{}...".format(stage_name))
    
    for i in range(max_retries):
        try:
            if position_key not in POSITIONS:
                print("    警告：缺少位置配置 {}".format(position_key))
                time.sleep(interval)
                continue
            
            x, y = POSITIONS[position_key]
            left, top, right, bottom = win32gui.GetWindowRect(dy.hwnd)
            width = right - left
            height = bottom - top
            
            # 计算截图区域
            screenshot_width = int(width * 0.15)
            screenshot_height = int(height * 0.15)
            x1 = int(left + x * width)
            y1 = int(top + y * height)
            x2 = min(x1 + screenshot_width, right)
            y2 = min(y1 + screenshot_height, bottom)
            
            if x2 - x1 < 50:
                x2 = min(x1 + 150, right)
            if y2 - y1 < 50:
                y2 = min(y1 + 150, bottom)
            
            # 截图
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            img_np = np.array(img)
            if len(img_np.shape) == 3 and img_np.shape[2] == 4:
                img_np = img_np[:, :, :3]
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            # 验证
            success, ocr_text = verify_func(img_bgr)
            
            if success:
                print("    ✓ {}验证成功，识别到：{}".format(stage_name, ocr_text))
                return True
            else:
                if i < max_retries - 1:
                    print("    第{}次验证未通过（识别：{}），{}秒后重试...".format(
                        i + 1, ocr_text if ocr_text else "无文字", interval))
                    time.sleep(interval)
                else:
                    print("    ✗ {}验证失败（已达最大重试次数）".format(stage_name))
                    
        except Exception as e:
            if i < max_retries - 1:
                print("    验证异常：{}，{}秒后重试...".format(e, interval))
                time.sleep(interval)
            else:
                print("    ✗ 验证异常：{}（已达最大重试次数）".format(e))
    
    return False


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


def send_message_via_search(user_id, message, need_follow=True, interval=1.0):
    """
    通过搜索用户进入用户界面的私信按钮发送私信

    Args:
        user_id: 目标用户ID
        message: 消息内容
        need_follow: 是否先关注
        interval: 每步间隔（秒）
    """
    dy = Douyin.open()
    print("窗口大小: {}x{}".format(dy.width, dy.height))
    print()

    # 检查必要点位
    required = ["点击搜索框", "点击用户头像"]
    if need_follow:
        required.append("点击头像内的关注")
    required.extend(["点击头像内的私信", "点击发送消息框"])

    missing = [r for r in required if r not in POSITIONS]
    if missing:
        print("[错误] 缺少必要点位: {}".format(missing))
        print("请先运行 calibrate_position.py 校准以上点位")
        return

    print("目标用户: {}".format(user_id))
    print("消息内容: {}".format(message))
    print("先关注: {}".format("是" if need_follow else "否"))
    print("间隔时间: {}s".format(interval))
    print("=" * 50)

    try:
        # 1. 搜索
        print("\n[1/6] 点击搜索框")
        dy.Click(*POSITIONS["点击搜索框"])
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

        print("[1/6] 输入用户ID: {}".format(user_id))
        input_text_via_clipboard(user_id, dy.hwnd)
        time.sleep(interval)

        print("[2/6] 点击搜索")
        if "点击搜索" in POSITIONS:
            dy.Click(*POSITIONS["点击搜索"])
        else:
            SendKey(Keys.ENTER, dy.hwnd)
        time.sleep(interval)

        # 验证 1：搜索结果页面是否加载完成（识别"抖音号"）
        print("\n[验证 1] 检测搜索结果页面")
        wait_and_verify(dy, verify_search_result, "点击用户头像", "搜索结果页面")

        # 2. 点击头像
        print("\n[3/7] 点击用户头像")
        dy.Click(*POSITIONS["点击用户头像"])
        time.sleep(interval)

        # 验证 2：私信按钮是否可见（识别"私信"）
        print("\n[验证 2] 检测私信按钮")
        wait_and_verify(dy, verify_private_message_button, "点击私信", "私信按钮")

        # 3. 关注
        if need_follow:
            print("[4/6] 点击关注")
            dy.Click(*POSITIONS["点击头像内的关注"])
            time.sleep(interval)

        # 4. 私信
        print("[5/7] 点击头像内的私信")
        dy.Click(*POSITIONS["点击头像内的私信"])
        time.sleep(interval)

        # 验证 3：消息输入框是否可用（识别"发送消息"）
        print("\n[验证 3] 检测消息输入框")
        wait_and_verify(dy, verify_message_input, "点击发送消息框", "消息输入框")

        # 5. 发消息
        print("[6/7] 点击发送消息框")
        dy.Click(*POSITIONS["点击发送消息框"])
        time.sleep(0.5)

        print("[6/6] 输入消息: {}".format(message))
        input_text_via_clipboard(message, dy.hwnd)
        time.sleep(0.3)

        print("[6/6] 发送")
        SendKey(Keys.ENTER, dy.hwnd)
        time.sleep(0.5)

        print("\n" + "=" * 50)
        print("发送完成！")
        print("=" * 50)

    except Exception as e:
        print("\n执行出错: {}".format(e))


def send_message_via_top(user_id, message, interval=1.0):
    """
    通过程序屏幕上方的私信入口发送私信

    Args:
        user_id: 目标用户ID
        message: 消息内容
        interval: 每步间隔（秒）
    """
    dy = Douyin.open()
    print("窗口大小: {}x{}".format(dy.width, dy.height))
    print()

    # 检查必要点位
    required = ["屏幕上方的私信入口", "点击发送消息框"]
    missing = [r for r in required if r not in POSITIONS]
    if missing:
        print("[错误] 缺少必要点位: {}".format(missing))
        print("请先运行 calibrate_position.py 校准以上点位")
        return

    print("目标用户: {}".format(user_id))
    print("消息内容: {}".format(message))
    print("间隔时间: {}s".format(interval))
    print("=" * 50)

    try:
        # 1. 点击屏幕上方的私信入口
        print("\n[1/4] 点击屏幕上方的私信入口")
        dy.Click(*POSITIONS["屏幕上方的私信入口"])
        time.sleep(interval)

        # 2. 搜索用户
        print("[2/4] 搜索用户: {}".format(user_id))
        # 这里需要根据实际界面情况实现搜索用户的功能
        # 暂时使用默认的搜索方法
        dy.Search(user_id)
        time.sleep(interval)

        # 3. 点击用户头像
        print("[3/4] 点击用户头像")
        dy.ClickUserAvatar()
        time.sleep(interval)

        # 4. 点击私信按钮
        print("[4/4] 点击私信按钮")
        dy.ClickPrivateMessage()
        time.sleep(interval)

        # 5. 发消息
        print("[5/5] 点击发送消息框")
        dy.ClickMessageInput()
        time.sleep(0.5)

        print("[5/5] 输入消息: {}".format(message))
        input_text_via_clipboard(message, dy.hwnd)
        time.sleep(0.3)

        print("[5/5] 发送")
        SendKey(Keys.ENTER, dy.hwnd)
        time.sleep(0.5)

        print("\n" + "=" * 50)
        print("发送完成！")
        print("=" * 50)

    except Exception as e:
        print("\n执行出错: {}".format(e))


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

    # 根据配置选择私信入口
    if MESSAGE_ENTRY == "search_result":
        send_message_via_search(
            user_id, message, need_follow=NEED_FOLLOW, interval=INTERVAL
        )
    elif MESSAGE_ENTRY == "top_screen":
        send_message_via_top(user_id, message, interval=INTERVAL)
    else:
        print("无效的私信入口类型: {}".format(MESSAGE_ENTRY))
        print("请使用 'search_result' 或 'top_screen'")


if __name__ == "__main__":
    main()
