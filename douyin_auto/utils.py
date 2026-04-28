# Utility functions for douyin-auto
import win32gui
import win32con
import win32api
import win32clipboard
import time


def FindWindow(class_name=None, window_name=None):
    """
    Find a window by class name and/or window name.
    Returns window handle (hwnd) or 0 if not found.
    """
    if isinstance(window_name, str):
        window_names = [window_name]
    else:
        window_names = window_name or []

    for name in window_names:
        hwnd = win32gui.FindWindow(class_name, name)
        if hwnd:
            return hwnd

    for name in window_names:

        def enum_callback(h, l):
            if win32gui.IsWindowVisible(h):
                t = win32gui.GetWindowText(h)
                if t and (name in t or t in name):
                    l.append(h)

        windows = []
        win32gui.EnumWindows(enum_callback, windows)
        if windows:
            return windows[0]
    return 0


def SetForegroundWindow(hwnd):
    """Bring window to foreground"""
    if hwnd:
        try:
            # Use SW_SHOW instead of SW_RESTORE to avoid window minimizing issues
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        except:
            pass
        try:
            # SetWindowPos doesn't have the foreground restriction that SetForegroundWindow has
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOP,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
            )
        except Exception as e:
            print("SetWindowPos warning: %s" % e)


def GetWindowRect(hwnd):
    """Get window rectangle (left, top, right, bottom)"""
    return win32gui.GetWindowRect(hwnd)


def GetWindowSize(hwnd):
    """Get window size (width, height)"""
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return right - left, bottom - top


def Click(x, y, hwnd=None):
    """Simulate mouse click at screen coordinates"""
    # x, y are screen coordinates, no conversion needed when hwnd is provided
    # hwnd parameter is kept for backward compatibility but is not used for coordinate conversion

    # Move mouse and click (SetCursorPos uses screen coordinates)
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def DoubleClick(x, y, hwnd=None):
    """Simulate mouse double click at screen coordinates"""
    # x, y are screen coordinates, hwnd is not used for coordinate conversion
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def RightClick(x, y, hwnd=None):
    """Simulate right mouse click at screen coordinates"""
    # x, y are screen coordinates, hwnd is not used for coordinate conversion
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)


def SendKey(key_code, hwnd=None):
    """Send a key press event"""
    if hwnd:
        win32gui.SetForegroundWindow(hwnd)

    win32api.keybd_event(key_code, 0, 0, 0)
    time.sleep(0.05)
    win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)


def SendKeys(keys, hwnd=None):
    """
    Send multiple keys. keys can be:
    - a single key code
    - a string (will be typed using clipboard)
    - a list of key codes
    """
    if hwnd:
        win32gui.SetForegroundWindow(hwnd)

    if isinstance(keys, str):
        # Use clipboard to send string
        SetClipboardText(keys)
        # Ctrl+V to paste
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(ord("V"), 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(ord("V"), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    elif isinstance(keys, list):
        for key in keys:
            SendKey(key)
    else:
        SendKey(keys)


def SetClipboardText(text):
    """Set clipboard text"""
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()


def GetClipboardText():
    """Get clipboard text"""
    win32clipboard.OpenClipboard()
    try:
        return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
    except:
        return ""
    finally:
        win32clipboard.CloseClipboard()


def ScrollDown(hwnd=None, amount=3):
    """Simulate mouse scroll down"""
    for _ in range(amount):
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120, 0)
        time.sleep(0.1)


def ScrollUp(hwnd=None, amount=3):
    """Simulate mouse scroll up"""
    for _ in range(amount):
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120, 0)
        time.sleep(0.1)


# Key codes for Douyin
class Keys:
    """Virtual key codes"""

    UP = 0x26  # Up arrow
    DOWN = 0x28  # Down arrow
    LEFT = 0x25  # Left arrow
    RIGHT = 0x27  # Right arrow
    SPACE = 0x20  # Space
    ENTER = 0x0D  # Enter
    ESCAPE = 0x1B  # Escape
    L = 0x4C  # L - like
    C = 0x43  # C - comment
    F = 0x46  # F - favorite/collect
    R = 0x52  # R - share
    J = 0x4A  # J - down (alternate)
    K = 0x4B  # K - up (alternate)
    S = 0x53  # S - search
    T = 0x54  # T - following
    HOME = 0x24  # Home
    END = 0x23  # End
