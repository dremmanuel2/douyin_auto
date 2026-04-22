# Main Douyin automation class
import sys
import time
import os
import numpy as np
import win32gui
import win32con
import cv2
from .utils import (
    FindWindow,
    SetForegroundWindow,
    GetWindowRect,
    GetWindowSize,
    Click,
    DoubleClick,
    RightClick,
    SendKey,
    SendKeys,
    ScrollDown,
    ScrollUp,
    SetClipboardText,
    GetClipboardText,
    Keys,
)
from .elements import (
    VideoElement,
    CommentElement,
    UserElement,
    MessageElement,
    SessionElement,
)
from .errors import WindowNotFoundError, OperationFailedError
from .vision import (
    SmartLocator,
    compute_image_hash,
    compare_images,
    detect_message_area,
    find_element_by_template,
    detect_red_badge,
    verify_search_result,
    verify_private_message_button,
    verify_message_input,
)

# 导入用户校准的位置配置
try:
    from .positions import POSITIONS
except ImportError:
    POSITIONS = {}


class Douyin:
    """
    Douyin automation class for PC客户端.

    Usage:
        from douyin_auto import Douyin

        dy = Douyin()
        dy.NextVideo()     # Next video
        dy.Like()          # Like current video
        dy.SendComment('Great!')  # Send comment
    """

    # Window class name for Douyin
    WINDOW_CLASS_NAME = "Chrome_WidgetWin_1"
    WINDOW_TITLE = "抖音"

    # 支持的浏览器类名
    BROWSER_CLASSES = [
        "Chrome_WidgetWin_1",
        "Chrome_WidgetWin_0",
        "MSEdge_WidgetWin_0",
        "MSEdge_WidgetWin_1",
    ]

    # 标准窗口尺寸
    DEFAULT_WIDTH = 1080
    DEFAULT_HEIGHT = 900

    def __init__(self, hwnd=None):
        """
        Initialize Douyin automation.

        Args:
            hwnd: Window handle. If None, will search for Douyin window.
        """
        self._hwnd = hwnd
        self._window_width = 0
        self._window_height = 0
        self._nickname = ""

        self._smart_locator = None
        self._last_screenshot = None
        self._last_screenshot_hash = ""
        self._last_message_area_hash = ""
        self._listening = False
        self._message_callbacks = []

        if not self._hwnd:
            self._hwnd = self._find_window()

        if self._hwnd:
            self._update_window_size()
            self._smart_locator = SmartLocator(self._hwnd)
            self._capture_baseline()
            # First show the window (restore if minimized)
            win32gui.ShowWindow(self._hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)
            # Then try to bring to foreground
            try:
                SetForegroundWindow(self._hwnd)
            except Exception as e:
                print("Warning: SetForegroundWindow failed: {}".format(e))
                # Try alternative method
                try:
                    win32gui.SetWindowPos(
                        self._hwnd,
                        win32con.HWND_TOP,
                        0,
                        0,
                        0,
                        0,
                        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
                    )
                except:
                    pass
            time.sleep(0.2)
        else:
            raise WindowNotFoundError("Douyin window not found")

    @classmethod
    def open(cls, x=0, y=0, width=None, height=None):
        """
        查找抖音窗口并固定到指定大小和位置。

        Args:
            x: 窗口左上角 X 坐标（默认 0）
            y: 窗口左上角 Y 坐标（默认 0）
            width: 窗口宽度（默认 800）
            height: 窗口高度（默认 900）

        Returns:
            Douyin 实例

        Example:
            dy = Douyin.open()          # 窗口固定到 (0,0) 800x900
            dy = Douyin.open(x=100, y=50, width=960, height=1080)
        """
        w = width or cls.DEFAULT_WIDTH
        h = height or cls.DEFAULT_HEIGHT

        # 查找窗口
        hwnd = FindWindow(cls.WINDOW_CLASS_NAME, cls.WINDOW_TITLE)
        if not hwnd:
            hwnd = FindWindow(None, cls.WINDOW_TITLE)

        # 如果找不到，尝试查找第一个 Chrome_WidgetWin_1 窗口
        if not hwnd:
            hwnd = cls._find_first_browser_window()

        if not hwnd:
            raise WindowNotFoundError(
                "Douyin window not found, please open Douyin first"
            )

        # 固定窗口大小和位置
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.1)
        win32gui.SetWindowPos(
            hwnd, 0, x, y, w, h, win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW
        )
        time.sleep(0.3)
        SetForegroundWindow(hwnd)
        time.sleep(0.2)

        instance = cls(hwnd=hwnd)
        instance._update_window_size()
        return instance

    def _find_window(self):
        """Find Douyin window"""
        # 1. 尝试通过标题精确匹配
        hwnd = FindWindow(self.WINDOW_CLASS_NAME, self.WINDOW_TITLE)
        if hwnd:
            return hwnd

        # 2. 通过标题模糊匹配
        hwnd = FindWindow(None, self.WINDOW_TITLE)
        if hwnd:
            return hwnd

        # 3. 尝试支持的所有浏览器类名
        for class_name in self.BROWSER_CLASSES:
            hwnd = FindWindow(class_name, self.WINDOW_TITLE)
            if hwnd:
                return hwnd
            hwnd = FindWindow(class_name, None)
            if hwnd:
                # 检查标题是否包含"抖音"
                title = win32gui.GetWindowText(hwnd)
                if title and ("抖音" in title or "douyin" in title.lower()):
                    return hwnd

        # 4. 通过枚举所有浏览器窗口查找
        hwnd = self._find_first_browser_window()
        if hwnd:
            return hwnd

        # 5. 通过标题包含"抖音"查找
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

    @classmethod
    def _find_first_browser_window(cls):
        """查找第一个支持的浏览器窗口，优先选择接近默认尺寸的"""
        result = []

        def enum_callback(h, data):
            if win32gui.IsWindowVisible(h):
                classname = win32gui.GetClassName(h)
                if classname in cls.BROWSER_CLASSES:
                    title = win32gui.GetWindowText(h)
                    # 优先选择标题包含"抖音"的窗口
                    is_douyin = title and ("抖音" in title or "douyin" in title.lower())
                    rect = win32gui.GetWindowRect(h)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    data.append(
                        {
                            "hwnd": h,
                            "width": width,
                            "height": height,
                            "is_douyin": is_douyin,
                            "title": title,
                        }
                    )

        win32gui.EnumWindows(enum_callback, result)

        if not result:
            return None

        # 优先选择标题包含"抖音"的窗口
        douyin_windows = [w for w in result if w.get("is_douyin")]
        if douyin_windows:
            # 如果有多个抖音窗口，选择接近默认尺寸的
            target_w, target_h = cls.DEFAULT_WIDTH, cls.DEFAULT_HEIGHT
            douyin_windows.sort(
                key=lambda x: abs(x["width"] - target_w) + abs(x["height"] - target_h)
            )
            return douyin_windows[0]["hwnd"]

        # 如果没有抖音窗口，选择接近默认尺寸的窗口
        target_w, target_h = cls.DEFAULT_WIDTH, cls.DEFAULT_HEIGHT
        result.sort(
            key=lambda x: abs(x["width"] - target_w) + abs(x["height"] - target_h)
        )
        return result[0]["hwnd"]

    def _update_window_size(self):
        """Update window dimensions"""
        if self._hwnd:
            self._window_width, self._window_height = GetWindowSize(self._hwnd)

    def _ensure_foreground(self):
        """Ensure Douyin window is in foreground"""
        if self._hwnd:
            SetForegroundWindow(self._hwnd)
            time.sleep(0.1)

    def _get_absolute_x(self, relative_x):
        """Convert relative X (0-1) to absolute screen coordinate"""
        left, top, right, bottom = GetWindowRect(self._hwnd)
        return left + int(relative_x * self._window_width)

    def _get_absolute_y(self, relative_y):
        """Convert relative Y (0-1) to absolute screen coordinate"""
        left, top, right, bottom = GetWindowRect(self._hwnd)
        return top + int(relative_y * self._window_height)

    def _click_relative(self, rel_x, rel_y):
        """Click at relative position (0-1)"""
        abs_x = self._get_absolute_x(rel_x)
        abs_y = self._get_absolute_y(rel_y)
        Click(abs_x, abs_y, self._hwnd)

    # ==================== Window Control ====================

    @property
    def hwnd(self):
        """Get window handle"""
        return self._hwnd

    @property
    def width(self):
        """Get window width"""
        return self._window_width

    @property
    def height(self):
        """Get window height"""
        return self._window_height

    def Refresh(self):
        """Refresh window size and position"""
        self._update_window_size()

    def set_size(self, x=0, y=0, width=None, height=None):
        """
        将窗口固定到指定大小和位置。

        Args:
            x: 窗口左上角 X 坐标（默认 0）
            y: 窗口左上角 Y 坐标（默认 0）
            width: 窗口宽度（默认 800）
            height: 窗口高度（默认 900）

        Example:
            dy.set_size()                # 固定为 800x900 在 (0,0)
            dy.set_size(x=100, y=50, width=960, height=1080)
        """
        w = width or self.DEFAULT_WIDTH
        h = height or self.DEFAULT_HEIGHT
        win32gui.ShowWindow(self._hwnd, win32con.SW_RESTORE)
        time.sleep(0.1)
        win32gui.SetWindowPos(
            self._hwnd, 0, x, y, w, h, win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW
        )
        time.sleep(0.3)
        self._update_window_size()
        SetForegroundWindow(self._hwnd)
        print(
            "窗口已设置为: ({}, {}) {}x{}".format(
                x, y, self._window_width, self._window_height
            )
        )

    # ==================== Video Navigation ====================

    def NextVideo(self):
        """
        Go to next video.
        Douyin PC: Down arrow, J key, or swipe up.
        """
        self._ensure_foreground()
        SendKey(Keys.DOWN, self._hwnd)
        time.sleep(0.5)

    def PreviousVideo(self):
        """
        Go to previous video.
        Douyin PC: Up arrow, K key, or swipe down.
        """
        self._ensure_foreground()
        SendKey(Keys.UP, self._hwnd)
        time.sleep(0.5)

    def ScrollToTop(self):
        """Scroll to top (go to first video)"""
        self._ensure_foreground()
        SendKey(Keys.HOME, self._hwnd)
        time.sleep(0.5)

    def ScrollToBottom(self):
        """Scroll to bottom"""
        self._ensure_foreground()
        SendKey(Keys.END, self._hwnd)
        time.sleep(0.5)

    # ==================== Video Actions ====================

    def Like(self):
        """
        Like current video.
        Douyin PC: L key or click like button.
        """
        self._ensure_foreground()
        # Click the like button (校准位置: 0.9437, 0.4781)
        self._click_relative(0.9437, 0.4781)
        time.sleep(0.3)

    def Unlike(self):
        """Unlike current video (toggle like)"""
        self.Like()

    def Collect(self):
        """
        Collect/favorite current video.
        Douyin PC: F key or click collect button.
        """
        self._ensure_foreground()
        # Click the collect button (right side, approximately 94%, 65%)
        self._click_relative(0.94, 0.65)
        time.sleep(0.3)

    def Share(self):
        """
        Share current video.
        Douyin PC: R key or click share button.
        """
        self._ensure_foreground()
        # Click the share button (right side, approximately 94%, 78%)
        self._click_relative(0.94, 0.78)
        time.sleep(0.3)

    def Pause(self):
        """Pause video playback"""
        self._ensure_foreground()
        SendKey(Keys.SPACE, self._hwnd)
        time.sleep(0.2)

    def Play(self):
        """Play video (same as pause - toggle)"""
        self.Pause()

    # ==================== Comment Actions ====================

    def OpenComments(self):
        """
        Open comment section.
        Douyin PC: Click comment button or C key.
        """
        self._ensure_foreground()
        # Click the comment button (right side, approximately 94%, 52%)
        self._click_relative(0.94, 0.52)
        time.sleep(0.5)

    def CloseComments(self):
        """Close comment section"""
        self._ensure_foreground()
        SendKey(Keys.ESCAPE, self._hwnd)
        time.sleep(0.3)

    def SendComment(self, text):
        """
        Send a comment on current video.

        Args:
            text: Comment text
        """
        self._ensure_foreground()
        self.OpenComments()
        time.sleep(0.5)

        # Click on comment input area (bottom center)
        self._click_relative(0.50, 0.85)
        time.sleep(0.3)

        # Type comment using clipboard
        SetClipboardText(text)
        time.sleep(0.1)

        # Ctrl+V to paste
        win32gui.SetForegroundWindow(self._hwnd)
        import win32api

        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(0x56, 0, 0, 0)  # V key
        time.sleep(0.05)
        win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.2)

        # Press Enter to send
        SendKey(Keys.ENTER, self._hwnd)
        time.sleep(0.5)

    def GetComments(self, count=20):
        """
        Get comments from current video.
        Note: This is a placeholder - actual implementation requires
        OCR or UI element analysis.

        Args:
            count: Number of comments to retrieve

        Returns:
            List of CommentElement objects
        """
        # This would require OCR or more sophisticated UI parsing
        # For now, return empty list
        return []

    def LikeComment(self, index=0):
        """
        Like a comment by index (0 = first comment).

        Args:
            index: Comment index
        """
        self._ensure_foreground()
        self.OpenComments()
        time.sleep(0.5)

        # Scroll to load comments if needed
        ScrollDown(self._hwnd, 2)
        time.sleep(0.3)

        # Calculate position for comment (approximately)
        # Comments are typically on the left side of the comment panel
        comment_x = 0.15
        comment_y = 0.40 + (index * 0.08)

        self._click_relative(comment_x, min(comment_y, 0.85))
        time.sleep(0.2)

        # Look for like button in comment area
        # This is a simplified implementation
        self._click_relative(0.12, 0.42)
        time.sleep(0.3)

    # ==================== User Actions ====================

    def Follow(self):
        """
        Follow the current video's author.
        Usually done by clicking the author name/avatar.
        """
        self._ensure_foreground()
        # Click on author area (left side, approximately 5%, 50%)
        self._click_relative(0.05, 0.50)
        time.sleep(0.5)

    def Unfollow(self):
        """Unfollow (toggle follow)"""
        self.Follow()

    def ViewProfile(self):
        """
        View author's profile.
        """
        self._ensure_foreground()
        # Click on author name
        self._click_relative(0.05, 0.55)
        time.sleep(0.5)

    def GetUserProfile(self):
        """
        Get current video author's profile.
        Note: Placeholder - requires UI analysis or API.

        Returns:
            UserElement object
        """
        user = UserElement(self._hwnd)
        # Would need to extract from UI
        return user

    # ==================== Search ====================

    def Search(self, keyword):
        """
        Search for users, videos, or topics.

        Args:
            keyword: Search keyword
        """
        self._ensure_foreground()

        # 使用校准的位置：点击搜索框
        if "点击搜索框" in POSITIONS:
            x, y = POSITIONS["点击搜索框"]
            self._click_relative(x, y)
        else:
            # 默认位置
            self._click_relative(0.36, 0.04)
        time.sleep(0.5)

        # 输入搜索内容
        SetClipboardText(keyword)
        time.sleep(0.1)

        import win32api

        win32gui.SetForegroundWindow(self._hwnd)
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(0x56, 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.3)

        # 使用校准的位置：点击搜索按钮
        if "点击搜索" in POSITIONS:
            x, y = POSITIONS["点击搜索"]
            self._click_relative(x, y)
        else:
            SendKey(Keys.ENTER, self._hwnd)
        time.sleep(1.0)

    # ==================== Private Messages ====================

    def OpenMessages(self):
        """
        Open private messages through the top screen entry.
        """
        self._ensure_foreground()
        # 使用positions.txt中定义的屏幕上方私信入口位置
        if "屏幕上方的私信入口" in POSITIONS:
            x, y = POSITIONS["屏幕上方的私信入口"]
            self._click_relative(x, y)
        else:
            # 默认位置 (top right area)
            self._click_relative(0.95, 0.05)
        time.sleep(0.5)

    def OpenMessagesViaSearch(self, user_id):
        """
        Open private messages through the search result entry.

        Args:
            user_id: User ID to search for
        """
        self._ensure_foreground()

        # 1. 搜索用户
        self.Search(user_id)
        time.sleep(1.0)

        # 2. 点击用户头像
        self.ClickUserAvatar()
        time.sleep(1.0)

        # 3. 点击私信按钮
        self.ClickPrivateMessage()
        time.sleep(1.0)

    def ClickUserAvatar(self):
        """点击搜索结果中的用户头像"""
        self._ensure_foreground()
        if "点击用户头像" in POSITIONS:
            x, y = POSITIONS["点击用户头像"]
            self._click_relative(x, y)
        else:
            self._click_relative(0.50, 0.25)
        time.sleep(0.5)

    def ClickFollowInProfile(self):
        """点击个人资料页中的关注按钮"""
        self._ensure_foreground()
        if "点击头像内部的关注" in POSITIONS:
            x, y = POSITIONS["点击头像内部的关注"]
            self._click_relative(x, y)
        else:
            self._click_relative(0.50, 0.25)
        time.sleep(0.5)

    def ClickPrivateMessage(self):
        """点击个人资料页中的私信按钮"""
        self._ensure_foreground()
        if "点击私信" in POSITIONS:
            x, y = POSITIONS["点击私信"]
            self._click_relative(x, y)
        else:
            self._click_relative(0.50, 0.25)
        time.sleep(0.5)

    def ClickMessageInput(self):
        """点击发送消息框"""
        self._ensure_foreground()
        if "点击发送消息框" in POSITIONS:
            x, y = POSITIONS["点击发送消息框"]
            self._click_relative(x, y)
        else:
            self._click_relative(0.50, 0.85)
        time.sleep(0.3)

