# -*- coding: utf-8 -*-
"""
抖音私信消息监听功能
流程：打开私信弹窗 -> 检测左侧用户区域红点 -> OCR识别数字 -> 点击红点打开会话
"""

import os
import sys
import time
import cv2
import numpy as np
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import win32gui
import win32con
import win32api
from PIL import Image, ImageGrab


def find_douyin_window():
    """查找抖音窗口"""
    BROWSER_CLASSES = [
        "Chrome_WidgetWin_1",
        "Chrome_WidgetWin_0",
        "MSEdge_WidgetWin_0",
        "MSEdge_WidgetWin_1",
    ]
    title = "抖音"

    hwnd = win32gui.FindWindow("Chrome_WidgetWin_1", title)
    if hwnd:
        return hwnd

    hwnd = win32gui.FindWindow(None, title)
    if hwnd:
        return hwnd

    for class_name in BROWSER_CLASSES:
        hwnd = win32gui.FindWindow(class_name, title)
        if hwnd:
            return hwnd
        hwnd = win32gui.FindWindow(class_name, None)
        if hwnd:
            title_text = win32gui.GetWindowText(hwnd)
            if title_text and ("抖音" in title_text or "douyin" in title_text.lower()):
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
        return windows[0][0]
    return 0


def activate_window(hwnd):
    """激活窗口"""
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.1)
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
    except Exception as e:
        print("激活窗口警告: %s" % e)


def click_at(screen_x, screen_y):
    """点击屏幕坐标"""
    win32api.SetCursorPos((screen_x, screen_y))
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def click_relative(hwnd, rel_x, rel_y):
    """根据相对坐标点击"""
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top
    x = int(left + rel_x * width)
    y = int(top + rel_y * height)
    click_at(x, y)


def find_reddot_by_color(image, target_bgr=(84, 45, 255), tolerance=20, min_area=30):
    """使用颜色检测红点 (RGB=255,45,84 -> BGR=84,45,255)"""
    h, w = image.shape[:2]

    target_color = np.array(target_bgr, dtype=np.uint8)
    lower = np.array([max(0, c - tolerance) for c in target_color], dtype=np.uint8)
    upper = np.array([min(255, c + tolerance) for c in target_color], dtype=np.uint8)

    mask = cv2.inRange(image, lower, upper)

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return False, 0, 0, 0

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    if area < min_area:
        return False, 0, 0, area

    x, y, cw, ch = cv2.boundingRect(largest)
    center_x = (x + cw / 2) / w
    center_y = (y + ch / 2) / h

    return True, center_x, center_y, area


def detect_reddot_by_color(image, min_area=30, debug=False):
    """使用颜色检测红点"""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)

    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)

    mask = cv2.bitwise_or(mask1, mask2)

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    pixel_count = cv2.countNonZero(mask)

    if pixel_count < min_area:
        return False, 0, 0, pixel_count, None

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False, 0, 0, pixel_count, None

    h, w = image.shape[:2]
    largest = max(contours, key=cv2.contourArea)
    x, y, cw, ch = cv2.boundingRect(largest)

    center_x = (x + cw / 2) / w
    center_y = (y + ch / 2) / h

    debug_image = None
    if debug:
        debug_image = image.copy()
        cv2.rectangle(debug_image, (x, y), (x + cw, y + ch), (0, 255, 0), 2)

    return True, center_x, center_y, pixel_count, debug_image


def expand_image_for_ocr(image, target_size=200):
    """将图像扩展到指定尺寸，背景填充黑色"""
    h, w = image.shape[:2]
    if h == 0 or w == 0:
        return np.zeros((target_size, target_size, 3), dtype=np.uint8)

    expanded = np.zeros((target_size, target_size, 3), dtype=np.uint8)
    start_x = (target_size - w) // 2
    start_y = (target_size - h) // 2
    expanded[start_y : start_y + h, start_x : start_x + w] = image
    return expanded


def keep_white_simple(image):
    """保留白色像素，其他颜色改成黑色（不膨胀）"""
    h, w = image.shape[:2]
    result = np.zeros((h, w, 3), dtype=np.uint8)

    lower_white = np.array([200, 200, 200])
    upper_white = np.array([255, 255, 255])
    mask = cv2.inRange(image, lower_white, upper_white)

    result[mask > 0] = (255, 255, 255)
    result[mask == 0] = (0, 0, 0)

    return result


def keep_white_convert(image):
    """保留白色像素，其他颜色改成黑色，并膨胀1次"""
    h, w = image.shape[:2]
    result = np.zeros((h, w, 3), dtype=np.uint8)

    lower_white = np.array([200, 200, 200])
    upper_white = np.array([255, 255, 255])
    mask = cv2.inRange(image, lower_white, upper_white)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.dilate(mask, kernel, iterations=1)

    result[mask > 0] = (255, 255, 255)
    result[mask == 0] = (0, 0, 0)

    return result


