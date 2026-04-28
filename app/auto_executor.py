# -*- coding: utf-8 -*-
"""
抖音私信自动化执行程序
功能：
1. 监听私信消息红点（集成 listen_messages.py 的功能）
2. 查询数据库中的待执行消息队列
3. 按时间顺序执行发送任务
4. 频率控制和重试机制
5. 记录发送日志
"""

import sys
import os
import time
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from douyin_auto.db_utils import MySQLDBManager
from douyin_auto.mq_utils import RabbitMQManager
from douyin_auto.mq_config import (
    RATE_LIMIT_CONFIG,
    RETRY_CONFIG,
    LISTEN_CONFIG,
    LOG_CONFIG,
)
from douyin_auto import Douyin
from douyin_auto.positions import POSITIONS
from douyin_auto.utils import SetClipboardText, SendKey, Keys
from douyin_auto.vision import (
    verify_search_result,
    verify_private_message_button,
    verify_message_input,
    verify_private_message_input_box,
    verify_user_homepage_private_button,
)
import win32gui
import win32con
import win32api
import win32clipboard
import cv2
import numpy as np
from PIL import Image, ImageGrab


def setup_logger():
    """配置日志记录器"""
    log_dir = LOG_CONFIG.get("log_dir", "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    today = datetime.now().strftime("%Y%m%d")
    executor_log = os.path.join(log_dir, f"executor_{today}.log")
    error_log = os.path.join(log_dir, f"error_{today}.log")

    logger = logging.getLogger("AutoExecutor")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        logger.handlers.clear()

    file_handler = logging.FileHandler(executor_log, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    error_handler = logging.FileHandler(error_log, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()


def load_config():
    """加载配置文件"""
    import json
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"interval": 1.0, "validation_repeat": 5}


def find_reddot_by_color(image, target_bgr=(84, 45, 255), tolerance=40, min_area=30):
    """使用颜色检测红点 (RGB=255,45,84 -> BGR=84,45,255)"""
    h, w = image.shape[:2]

    target_color = np.array(target_bgr, dtype=np.uint8)
    lower = np.array([max(0, int(c) - tolerance) for c in target_color], dtype=np.uint8)
    upper = np.array([min(255, int(c) + tolerance) for c in target_color], dtype=np.uint8)

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


def recognize_number_with_ocr(image):
    """使用 OCR 识别图像中的数字"""
    if image is None:
        return "N/A"

    h, w = image.shape[:2]
    if h == 0 or w == 0:
        return "N/A"

    try:
        from rapidocr import RapidOCR

        rapidocr = RapidOCR()

        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        output = rapidocr(pil_img)
        if output and output.txts:
            text = "".join(str(t) for t in output.txts).strip()
            if text:
                return text
    except Exception as e:
        logger.debug(f"RapidOCR 错误：{e}")

    try:
        from rapidocr import RapidOCR

        rapidocr = RapidOCR()

        inverted = cv2.bitwise_not(image)
        img_rgb = cv2.cvtColor(inverted, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        output = rapidocr(pil_img)
        if output and output.txts:
            text = "".join(str(t) for t in output.txts).strip()
            if text:
                return text
    except Exception as e:
        logger.debug(f"反转 OCR 错误：{e}")

    return "N/A"


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


def get_chat_window_area(hwnd):
    """获取私信聊天窗口范围"""
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


def send_hello_message(hwnd):
    """发送"你好"消息"""
    try:
        from douyin_auto.positions import POSITIONS

        if "点击发送消息框" in POSITIONS:
            rx, ry = POSITIONS["点击发送消息框"]
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            x = int(left + rx * width)
            y = int(top + ry * height)
            click_at(x, y)
            logger.debug("点击发送消息框")
            time.sleep(0.5)

        win32gui.SetForegroundWindow(hwnd)

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

        win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.5)

        logger.info("自动回复消息：你好")

    except Exception as e:
        logger.error(f"发送消息失败：{e}")


def click_top_user(hwnd):
    """点击置顶用户回到列表"""
    try:
        from douyin_auto.positions import POSITIONS

        if "私信聊天框左侧用户区域置顶用户" in POSITIONS:
            rx, ry = POSITIONS["私信聊天框左侧用户区域置顶用户"]
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            x = int(left + rx * width)
            y = int(top + ry * height)
            logger.debug(f"点击置顶用户回到列表：({x}, {y})")
            click_at(x, y)
            time.sleep(0.5)
    except Exception as e:
        logger.error(f"点击置顶用户失败：{e}")


def get_message_box_area(hwnd):
    """获取消息框区域"""
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top

    # 消息框区域（右侧聊天区域）
    x1 = int(left + width * 0.35)
    y1 = int(top + height * 0.08)
    x2 = int(left + width * 0.95)
    y2 = int(top + height * 0.70)

    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    img_np = np.array(img)

    if len(img_np.shape) == 3 and img_np.shape[2] == 4:
        img_np = img_np[:, :, :3]

    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    return img_bgr, {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


def recognize_messages_from_image(image):
    """从图像中识别消息"""
    messages = []

    try:
        from rapidocr import RapidOCR

        rapidocr = RapidOCR()

        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        output = rapidocr(pil_img)
        if output and output.txts:
            for text_box in output.txts:
                text = str(text_box).strip()
                if text and len(text) > 0:
                    messages.append(text)
    except Exception as e:
        logger.debug(f"OCR 识别消息失败：{e}")

    return messages


class AutoExecutor:
    """自动化执行器"""

    def __init__(self):
        """初始化自动化执行器"""
        self.db_manager: Optional[MySQLDBManager] = None
        self.mq_manager: Optional[RabbitMQManager] = None
        self.douyin: Optional[Douyin] = None
        self.hwnd = None
        self.last_send_time: float = 0
        self.today_send_count: int = 0
        self.running: bool = False

    def initialize(self) -> bool:
        """
        初始化数据库、RabbitMQ 和抖音窗口

        Returns:
            bool: 初始化是否成功
        """
        logger.info("=" * 60)
        logger.info("启动抖音私信自动化执行程序")
        logger.info("=" * 60)

        try:
            self.db_manager = MySQLDBManager()
            if not self.db_manager.connect():
                logger.error("数据库连接失败")
                return False
            logger.info("数据库连接成功")

            self.today_send_count = self.db_manager.get_today_send_count()
            logger.info(
                f"今日已发送：{self.today_send_count}/{RATE_LIMIT_CONFIG['daily_limit']}"
            )

            self.mq_manager = RabbitMQManager()
            if not self.mq_manager.connect():
                logger.error("RabbitMQ 连接失败")
                return False
            
            if not self.mq_manager.initialize_queues():
                logger.error("RabbitMQ 队列初始化失败")
                return False
            logger.info("RabbitMQ 初始化成功")

            try:
                self.douyin = Douyin.open()
                self.hwnd = self.douyin.hwnd
                logger.info(f"抖音窗口已打开：{self.douyin.width}x{self.douyin.height}")
            except Exception as e:
                logger.error(f"打开抖音窗口失败：{e}")
                return False

            return True

        except Exception as e:
            logger.error(f"初始化异常：{e}")
            return False

    def cleanup(self):
        """清理资源"""
        logger.info("清理资源...")
        if self.db_manager:
            self.db_manager.disconnect()
        if self.mq_manager:
            self.mq_manager.disconnect()
        self.running = False

    def recognize_messages(self, expected_count=10):
        """
        识别当前聊天窗口中的消息

        Args:
            expected_count: 期望识别的消息数量

        Returns:
            list: 消息列表
        """
        try:
            logger.debug("正在识别消息框中的消息...")

            # 获取消息框区域
            msg_img, msg_info = get_message_box_area(self.hwnd)

            # 识别消息
            messages = recognize_messages_from_image(msg_img)

            # 返回最新的消息（最后几条）
            if messages:
                latest_messages = (
                    messages[-expected_count:]
                    if len(messages) > expected_count
                    else messages
                )
                logger.debug(f"识别到 {len(latest_messages)} 条消息")
                return latest_messages

            return []

        except Exception as e:
            logger.error(f"识别消息失败：{e}")
            return []
    
    def _wait_and_verify(self, verify_func, position_key, stage_name="",
                         max_retries=None, interval=None, abort_on_fail=False):
        """
        等待并验证页面状态
        
        Args:
            verify_func: 验证函数
            position_key: 位置配置键名
            stage_name: 阶段名称
            max_retries: 最大重试次数
            interval: 重试间隔（秒）
            abort_on_fail: 验证失败时是否中止流程
        
        Returns:
            (success, should_abort): tuple
        """
        config = load_config()
        if max_retries is None:
            max_retries = config.get("validation_repeat", 5)
        if interval is None:
            interval = config.get("interval", 1.0)
        
        logger.debug("    正在验证{}...".format(stage_name))
        
        for i in range(max_retries):
            try:
                # 确保窗口在前台
                self.douyin._ensure_foreground()
                time.sleep(0.3)
                
                if position_key not in POSITIONS:
                    logger.warning("    缺少位置配置 {}".format(position_key))
                    time.sleep(interval)
                    continue
                
                x, y = POSITIONS[position_key]
                left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
                width = right - left
                height = bottom - top
                
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
                
                img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                img_np = np.array(img)
                if len(img_np.shape) == 3 and img_np.shape[2] == 4:
                    img_np = img_np[:, :, :3]
                img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                
                success, ocr_text = verify_func(img_bgr)
                
                if success:
                    logger.info("    ✓ {}验证成功，识别到：{}".format(stage_name, ocr_text))
                    return True, False
                else:
                    if i < max_retries - 1:
                        logger.debug("    第{}次验证未通过（识别：{}），{}秒后重试...".format(
                            i + 1, ocr_text if ocr_text else "无文字", interval))
                        time.sleep(interval)
                    else:
                        logger.warning("    ✗ {}验证失败（已达最大重试次数{}次）".format(stage_name, max_retries))
                        if abort_on_fail:
                            logger.info("    → 中止当前发送流程，返回监听状态")
                            return False, True
                        return False, False
                        
            except Exception as e:
                if i < max_retries - 1:
                    logger.debug("    验证异常：{}，{}秒后重试...".format(e, interval))
                    time.sleep(interval)
                else:
                    logger.error("    ✗ 验证异常：{}（已达最大重试次数）".format(e))
                    if abort_on_fail:
                        logger.info("    → 中止当前发送流程，返回监听状态")
                        return False, True
                    return False, False
        
        return False, False

    def verify_and_click_message_input(self, max_retries=None, interval=None) -> bool:
        """
        验证并点击消息输入框
        
        流程：
        1. 优先在私信会话栏区域截图检测"发送消息"文字
        2. 如果检测到，则点击发送消息框
        3. 如果未检测到，重试多次后回退到默认检测方式
        
        Args:
            max_retries: 最大重试次数
            interval: 重试间隔（秒）
        
        Returns:
            bool: 验证是否成功
        """
        config = load_config()
        if max_retries is None:
            max_retries = config.get("validation_repeat", 5)
        if interval is None:
            interval = config.get("interval", 1.0)
        
        logger.debug("    正在验证消息输入框...")
        
        # 检查是否有私信会话栏区域配置
        has_private_area = (
            "私信会话栏中的发送消息框的左上" in POSITIONS and
            "私信会话栏中的发送消息框的右下" in POSITIONS
        )
        
        if has_private_area:
            # 优先使用私信会话栏区域检测
            x1_rel, y1_rel = POSITIONS["私信会话栏中的发送消息框的左上"]
            x2_rel, y2_rel = POSITIONS["私信会话栏中的发送消息框的右下"]
            
            for i in range(max_retries):
                try:
                    # 确保窗口在前台
                    self.douyin._ensure_foreground()
                    time.sleep(0.3)
                    
                    left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
                    width = right - left
                    height = bottom - top
                    
                    # 计算私信会话栏区域
                    x1 = int(left + x1_rel * width)
                    y1 = int(top + y1_rel * height)
                    x2 = int(left + x2_rel * width)
                    y2 = int(top + y2_rel * height)
                    
                    # 截图
                    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                    img_np = np.array(img)
                    if len(img_np.shape) == 3 and img_np.shape[2] == 4:
                        img_np = img_np[:, :, :3]
                    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                    
                    # OCR 验证
                    success, ocr_text = verify_private_message_input_box(img_bgr)
                    
                    if success:
                        logger.info("    ✓ 私信会话栏验证成功，识别到：{}".format(ocr_text))
                        
                        # 点击发送消息框
                        if "点击发送消息框" in POSITIONS:
                            click_x, click_y = POSITIONS["点击发送消息框"]
                            logger.debug("    点击发送消息框：相对坐标 ({}, {})".format(click_x, click_y))
                            self.douyin.Click(click_x, click_y)
                            time.sleep(1.0)
                            return True
                        else:
                            logger.error("    缺少位置配置：点击发送消息框")
                            return False
                    else:
                        if i < max_retries - 1:
                            logger.debug("    第{}次验证未通过（识别：{}），{}秒后重试...".format(
                                i + 1, ocr_text if ocr_text else "无文字", interval))
                            time.sleep(interval)
                        else:
                            logger.warning("    ✗ 私信会话栏验证失败（已达最大重试次数{}次）".format(max_retries))
                            break
                            
                except Exception as e:
                    if i < max_retries - 1:
                        logger.debug("    验证异常：{}，{}秒后重试...".format(e, interval))
                        time.sleep(interval)
                    else:
                        logger.error("    ✗ 验证异常：{}（已达最大重试次数）".format(e))
                        break
        
        # 回退到默认检测方式
        logger.debug("    回退到默认消息输入框检测方式...")
        success, should_abort = self._wait_and_verify(
            verify_message_input,
            "点击发送消息框",
            "消息输入框",
            max_retries=max_retries,
            interval=interval,
            abort_on_fail=False
        )
        
        if success:
            # 点击发送消息框
            if "点击发送消息框" in POSITIONS:
                click_x, click_y = POSITIONS["点击发送消息框"]
                self.douyin.Click(click_x, click_y)
                time.sleep(1.0)
                return True
        
        return False

    def verify_and_click_user_homepage_private_button(
        self, max_retries=None, interval=None
    ) -> bool:
        """
        验证并点击用户主页的私信按钮
        
        流程：
        1. 在用户主页的私信按钮区域截图检测"私信"文字
        2. 如果检测到，则点击私信按钮
        3. 如果未检测到，重试多次后返回失败
        
        Args:
            max_retries: 最大重试次数
            interval: 重试间隔（秒）
        
        Returns:
            bool: 验证是否成功
        """
        config = load_config()
        if max_retries is None:
            max_retries = config.get("validation_repeat", 5)
        if interval is None:
            interval = config.get("interval", 1.0)
        
        logger.debug("    正在验证用户主页私信按钮...")
        
        # 检查是否有用户主页私信按钮区域配置
        has_private_button_area = (
            "进入用户主页的私信按钮左上" in POSITIONS and
            "进入用户主页的私信按钮右下" in POSITIONS
        )
        
        if not has_private_button_area:
            logger.error("    缺少位置配置：进入用户主页的私信按钮区域")
            return False
        
        x1_rel, y1_rel = POSITIONS["进入用户主页的私信按钮左上"]
        x2_rel, y2_rel = POSITIONS["进入用户主页的私信按钮右下"]
        
        for i in range(max_retries):
            try:
                # 确保窗口在前台
                self.douyin._ensure_foreground()
                time.sleep(0.3)
                
                left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
                width = right - left
                height = bottom - top
                
                # 计算用户主页私信按钮区域
                x1 = int(left + x1_rel * width)
                y1 = int(top + y1_rel * height)
                x2 = int(left + x2_rel * width)
                y2 = int(top + y2_rel * height)
                
                # 截图
                img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                img_np = np.array(img)
                if len(img_np.shape) == 3 and img_np.shape[2] == 4:
                    img_np = img_np[:, :, :3]
                img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                
                # OCR 验证
                success, ocr_text = verify_user_homepage_private_button(img_bgr)
                
                if success:
                    logger.info("    ✓ 用户主页私信按钮验证成功，识别到：{}".format(ocr_text))
                    
                    # 点击私信按钮
                    if "点击头像内的私信" in POSITIONS:
                        click_x, click_y = POSITIONS["点击头像内的私信"]
                        logger.debug("    点击私信按钮：相对坐标 ({}, {})".format(click_x, click_y))
                        self.douyin.Click(click_x, click_y)
                        time.sleep(1.0)
                        return True
                    else:
                        logger.error("    缺少位置配置：点击头像内的私信")
                        return False
                else:
                    if i < max_retries - 1:
                        logger.debug("    第{}次验证未通过（识别：{}），{}秒后重试...".format(
                            i + 1, ocr_text if ocr_text else "无文字", interval))
                        time.sleep(interval)
                    else:
                        logger.warning("    ✗ 用户主页私信按钮验证失败（已达最大重试次数{}次）".format(max_retries))
                        break
                        
            except Exception as e:
                if i < max_retries - 1:
                    logger.debug("    验证异常：{}，{}秒后重试...".format(e, interval))
                    time.sleep(interval)
                else:
                    logger.error("    ✗ 验证异常：{}（已达最大重试次数）".format(e))
                    break
        
        return False

    def check_rate_limit(self) -> bool:
        """
        检查发送频率限制

        Returns:
            bool: 是否可以发送
        """
        if self.today_send_count >= RATE_LIMIT_CONFIG["daily_limit"]:
            logger.warning(
                f"已达到今日发送上限：{self.today_send_count}/"
                f"{RATE_LIMIT_CONFIG['daily_limit']}"
            )
            return False

        elapsed = time.time() - self.last_send_time
        if elapsed < RATE_LIMIT_CONFIG["send_interval"]:
            wait_time = RATE_LIMIT_CONFIG["send_interval"] - elapsed
            logger.info(f"频率控制：等待 {wait_time:.1f}秒")
            time.sleep(wait_time)

        return True

    def send_message(self, douyin_id: str, message: str) -> bool:
        """
        发送私信消息

        Args:
            douyin_id: 目标用户抖音 ID
            message: 消息内容

        Returns:
            bool: 发送是否成功
        """
        try:
            logger.info(f"正在发送消息给 {douyin_id}: {message[:30]}...")

            if not self.douyin:
                logger.error("抖音窗口未初始化")
                return False

            self.douyin._ensure_foreground()
            time.sleep(1.0)

            if "点击搜索框" not in POSITIONS:
                logger.error("缺少必要点位：点击搜索框")
                return False

            logger.debug("步骤 1: 点击搜索框")
            self.douyin.Click(*POSITIONS["点击搜索框"])
            time.sleep(2.0)

            left, top, right, bottom = win32gui.GetWindowRect(self.douyin.hwnd)
            width = right - left
            height = bottom - top

            logger.debug("步骤 2: 清空搜索框内容")
            win32gui.SetForegroundWindow(self.douyin.hwnd)
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(0x41, 0, 0, 0)
            time.sleep(0.1)
            win32api.keybd_event(0x41, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.3)
            win32api.keybd_event(win32con.VK_DELETE, 0, 0, 0)
            win32api.keybd_event(win32con.VK_DELETE, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.5)

            logger.debug(f"步骤 3: 输入抖音 ID: {douyin_id}")
            SetClipboardText(douyin_id)
            time.sleep(0.3)

            win32gui.SetForegroundWindow(self.douyin.hwnd)
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(0x56, 0, 0, 0)
            time.sleep(0.1)
            win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(1.0)

            logger.debug("步骤 4: 执行搜索")
            if "点击搜索" in POSITIONS:
                self.douyin.Click(*POSITIONS["点击搜索"])
            else:
                SendKey(Keys.ENTER, self.douyin.hwnd)
            time.sleep(3.0)

            # 验证 1：搜索结果页面（识别"抖音号"）
            logger.debug("验证 1: 检测搜索结果页面")
            success, should_abort = self._wait_and_verify(
                verify_search_result,
                "点击用户头像",
                "搜索结果页面",
                abort_on_fail=True
            )
            if should_abort:
                logger.warning("搜索结果页面验证失败，返回监听状态")
                return False

            if "点击用户头像" not in POSITIONS:
                logger.error("缺少必要点位：点击用户头像")
                return False

            logger.debug("步骤 5: 点击用户头像")
            self.douyin.Click(*POSITIONS["点击用户头像"])
            time.sleep(2.0)

            # 确保窗口在前台
            self.douyin._ensure_foreground()
            time.sleep(0.5)

            # 验证 2：用户主页私信按钮（识别"私信"）并点击
            logger.debug("验证 2: 检测用户主页私信按钮")
            success = self.verify_and_click_user_homepage_private_button()
            if not success:
                logger.warning("用户主页私信按钮验证失败，返回监听状态")
                return False

            time.sleep(2.0)

            # 验证 3：消息输入框（识别"发送消息"）
            logger.debug("验证 3: 检测消息输入框")
            success = self.verify_and_click_message_input()
            if not success:
                logger.warning("消息输入框验证失败，返回监听状态")
                return False

            logger.debug("步骤 7: 消息输入框已点击")

            logger.debug(f"步骤 8: 输入消息：{message[:20]}...")
            SetClipboardText(message)
            time.sleep(0.3)

            win32gui.SetForegroundWindow(self.douyin.hwnd)
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(0x56, 0, 0, 0)
            time.sleep(0.1)
            win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.5)

            logger.debug("步骤 9: 发送消息")
            SendKey(Keys.ENTER, self.douyin.hwnd)
            time.sleep(1.0)

            logger.debug("步骤 10: 点击置顶用户返回列表")
            click_top_user(self.hwnd)
            time.sleep(1.0)

            logger.info(f"消息发送成功：{douyin_id}")
            return True

        except Exception as e:
            logger.error(f"发送消息失败：{e}")
            return False

    def execute_with_retry(self, msg: Dict, delivery_tag=None) -> bool:
        """
        带重试机制的执行消息发送

        Args:
            msg: 消息字典，包含 douyin_id, message 等字段
            delivery_tag: RabbitMQ 消息交付标签（可选）

        Returns:
            bool: 执行是否成功
        """
        max_retries = RETRY_CONFIG["max_retries"]
        retry_interval = RETRY_CONFIG["retry_delay"]
        retry_count = msg.get("retry_count", 0)

        try:
            success = self.send_message(msg["douyin_id"], msg["message"])

            if success:
                self.db_manager.log_message(
                    douyin_id=msg["douyin_id"],
                    message=msg["message"],
                    send_status=1,
                    retry_count=retry_count,
                )

                self.today_send_count += 1
                self.last_send_time = time.time()

                logger.info(
                    f"消息执行成功 (重试{retry_count}次): {msg['douyin_id']}"
                )
                
                if delivery_tag is not None and self.mq_manager:
                    self.mq_manager.ack_message(delivery_tag)
                
                return True
            else:
                raise Exception("发送失败")

        except Exception as e:
            retry_count += 1
            logger.warning(
                f"发送失败，重试第 {retry_count}/{max_retries} 次： "
                f"{msg['douyin_id']}, 错误：{e}"
            )

            if retry_count < max_retries:
                if delivery_tag is not None and self.mq_manager:
                    self.mq_manager.retry_message(msg, delivery_tag)
                time.sleep(retry_interval)
                return False
            else:
                self.db_manager.log_message(
                    douyin_id=msg["douyin_id"],
                    message=msg["message"],
                    send_status=0,
                    retry_count=retry_count,
                    error_message=f"重试{retry_count}次失败",
                )
                
                if delivery_tag is not None and self.mq_manager:
                    self.mq_manager.ack_message(delivery_tag)
                
                logger.error(f"消息执行失败 (已达最大重试次数): {msg['douyin_id']}")
                return False

    def listen_and_respond(self):
        """
        监听消息红点并自动回复（完整流程）
        流程：
        1. 检测红点并识别数字
        2. 点击红点进入对应用户的聊天
        3. 识别消息框中的消息
        4. 获取最新消息（数量=红点数字）
        5. 回复"你好"
        6. 返回列表

        Returns:
            bool: 是否检测到并处理了消息
        """
        try:
            if not self.douyin or not self.hwnd:
                return False

            logger.debug("=== 开始监听私信消息 ===")

            # 步骤 1: 点击私信按钮，打开私信窗口
            logger.debug("步骤 1: 点击私信按钮")
            click_relative(self.hwnd, 0.7389, 0.0267)
            time.sleep(1.5)

            # 步骤 2: 获取聊天窗口截图
            logger.debug("步骤 2: 获取聊天窗口截图")
            chat_img, chat_area_info = get_chat_window_area(self.hwnd)
            h_chat, w_chat = chat_img.shape[:2]

            # 步骤 3: 检测红点
            logger.debug("步骤 3: 检测红点")
            found, rx, ry, area = find_reddot_by_color(
                chat_img, target_bgr=(84, 45, 255), tolerance=20, min_area=30
            )

            if not found:
                logger.debug("未检测到消息红点")
                return False

            logger.info(f"检测到红点！像素面积：{area}")

            # 步骤 4: 识别红点中的数字
            logger.debug("步骤 4: OCR 识别红点数字")
            offset = 20
            x1_crop = max(0, int(rx * w_chat) - offset)
            y1_crop = max(0, int(ry * h_chat) - offset)
            x2_crop = min(w_chat, int(rx * w_chat) + offset)
            y2_crop = min(h_chat, int(ry * h_chat) + offset)
            reddot_crop = chat_img[y1_crop:y2_crop, x1_crop:x2_crop]
            expanded = expand_image_for_ocr(reddot_crop, target_size=200)

            white_image = keep_white_simple(expanded)
            number_text = recognize_number_with_ocr(white_image)
            numbers = re.findall(r"\d+", number_text)

            if not numbers:
                logger.debug("第一次未识别到数字，尝试膨胀处理")
                white_image_dilate = keep_white_simple(cv2.bitwise_not(expanded))
                number_text = recognize_number_with_ocr(white_image_dilate)
                numbers = re.findall(r"\d+", number_text)

            if not numbers:
                logger.warning("检测到红点但未识别到数字")
                return False

            unread_count = int(numbers[0])
            logger.info(f"✓ 识别到未读消息数量：{unread_count}条")

            # 步骤 5: 点击红点进入聊天
            logger.debug(f"步骤 5: 点击红点 (位置：{rx:.2f}, {ry:.2f})")
            abs_x = chat_area_info["x1"] + int(rx * w_chat)
            abs_y = chat_area_info["y1"] + int(ry * h_chat)
            logger.info(f"点击红点进入聊天：({abs_x}, {abs_y})")
            click_at(abs_x, abs_y)
            time.sleep(1.5)

            # 步骤 6: 识别消息框中的消息
            logger.debug("步骤 6: 识别消息框")
            messages = self.recognize_messages(unread_count)

            if messages:
                logger.info(f"✓ 成功识别 {len(messages)} 条消息")
                for i, msg in enumerate(messages, 1):
                    logger.info(f"  消息{i}: {msg[:30]}...")
            else:
                logger.warning("未识别到消息内容")

            # 步骤 7: 回复"你好"
            logger.debug("步骤 7: 回复消息")
            send_hello_message(self.hwnd)
            time.sleep(0.5)

            # 步骤 8: 点击置顶用户返回列表
            logger.debug("步骤 8: 点击置顶用户返回列表")
            click_top_user(self.hwnd)
            time.sleep(1.0)

            logger.info(f"✓ 监听完成：识别{unread_count}条消息，已回复")
            return True

        except Exception as e:
            logger.error(f"监听消息异常：{e}")
            import traceback

            logger.error(traceback.format_exc())
            return False

    def run(self):
        """运行主循环"""
        if not self.initialize():
            logger.error("初始化失败，程序退出")
            return

        self.running = True
        check_interval = LISTEN_CONFIG["check_interval"]

        logger.info("进入主循环，开始监听...")
        logger.info(f"监听间隔：{check_interval}秒")
        logger.info(f"发送间隔：{RATE_LIMIT_CONFIG['send_interval']}秒")
        logger.info(f"每日上限：{RATE_LIMIT_CONFIG['daily_limit']}条")
        logger.info(f"最大重试：{RETRY_CONFIG['max_retries']}次")

        try:
            while self.running:
                try:
                    if self.today_send_count >= RATE_LIMIT_CONFIG["daily_limit"]:
                        logger.warning(
                            f"已达到今日发送上限，停止发送 "
                            f"({self.today_send_count}/{RATE_LIMIT_CONFIG['daily_limit']})"
                        )
                        time.sleep(60)
                        self.today_send_count = self.db_manager.get_today_send_count()
                        continue

                    logger.debug("=== 开始新一轮监听 ===")

                    # 1. 监听消息红点并自动回复
                    logger.debug("步骤 1: 监听私信消息红点")
                    has_reddot = self.listen_and_respond()

                    if has_reddot:
                        logger.info("检测到新消息并已自动回复")

                    time.sleep(2)

                    # 2. 从 RabbitMQ 消费待执行消息
                    logger.debug("步骤 2: 从 RabbitMQ 消费待执行消息")
                    
                    if not self.check_rate_limit():
                        time.sleep(check_interval)
                        continue
                    
                    msg = self.mq_manager.consume_one(auto_ack=False)
                    
                    if msg:
                        logger.info(f"从队列获取到消息：{msg['douyin_id']}")
                        
                        if (
                            self.today_send_count
                            >= RATE_LIMIT_CONFIG["daily_limit"]
                        ):
                            logger.warning("已达到今日发送上限，消息将保留在队列中")
                            if self.mq_manager:
                                self.mq_manager.nack_message(
                                    msg.get('_delivery_tag', 0),
                                    requeue=False
                                )
                        else:
                            success = self.execute_with_retry(msg)
                            
                            if not success:
                                logger.warning("消息执行失败，等待下一轮")
                    else:
                        logger.debug("没有待执行消息，继续监听")
                    
                    time.sleep(check_interval)

                except KeyboardInterrupt:
                    logger.info("收到停止信号")
                    break
                except Exception as e:
                    logger.error(f"循环错误：{e}")
                    time.sleep(check_interval)

        finally:
            self.cleanup()
            logger.info("程序已退出")

    def stop(self):
        """停止运行"""
        logger.info("收到停止命令")
        self.running = False


def main():
    """主函数"""
    executor = AutoExecutor()

    try:
        executor.run()
    except KeyboardInterrupt:
        logger.info("用户中断")
        executor.stop()
    except Exception as e:
        logger.error(f"程序异常：{e}")
        executor.cleanup()


if __name__ == "__main__":
    main()