def _load_config(self):
        """加载配置文件"""
        import json
        config_path = os.path.join(os.path.dirname(__file__), "..", "app", "config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"interval": 1.0, "validation_repeat": 5}
    
    def _wait_and_verify(self, verify_func, screenshot_func, position_key, 
                         max_retries=None, interval=None, stage_name=""):
        """
        等待并验证页面状态
        
        Args:
            verify_func: 验证函数
            screenshot_func: 截图函数
            position_key: 位置配置键名
            max_retries: 最大重试次数
            interval: 重试间隔（秒）
            stage_name: 阶段名称（用于日志）
        
        Returns:
            success: bool
        """
        config = self._load_config()
        if max_retries is None:
            max_retries = config.get("validation_repeat", 5)
        if interval is None:
            interval = config.get("interval", 1.0)
        
        print("    正在验证{}...".format(stage_name))
        
        for i in range(max_retries):
            try:
                # 获取位置配置
                if position_key not in POSITIONS:
                    print("    警告：缺少位置配置 {}".format(position_key))
                    # 如果没有位置配置，使用默认等待
                    time.sleep(interval)
                    continue
                
                x, y = POSITIONS[position_key]
                left, top, right, bottom = GetWindowRect(self._hwnd)
                width = right - left
                height = bottom - top
                
                # 计算截图区域（头像区域，约 100x100 像素）
                screenshot_width = int(width * 0.15)
                screenshot_height = int(height * 0.15)
                x1 = int(left + x * width)
                y1 = int(top + y * height)
                x2 = min(x1 + screenshot_width, right)
                y2 = min(y1 + screenshot_height, bottom)
                
                # 调整截图区域确保合理大小
                if x2 - x1 < 50:
                    x2 = min(x1 + 150, right)
                if y2 - y1 < 50:
                    y2 = min(y1 + 150, bottom)
                
                # 截图
                from PIL import ImageGrab
                import numpy as np
                import cv2
                
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
    
    def SendMessage(self, user, text, follow_first=True):
        """
        搜索用户并发送私信的完整流程

        Args:
            user: 要搜索的用户名
            text: 要发送的消息内容
            follow_first: 是否先关注再发消息 (默认 True)
        """
        self._ensure_foreground()

        # 1. 搜索用户
        print("正在搜索用户：{}".format(user))
        self.Search(user)
        time.sleep(1.0)

        # 验证 1：搜索结果页面是否加载完成（识别"抖音号"）
        if not self._wait_and_verify(
            verify_search_result,
            self.TakeScreenshot,
            "点击用户头像",
            stage_name="搜索结果页面"
        ):
            print("警告：搜索结果页面验证未通过，继续执行...")

        # 2. 点击用户头像
        print("正在点击用户头像...")
        self.ClickUserAvatar()
        time.sleep(1.0)

        # 验证 2：私信按钮是否可见（识别"私信"）
        if not self._wait_and_verify(
            verify_private_message_button,
            self.TakeScreenshot,
            "点击私信",
            stage_name="私信按钮"
        ):
            print("警告：私信按钮验证未通过，继续执行...")

        # 3. 如果需要关注，先点击关注
        if follow_first:
            print("正在点击关注...")
            self.ClickFollowInProfile()
            time.sleep(1.0)

        # 4. 点击私信按钮
        print("正在点击私信按钮...")
        self.ClickPrivateMessage()
        time.sleep(1.0)

        # 验证 3：消息输入框是否可用（识别"发送消息"）
        if not self._wait_and_verify(
            verify_message_input,
            self.TakeScreenshot,
            "点击发送消息框",
            stage_name="消息输入框"
        ):
            print("警告：消息输入框验证未通过，继续执行...")

        # 5. 点击发送消息框
        print("正在点击发送消息框...")
        self.ClickMessageInput()
        time.sleep(0.5)

        # 6. 输入消息内容
        print("正在输入消息：{}".format(text))
        SetClipboardText(text)
        time.sleep(0.2)

        win32gui.SetForegroundWindow(self._hwnd)
        import win32api

        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(0x56, 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.3)

        # 7. 按回车发送
        print("正在发送消息...")
        SendKey(Keys.ENTER, self._hwnd)
        time.sleep(0.5)

        print("消息发送完成！")

    # ==================== Screenshot ====================

    def TakeScreenshot(self, filepath=None):
        """
        Take a screenshot of the Douyin window.

        Args:
            filepath: Output file path. If None, saves to desktop.
        """
        import os
        from PIL import Image

        left, top, right, bottom = GetWindowRect(self._hwnd)
        width = right - left
        height = bottom - top

        # 使用PIL截图（更稳定）
        import win32gui
        from PIL import ImageGrab

        bbox = (left, top, right, bottom)
        img = ImageGrab.grab(bbox=bbox)

        if filepath:
            img.save(filepath)
            return filepath
        else:
            # 转换为numpy数组返回
            import numpy as np

            img_np = np.array(img)
            if len(img_np.shape) == 3 and img_np.shape[2] == 4:
                img_np = img_np[:, :, :3]
            return img_np

    # ==================== Utilities ====================

    def Click(self, rel_x, rel_y):
        """
        Click at relative position (0-1).

        Args:
            rel_x: Relative X position (0-1)
            rel_y: Relative Y position (0-1)
        """
        self._ensure_foreground()
        self._click_relative(rel_x, rel_y)

    def DoubleClick(self, rel_x, rel_y):
        """
        Double click at relative position.

        Args:
            rel_x: Relative X position (0-1)
            rel_y: Relative Y position (0-1)
        """
        self._ensure_foreground()
        abs_x = self._get_absolute_x(rel_x)
        abs_y = self._get_absolute_y(rel_y)
        DoubleClick(abs_x, abs_y, self._hwnd)
        time.sleep(0.3)

    def RightClick(self, rel_x, rel_y):
        """
        Right click at relative position.

        Args:
            rel_x: Relative X position (0-1)
            rel_y: Relative Y position (0-1)
        """
        self._ensure_foreground()
        abs_x = self._get_absolute_x(rel_x)
        abs_y = self._get_absolute_y(rel_y)
        RightClick(abs_x, abs_y, self._hwnd)

    def PressKey(self, key_code):
        """
        Press a key by its virtual key code.

        Args:
            key_code: Virtual key code (use Keys class)
        """
        self._ensure_foreground()
        SendKey(key_code, self._hwnd)

    # ==================== 消息监听功能 ====================

    def _capture_baseline(self):
        """捕获基线截图用于消息变化检测"""
        self._last_screenshot = self.TakeScreenshot()
        if self._last_screenshot is not None and hasattr(
            self._last_screenshot, "shape"
        ):
            self._last_screenshot_hash = compute_image_hash(self._last_screenshot)
            msg_area = detect_message_area(self._last_screenshot, "left")
            self._last_message_area_hash = compute_image_hash(msg_area)

    def _capture_current_screenshot(self):
        """捕获当前截图"""
        screenshot = self.TakeScreenshot()
        if screenshot is not None and hasattr(screenshot, "shape"):
            return screenshot
        return None

    def _get_message_area_image(self):
        """获取消息区域图像"""
        current = self._capture_current_screenshot()
        if current is None or not hasattr(current, "shape"):
            return None
        return detect_message_area(current, "left")

    def CheckNewMessage(self):
        """
        检查是否有新消息（通过截图差异检测）

        Returns:
            has_new: bool - 是否有新消息
            diff_info: dict - 差异信息
        """
        self._ensure_foreground()
        time.sleep(0.1)

        current = self._capture_current_screenshot()
        if current is None:
            return False, {}

        current_hash = compute_image_hash(current)
        if current_hash != self._last_screenshot_hash:
            self._last_screenshot = current
            self._last_screenshot_hash = current_hash

            current_msg_area = detect_message_area(current, "left")
            current_msg_hash = compute_image_hash(current_msg_area)

            if current_msg_hash != self._last_message_area_hash:
                self._last_message_area_hash = current_msg_hash
                return True, {"type": "message_area_change"}

            return True, {"type": "screen_change"}

        return False, {}

    def CheckNewMessageByRedDot(self):
        """
        通过红点检测是否有新消息（检查消息图标区域）

        Returns:
            has_new: bool - 是否有新消息（红点）
        """
        self._ensure_foreground()
        time.sleep(0.1)

        left, top, right, bottom = GetWindowRect(self._hwnd)
        width = right - left
        height = bottom - top

        from PIL import Image, ImageGrab

        msg_icon_area = (
            left + int(width * 0.92),
            top + int(height * 0.02),
            left + int(width * 0.98),
            top + int(height * 0.08),
        )
        img = ImageGrab.grab(bbox=msg_icon_area)
        img_np = np.array(img)

        if img_np.size == 0:
            return False

        if len(img_np.shape) == 3 and img_np.shape[2] == 4:
            img_np = img_np[:, :, :3]

        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        has_badge, _, _ = detect_red_badge(img_bgr, min_area=30)
        return has_badge

    def StartListening(self, callback=None):
        """
        开始监听新消息

        Args:
            callback: 新消息回调函数，签名为 callback(has_new, diff_info)
        """
        self._listening = True
        if callback:
            self._message_callbacks.append(callback)
        self._capture_baseline()

    def StopListening(self):
        """停止监听新消息"""
        self._listening = False

    def GetNewMessage(self, timeout=10, check_interval=1.0):
        """
        等待并获取新消息

        Args:
            timeout: 超时时间（秒）
            check_interval: 检查间隔（秒）

        Returns:
            has_new: bool - 是否有新消息
            diff_info: dict - 差异信息
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            has_new, diff_info = self.CheckNewMessage()
            if has_new:
                for cb in self._message_callbacks:
                    try:
                        cb(has_new, diff_info)
                    except:
                        pass
                return has_new, diff_info
            time.sleep(check_interval)

        return False, {"type": "timeout"}

    def OnNewMessage(self, callback):
        """
        注册新消息回调

        Args:
            callback: 回调函数
        """
        if callback not in self._message_callbacks:
            self._message_callbacks.append(callback)

    # ==================== 私信消息处理 ====================

    def GetPrivateMessages(self, count=50):
        """
        获取当前会话的私信消息

        流程：
        1. 截图
        2. 检测消息框位置
        3. OCR提取消息文字
        4. 返回消息列表

        Args:
            count: 最大返回消息数量

        Returns:
            list: MessageElement列表
        """
        from .vision import detect_message_box, extract_messages_from_box

        self._ensure_foreground()
        time.sleep(0.1)

        screenshot = self.TakeScreenshot()
        if screenshot is None:
            return []

        box_info = detect_message_box(screenshot)
        box = box_info["box"]

        raw_messages = extract_messages_from_box(screenshot, box)

        messages = []
        for i, msg in enumerate(raw_messages[:count]):
            elem = MessageElement(self._hwnd)
            elem.content = msg["text"]
            elem.is_self = msg["is_self"]
            elem.id = str(i)
            messages.append(elem)

        return messages

    def GetPrivateMessagesByPosition(self, count=50):
        """
        使用已知位置获取私信消息（基于positions.txt）

        Args:
            count: 最大返回消息数量

        Returns:
            list: MessageElement列表
        """
        from .vision import extract_messages_from_box, get_message_box_by_position

        self._ensure_foreground()
        time.sleep(0.1)

        screenshot = self.TakeScreenshot()
        if screenshot is None:
            return []

        box = get_message_box_by_position()
        raw_messages = extract_messages_from_box(screenshot, box)

        messages = []
        for i, msg in enumerate(raw_messages[:count]):
            elem = MessageElement(self._hwnd)
            elem.content = msg["text"]
            elem.is_self = msg["is_self"]
            elem.id = str(i)
            messages.append(elem)

        return messages

    def GetSessionList(self):
        """
        获取私信会话列表

        返回结构：
        [
            {"name": "用户名", "unread": True/False, "last_msg": "最后消息", "rel_y": 0.1},
            ...
        ]

        Returns:
            list: 会话列表
        """
        from .vision import detect_red_badge

        self._ensure_foreground()
        time.sleep(0.1)

        left, top, right, bottom = GetWindowRect(self._hwnd)
        width = right - left
        height = bottom - top

        from PIL import Image, ImageGrab

        session_list_area = (
            left + int(width * 0.01),
            top + int(height * 0.08),
            left + int(width * 0.35),
            top + int(height * 0.85),
        )

        img = ImageGrab.grab(bbox=session_list_area)
        img_np = np.array(img)

        if img_np.size == 0:
            return []

        if len(img_np.shape) == 3 and img_np.shape[2] == 4:
            img_np = img_np[:, :, :3]

        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        has_badge, _, _ = detect_red_badge(img_bgr, min_area=20)

        sessions = []
        if has_badge:
            sessions.append(
                {"name": "有新消息", "unread": True, "last_msg": "", "rel_y": 0.1}
            )

        return sessions

    def ClickSession(self, rel_y):
        """
        点击会话列表中的指定会话

        Args:
            rel_y: 相对Y坐标 (0-1)
        """
        self._ensure_foreground()

        left, top, right, bottom = GetWindowRect(self._hwnd)
        width = right - left
        height = bottom - top

        x = int(left + width * 0.17)
        y = int(top + rel_y * height)

        Click(x, y)
        time.sleep(0.5)

    def OpenMessageSession(self, session_name):
        """
        打开指定会话

        Args:
            session_name: 会话名称/用户名
        """
        self._ensure_foreground()
        self.OpenMessages()
        time.sleep(0.5)

        sessions = self.GetSessionList()
        for i, session in enumerate(sessions):
            if session_name in session.get("name", ""):
                self.ClickSession(session["rel_y"])
                time.sleep(0.5)
                return True

        return False

    def GetAllNewMessage(self, max_count=10):
        """
        获取所有未读私信消息（参考wxauto的GetAllNewMessage）

        流程：
        1. 检查消息图标红点
        2. 进入私信列表
        3. 遍历未读会话获取消息
        4. 返回所有消息

        Args:
            max_count: 每个会话最多返回消息数

        Returns:
            dict: {username: [MessageElement列表], ...}
        """
        if not self.CheckNewMessageByRedDot():
            return {}

        self.OpenMessages()
        time.sleep(0.8)

        sessions = self.GetSessionList()

        all_messages = {}
        for session in sessions:
            if session.get("unread", False):
                username = session.get("name", "未知用户")
                self.ClickSession(session.get("rel_y", 0.1))
                time.sleep(0.5)

                messages = self.GetPrivateMessages(max_count)
                if messages:
                    all_messages[username] = messages

        return all_messages

    def SmartClick(self, element_name, retry=2):
        """
        使用智能定位点击元素（模板匹配 -> 颜色检测 -> 相对坐标fallback）

        Args:
            element_name: 元素名称（如 "like", "comment", "share"）
            retry: 重试次数

        Returns:
            success: bool
        """
        from .vision import SmartLocator

        if not self._smart_locator:
            self._smart_locator = SmartLocator(self._hwnd)

        element_map = {
            "like": ("like_button", (0.9437, 0.4781)),
            "comment": ("comment_button", (0.94, 0.52)),
            "share": ("share_button", (0.94, 0.78)),
            "collect": ("collect_button", (0.94, 0.65)),
            "search": ("search_button", (0.36, 0.04)),
        }

        if element_name not in element_map:
            element_name_key = element_name
            fallback_pos = None
        else:
            element_name_key, fallback_pos = element_map[element_name]

        for i in range(retry):
            success, rx, ry, method = self._smart_locator.locate(
                element_name_key, fallback_pos=fallback_pos
            )
            if success:
                abs_x = self._get_absolute_x(rx)
                abs_y = self._get_absolute_y(ry)
                Click(abs_x, abs_y)
                time.sleep(0.2)
                return True
            time.sleep(0.3)
        return False

    def LocateElement(self, element_name):
        """
        定位元素位置

        Args:
            element_name: 元素名称

        Returns:
            success: bool
            rel_x, rel_y: 相对坐标
            method: str - 使用的定位方法
        """
        from .vision import SmartLocator

        if not self._smart_locator:
            self._smart_locator = SmartLocator(self._hwnd)

        element_map = {
            "like": ("like_button", (0.9437, 0.4781)),
            "comment": ("comment_button", (0.94, 0.52)),
            "share": ("share_button", (0.94, 0.78)),
            "collect": ("collect_button", (0.94, 0.65)),
            "search": ("search_button", (0.36, 0.04)),
        }

        if element_name not in element_map:
            element_name_key = element_name
            fallback_pos = None
        else:
            element_name_key, fallback_pos = element_map[element_name]

        return self._smart_locator.locate(element_name_key, fallback_pos=fallback_pos)

    def __repr__(self):
        return "<Douyin: {}x{}>".format(self.width, self.height)
