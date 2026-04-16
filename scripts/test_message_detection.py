# -*- coding: utf-8 -*-
"""
测试消息框检测和OCR识别功能
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import win32gui
import win32con
import win32ui
import win32api
from PIL import Image
import numpy as np
import cv2


def find_douyin_window():
    """查找抖音窗口 (使用 listen_messages.py 的算法)"""
    BROWSER_CLASSES = [
        "Chrome_WidgetWin_1",
        "Chrome_WidgetWin_0",
        "MSEdge_WidgetWin_0",
        "MSEdge_WidgetWin_1",
    ]
    title = "抖音"

    hwnd = win32gui.FindWindow("Chrome_WidgetWin_1", title)
    if hwnd:
        print("    方式1成功: Chrome_WidgetWin_1 + %s" % title)
        return hwnd

    hwnd = win32gui.FindWindow(None, title)
    if hwnd:
        print("    方式2成功: 标题=%s" % title)
        return hwnd

    for class_name in BROWSER_CLASSES:
        hwnd = win32gui.FindWindow(class_name, title)
        if hwnd:
            print("    方式3成功: %s + %s" % (class_name, title))
            return hwnd
        hwnd = win32gui.FindWindow(class_name, None)
        if hwnd:
            title_text = win32gui.GetWindowText(hwnd)
            if title_text and ("抖音" in title_text or "douyin" in title_text.lower()):
                print("    方式4成功: %s + %s" % (class_name, title_text))
                return hwnd

    def enum_callback(h, data):
        if win32gui.IsWindowVisible(h):
            try:
                title_text = win32gui.GetWindowText(h)
                if title_text and (
                    "抖音" in title_text or "douyin" in title_text.lower()
                ):
                    data.append((h, title_text))
            except:
                pass

    windows = []
    win32gui.EnumWindows(enum_callback, windows)
    if windows:
        print("    方式5成功: 枚举窗口找到 '%s'" % windows[0][1])
        return windows[0][0]
    return 0


def capture_screenshot(hwnd, dm_area=True):
    """使用 PIL 截图聊天窗口区域"""
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top

    from PIL import Image, ImageGrab

    if dm_area:
        # 私信聊天框的主区域（从 positions.txt 获取）
        # 私信聊天框的主区域左上：(0.6148, 0.1111)
        # 私信聊天框的主区域右下：(0.9306, 0.6800)
        x1 = int(left + width * 0.6148)
        y1 = int(top + height * 0.1111)
        x2 = int(left + width * 0.9306)
        y2 = int(top + height * 0.6800)
    else:
        # 整个窗口
        x1, y1, x2, y2 = left, top, right, bottom

    bbox = (x1, y1, x2, y2)
    img = ImageGrab.grab(bbox=bbox)

    temp_file = os.path.join(tempfile.gettempdir(), "dy_msg_test.png")
    img.save(temp_file)

    img_np = np.array(img)
    if len(img_np.shape) == 3 and img_np.shape[2] == 4:
        img_np = img_np[:, :, :3]

    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    return img_bgr, temp_file


def test_message_detection():
    print("=" * 50)
    print("抖音私信消息检测测试")
    print("=" * 50)

    # 允许用户输入自定义窗口标题
    print("\n请确认抖音PC客户端已打开")
    print("(窗口标题默认使用'抖音')")
    custom_title = None

    # 1. 查找窗口
    print("\n[1] 查找抖音窗口...")

    hwnd = find_douyin_window()
    if not hwnd:
        print("    未找到抖音窗口!")
        print("    请确认抖音PC客户端已打开")
        input("\n按回车键退出...")
        return

    print("    找到窗口, hwnd=%d" % hwnd)

    # 显示窗口信息
    title = win32gui.GetWindowText(hwnd)
    print("    窗口标题: %s" % title)

    # 激活窗口并固定大小
    print("\n[2] 激活窗口并固定大小...")
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.2)
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
        )
        time.sleep(0.2)

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        print("    窗口大小: %dx%d" % (width, height))

        # 强制设置窗口大小
        win32gui.SetWindowPos(
            hwnd,
            0,
            0,
            0,
            1080,
            900,
            win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW | win32con.SWP_NOMOVE,
        )
        time.sleep(0.3)

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        print("    重新设置后: %dx%d" % (width, height))

    except Exception as e:
        print("    错误: %s" % e)
        import traceback

        traceback.print_exc()
        input("\n按回车键退出...")
        return

    # 3. 点击私信位置打开私信窗口
    print("\n[3] 点击私信位置打开私信窗口...")
    try:
        # 根据 positions.txt，使用屏幕上方的私信入口位置 (0.7389, 0.0267)
        x = left + int(width * 0.7389)
        y = top + int(height * 0.0267)

        # 激活窗口（尝试多种方式）
        try:
            win32gui.SetForegroundWindow(hwnd)
        except:
            pass
        time.sleep(0.5)

        # 点击私信位置
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
        print("    已点击私信位置 (%d, %d)" % (x, y))
        time.sleep(2)  # 等待私信窗口打开

        # 重新获取窗口信息（可能有新窗口打开）
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
    except Exception as e:
        print("    点击私信位置错误：%s" % e)
        print("    继续使用当前窗口进行测试...")

    # 4. 截图
    print("\n[4] 截图...")
    try:
        screenshot, screenshot_path = capture_screenshot(hwnd)
        if screenshot is None:
            print("    截图失败!")
            input("\n按回车键退出...")
            return
        print("    截图尺寸: %dx%d" % (screenshot.shape[1], screenshot.shape[0]))
        print("    截图保存到: %s" % screenshot_path)
    except Exception as e:
        print("    截图错误: %s" % e)
        import traceback

        traceback.print_exc()
        input("\n按回车键退出...")
        return

    # 4. 导入并检测消息框（两阶段背景检测 + 回退检测）
    print("\n[4] 检测消息框位置...")
    try:
        from douyin_auto.vision import (
            detect_message_box,
            extract_messages_from_box,
        )

        box_info = detect_message_box(screenshot, debug=True)

        print("    消息框位置:")
        print("      left:   %.4f" % box_info["left"])
        print("      right:  %.4f" % box_info["right"])
        print("      top:    %.4f" % box_info["top"])
        print("      bottom: %.4f" % box_info["bottom"])

        # 保存调试图像
        if box_info.get("debug_image") is not None:
            debug_path = os.path.join(
                os.path.dirname(__file__), "..", "screenshots", "msg_box_debug.png"
            )
            cv2.imwrite(debug_path, box_info["debug_image"])
            print("    调试图像已保存：%s" % debug_path)

        # 生成并保存 mask 图片
        print("\n[4.1] 生成背景 mask 图片...")
        h, w = screenshot.shape[:2]
        opponent_color_bgr = np.array([76, 66, 66], dtype=np.uint8)
        my_color_bgr = np.array([255, 141, 41], dtype=np.uint8)
        tolerance = 20

        opponent_lower = np.array(
            [max(0, c - tolerance) for c in opponent_color_bgr], dtype=np.uint8
        )
        opponent_upper = np.array(
            [min(255, c + tolerance) for c in opponent_color_bgr], dtype=np.uint8
        )
        opponent_mask = cv2.inRange(screenshot, opponent_lower, opponent_upper)

        my_lower = np.array(
            [max(0, c - tolerance) for c in my_color_bgr], dtype=np.uint8
        )
        my_upper = np.array(
            [min(255, c + tolerance) for c in my_color_bgr], dtype=np.uint8
        )
        my_mask = cv2.inRange(screenshot, my_lower, my_upper)

        message_mask = cv2.bitwise_or(opponent_mask, my_mask)

        # 保存原始 mask
        mask_raw_path = os.path.join(
            os.path.dirname(__file__), "..", "screenshots", "msg_box_raw_mask.png"
        )
        cv2.imwrite(mask_raw_path, message_mask)
        print("    原始 mask 已保存：%s" % mask_raw_path)

        # 保存彩色 mask
        mask_img = np.zeros((h, w, 3), dtype=np.uint8)
        mask_img[opponent_mask > 0] = (100, 100, 100)
        mask_img[my_mask > 0] = (255, 141, 41)
        mask_path = os.path.join(
            os.path.dirname(__file__), "..", "screenshots", "msg_box_mask.png"
        )
        cv2.imwrite(mask_path, mask_img)
        print("    彩色 mask 已保存：%s" % mask_path)

        # 保存对方消息 mask
        opponent_mask_path = os.path.join(
            os.path.dirname(__file__), "..", "screenshots", "opponent_mask.png"
        )
        cv2.imwrite(opponent_mask_path, opponent_mask)
        print("    对方消息 mask 已保存：%s" % opponent_mask_path)

        # 保存我的消息 mask
        my_mask_path = os.path.join(
            os.path.dirname(__file__), "..", "screenshots", "my_mask.png"
        )
        cv2.imwrite(my_mask_path, my_mask)
        print("    我的消息 mask 已保存：%s" % my_mask_path)

    except Exception as e:
        print("    检测消息框错误：%s" % e)
        import traceback

        traceback.print_exc()
        input("\n按回车键退出...")
        return

    # 5. OCR提取消息
    print("\n[5] OCR识别消息文字...")
    try:
        box = box_info["box"]
        bubbles = box_info.get("bubbles", [])
        screenshots_dir = os.path.join(os.path.dirname(__file__), "..", "screenshots")
        messages = extract_messages_from_box(
            screenshot,
            box,
            bubbles=bubbles,
            debug=True,
            screenshots_dir=screenshots_dir,
        )

        if not messages:
            print("    未检测到任何文字")
            print(
                "    提示：每个气泡框的图片（带黑色边框扩展）已保存到 screenshots 目录 (bubble_*.png)"
            )
        else:
            print("    检测到 %d 条消息:" % len(messages))
            print("-" * 40)
            for i, msg in enumerate(messages):
                sender = "【我】" if msg["is_self"] else "【对方】"
                bubble_idx = msg.get("bubble_index", i)
                print(
                    "    %d. %s (气泡框%d) %s"
                    % (i + 1, sender, bubble_idx + 1, msg["text"])
                )
            print("-" * 40)
    except Exception as e:
        print("    OCR识别错误: %s" % e)
        import traceback

        traceback.print_exc()
        input("\n按回车键退出...")
        return

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
    input("\n按回车键退出...")


if __name__ == "__main__":
    test_message_detection()