def recognize_number_with_ocr(image):
    """使用OCR识别图像中的数字"""
    if image is None:
        return "N/A"

    h, w = image.shape[:2]
    if h == 0 or w == 0:
        return "N/A"

    # 直接用原图识别
    try:
        from rapidocr import RapidOCR

        rapidocr = RapidOCR()

        # 转为RGB格式
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        output = rapidocr(pil_img)
        if output and output.txts:
            text = "".join(str(t) for t in output.txts).strip()
            if text:
                print("RapidOCR结果: %s" % text)
                return text
    except Exception as e:
        print("RapidOCR错误: %s" % e)

    # 尝试反转颜色（白底黑字）
    try:
        from rapidocr import RapidOCR

        rapidocr = RapidOCR()

        # 反转颜色
        inverted = cv2.bitwise_not(image)
        img_rgb = cv2.cvtColor(inverted, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        output = rapidocr(pil_img)
        if output and output.txts:
            text = "".join(str(t) for t in output.txts).strip()
            if text:
                print("反转颜色结果: %s" % text)
                return text
    except Exception as e:
        print("反转错误: %s" % e)

    return "N/A"

    # 尝试 RapidOCR
    try:
        from rapidocr import RapidOCR

        rapidocr = RapidOCR()
        output = rapidocr(pil_img)
        if output and output.txts:
            return "".join(str(t) for t in output.txts).strip()
    except Exception as e:
        print("RapidOCR: %s" % e)

    # 尝试 cnocr
    try:
        from cnocr import CnOcr

        cnocr = CnOcr()
        results = cnocr(pil_img)
        if results and len(results) > 0:
            texts = [r.get("text", "").strip() for r in results if r.get("text")]
            return "".join(texts)
    except Exception as e:
        print("cnocr: %s" % e)

    # 尝试 pytesseract
    try:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = (
            r"D:\Program Files\Tesseract-OCR\tesseract.exe"
        )
        text = pytesseract.image_to_string(pil_img, lang="eng")
        return text.strip()
    except Exception as e:
        print("pytesseract: %s" % e)

    return "N/A"


def get_chat_window_area(hwnd):
    """获取私信聊天窗口最大范围"""
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top

    x1 = int(left + width * 0.3454)
    y1 = int(top + height * 0.0689)
    x2 = int(left + width * 0.9657)
    y2 = int(top + height * 0.7522)

    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    img_np = np.array(img)

    if len(img_np.shape) == 3 and img_np.shape[2] == 4:
        img_np = img_np[:, :, :3]

    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    return img_bgr, {"x1": x1, "y1": y1, "left": left, "top": top}


def get_session_list_area(hwnd):
    """获取私信聊天窗口最大范围"""
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top

    x1 = int(left + width * 0.3454)
    y1 = int(top + height * 0.0689)
    x2 = int(left + width * 0.9657)
    y2 = int(top + height * 0.7522)

    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    img_np = np.array(img)

    if len(img_np.shape) == 3 and img_np.shape[2] == 4:
        img_np = img_np[:, :, :3]

    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    return img_bgr, {"x1": x1, "y1": y1, "left": left, "top": top}


def save_debug_image(image, name):
    """保存调试图像"""
    dir_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    path = os.path.join(dir_path, name)
    cv2.imwrite(path, image)
    print("调试图像已保存: %s" % path)


def continuous_listen(interval=5):
    """持续监听模式"""
    print("=" * 60)
    print("进入持续监听模式")
    print("按 Ctrl+C 停止")
    print("=" * 60)

    count = 0
    try:
        while True:
            count += 1
            print("\n第 %d 次检查" % count)
            try:
                main()
            except Exception as e:
                print("检查错误: %s" % e)
            print("等待 %d 秒..." % interval)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n监听停止，共检查 %d 次" % count)


def send_hello_message(hwnd):
    """发送"你好"消息"""
    import win32gui
    import win32api
    import win32con

    try:
        from douyin_auto.positions import POSITIONS

        # 点击发送消息框
        if "点击发送消息框" in POSITIONS:
            rx, ry = POSITIONS["点击发送消息框"]
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            x = int(left + rx * width)
            y = int(top + ry * height)
            click_at(x, y)
            print("点击发送消息框")
            time.sleep(0.5)

        # 输入"你好"
        win32gui.SetForegroundWindow(hwnd)
        import win32clipboard

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText("你好", win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()

        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(0x56, 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.3)

        # 按回车发送
        win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.5)

        print("消息已发送: 你好")

    except Exception as e:
        print("发送消息失败: %s" % e)


def click_top_user(hwnd):
    """点击置顶用户回到列表"""
    import win32gui

    try:
        from douyin_auto.positions import POSITIONS

        if "私信聊天框左侧用户区域置顶用户" in POSITIONS:
            rx, ry = POSITIONS["私信聊天框左侧用户区域置顶用户"]
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            x = int(left + rx * width)
            y = int(top + ry * height)
            print("点击置顶用户回到列表: (%d, %d)" % (x, y))
            click_at(x, y)
            time.sleep(0.5)
    except Exception as e:
        print("点击置顶用户失败: %s" % e)


def main():
    # 1. 查找窗口并固定位置大小
    try:
        from douyin_auto import Douyin

        dy = Douyin.open()
        hwnd = dy.hwnd
    except Exception as e:
        print("未找到抖音窗口: %s" % e)
        return

    activate_window(hwnd)
    time.sleep(0.3)

    # 2. 点击私信按钮
    click_relative(hwnd, 0.7389, 0.0267)
    time.sleep(1.0)

    # 3. 获取私信聊天窗口截图
    chat_img, chat_area_info = get_chat_window_area(hwnd)
    h_chat, w_chat = chat_img.shape[:2]
    save_debug_image(chat_img, "chat_window.png")

    # 4. 检测user_open.jpg是否存在
    user_open_template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "douyin_auto",
        "templates",
        "user_open.jpg",
    )
    user_found = False
    user_rx, user_ry = 0, 0

    print("检测user_open.jpg...")
    # user_open检测暂时跳过

    if False:
        # 移动鼠标到user_open位置并点击
        abs_x = chat_area_info["x1"] + int(user_rx * w_chat)
        abs_y = chat_area_info["y1"] + int(user_ry * h_chat)
        print("检测到user_open: (%d, %d), 点击进入..." % (abs_x, abs_y))
        click_at(abs_x, abs_y)
        time.sleep(1.0)

        # 重新获取截图
        chat_img, chat_area_info = get_chat_window_area(hwnd)
        save_debug_image(chat_img, "chat_window_after_click.png")

    # 5. 使用颜色检测红点 (RGB=255,45,84 -> BGR=84,45,255)
    print("检测聊天窗口消息红点...")
    found = False
    rx, ry = 0, 0
    area = 0

    found, rx, ry, area = find_reddot_by_color(
        chat_img, target_bgr=(84, 45, 255), tolerance=20, min_area=30
    )
    if found:
        print("检测到红点! 像素面积: %d" % area)

    if found:
        # 黑色像素扩展
        offset = 20
        x1_crop = max(0, int(rx * w_chat) - offset)
        y1_crop = max(0, int(ry * h_chat) - offset)
        x2_crop = min(w_chat, int(rx * w_chat) + offset)
        y2_crop = min(h_chat, int(ry * h_chat) + offset)
        reddot_crop = chat_img[y1_crop:y2_crop, x1_crop:x2_crop]
        expanded = expand_image_for_ocr(reddot_crop, target_size=200)

        # 第一次：白色像素保留（不膨胀），直接OCR
        white_image = keep_white_simple(expanded)
        save_debug_image(white_image, "reddot_white.png")
        number_text = recognize_number_with_ocr(white_image)

        numbers = re.findall(r"\d+", number_text)

        # 如果没识别到，第二次膨胀后再OCR
        if not numbers:
            print("第一次未识别到，进行膨胀...")
            white_image_dilate = keep_white_convert(expanded)
            save_debug_image(white_image_dilate, "reddot_dilate.png")
            number_text = recognize_number_with_ocr(white_image_dilate)
            numbers = re.findall(r"\d+", number_text)

        if numbers:
            print("OCR识别结果: %s" % number_text)
            print("检测到未读消息数量: %s" % numbers[0])

            # 点击红点进入聊天界面
            abs_x = chat_area_info["x1"] + int(rx * w_chat)
            abs_y = chat_area_info["y1"] + int(ry * h_chat)
            print("点击红点进入聊天: (%d, %d)" % (abs_x, abs_y))
            click_at(abs_x, abs_y)
            time.sleep(1.0)

            # 发送"你好"消息
            send_hello_message(hwnd)

            # 发送完后点击置顶用户回到列表，准备下一次监听
            click_top_user(hwnd)
        else:
            print("OCR识别结果: %s" % number_text)
            print("检测到红点但未识别到数字")
    else:
        print("未检测到消息红点")


if __name__ == "__main__":
    main()
    continuous_listen(3)
