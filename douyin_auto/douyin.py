# Main Douyin automation class
import sys
import time
import win32gui
import win32con
from .utils import (
    FindWindow, SetForegroundWindow, GetWindowRect, GetWindowSize,
    Click, DoubleClick, RightClick, SendKey, SendKeys, ScrollDown, ScrollUp,
    SetClipboardText, GetClipboardText, Keys
)
from .elements import (
    VideoElement, CommentElement, UserElement, MessageElement, SessionElement
)
from .errors import WindowNotFoundError, OperationFailedError

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
    WINDOW_CLASS_NAME = 'Chrome_WidgetWin_1'
    WINDOW_TITLE = '抖音'

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
        self._nickname = ''

        if not self._hwnd:
            self._hwnd = self._find_window()

        if self._hwnd:
            self._update_window_size()
            # First show the window (restore if minimized)
            win32gui.ShowWindow(self._hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)
            # Then try to bring to foreground
            try:
                SetForegroundWindow(self._hwnd)
            except Exception as e:
                print(f'Warning: SetForegroundWindow failed: {e}')
                # Try alternative method
                try:
                    win32gui.SetWindowPos(self._hwnd, win32con.HWND_TOP, 0, 0, 0, 0,
                                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                except:
                    pass
            time.sleep(0.2)
        else:
            raise WindowNotFoundError('Douyin window not found')

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

        if not hwnd:
            raise WindowNotFoundError('Douyin window not found, please open Douyin first')

        # 固定窗口大小和位置
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.1)
        win32gui.SetWindowPos(hwnd, 0, x, y, w, h,
                              win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW)
        time.sleep(0.3)
        SetForegroundWindow(hwnd)
        time.sleep(0.2)

        instance = cls(hwnd=hwnd)
        instance._update_window_size()
        return instance

    def _find_window(self):
        """Find Douyin window"""
        hwnd = FindWindow(self.WINDOW_CLASS_NAME, self.WINDOW_TITLE)
        if hwnd:
            return hwnd

        # Try partial match
        hwnd = FindWindow(None, self.WINDOW_TITLE)
        if hwnd:
            return hwnd

        return 0

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
        win32gui.SetWindowPos(self._hwnd, 0, x, y, w, h,
                              win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW)
        time.sleep(0.3)
        self._update_window_size()
        SetForegroundWindow(self._hwnd)
        print(f'窗口已设置为: ({x}, {y}) {self._window_width}x{self._window_height}')

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
        if '点击搜索框' in POSITIONS:
            x, y = POSITIONS['点击搜索框']
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
        if '点击搜索' in POSITIONS:
            x, y = POSITIONS['点击搜索']
            self._click_relative(x, y)
        else:
            SendKey(Keys.ENTER, self._hwnd)
        time.sleep(1.0)

    # ==================== Private Messages ====================

    def OpenMessages(self):
        """
        Open private messages.
        """
        self._ensure_foreground()
        # Click on message icon (usually top right area)
        self._click_relative(0.95, 0.05)
        time.sleep(0.5)

    def ClickUserAvatar(self):
        """点击搜索结果中的用户头像"""
        self._ensure_foreground()
        if '点击用户头像' in POSITIONS:
            x, y = POSITIONS['点击用户头像']
            self._click_relative(x, y)
        else:
            self._click_relative(0.50, 0.25)
        time.sleep(0.5)

    def ClickFollowInProfile(self):
        """点击个人资料页中的关注按钮"""
        self._ensure_foreground()
        if '点击头像内部的关注' in POSITIONS:
            x, y = POSITIONS['点击头像内部的关注']
            self._click_relative(x, y)
        else:
            self._click_relative(0.50, 0.25)
        time.sleep(0.5)

    def ClickPrivateMessage(self):
        """点击个人资料页中的私信按钮"""
        self._ensure_foreground()
        if '点击私信' in POSITIONS:
            x, y = POSITIONS['点击私信']
            self._click_relative(x, y)
        else:
            self._click_relative(0.50, 0.25)
        time.sleep(0.5)

    def ClickMessageInput(self):
        """点击发送消息框"""
        self._ensure_foreground()
        if '点击发送消息框' in POSITIONS:
            x, y = POSITIONS['点击发送消息框']
            self._click_relative(x, y)
        else:
            self._click_relative(0.50, 0.85)
        time.sleep(0.3)

    def SendMessage(self, user, text, follow_first=True):
        """
        搜索用户并发送私信的完整流程

        Args:
            user: 要搜索的用户名
            text: 要发送的消息内容
            follow_first: 是否先关注再发消息 (默认True)
        """
        self._ensure_foreground()

        # 1. 搜索用户
        print(f"正在搜索用户: {user}")
        self.Search(user)
        time.sleep(1.0)

        # 2. 点击用户头像
        print("正在点击用户头像...")
        self.ClickUserAvatar()
        time.sleep(1.0)

        # 3. 如果需要关注，先点击关注
        if follow_first:
            print("正在点击关注...")
            self.ClickFollowInProfile()
            time.sleep(1.0)

        # 4. 点击私信按钮
        print("正在点击私信按钮...")
        self.ClickPrivateMessage()
        time.sleep(1.0)

        # 5. 点击发送消息框
        print("正在点击发送消息框...")
        self.ClickMessageInput()
        time.sleep(0.5)

        # 6. 输入消息内容
        print(f"正在输入消息: {text}")
        SetClipboardText(text)
        time.sleep(0.2)

        win32gui.SetForegroundWindow(self._hwnd)
        import win32api
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(0x56, 0, 0, 0)
        time.sleep(0.1)
        win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.3)

        # 7. 按回车发送
        print("正在发送消息...")
        SendKey(Keys.ENTER, self._hwnd)
        time.sleep(0.5)

        print(f"消息发送完成！")

    # ==================== Screenshot ====================

    def TakeScreenshot(self, filepath=None):
        """
        Take a screenshot of the Douyin window.

        Args:
            filepath: Output file path. If None, saves to desktop.
        """
        import os
        if not filepath:
            filepath = os.path.join(os.path.expanduser('~'), 'Desktop', 'douyin_screenshot.png')

        left, top, right, bottom = GetWindowRect(self._hwnd)
        width = right - left
        height = bottom - top

        import win32gui
        import win32ui
        hwndDC = win32gui.GetWindowDC(self._hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(bitmap)
        saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

        bitmap.SaveBitmapFile(saveDC, filepath)

        win32gui.DeleteObject(bitmap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(self._hwnd, hwndDC)

        return filepath

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

    def __repr__(self):
        return f'<Douyin: {self.width}x{self.height}>'
