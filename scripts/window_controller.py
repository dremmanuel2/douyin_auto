"""窗口控制工具 - 打开窗口、固定位置大小、截图"""
import os
import sys
import time
import win32gui
import win32con
import win32ui

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from douyin_auto.utils import FindWindow, SetForegroundWindow, GetWindowRect, GetWindowSize


def set_window_pos(hwnd, x, y, width, height):
    """设置窗口位置和大小"""
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    time.sleep(0.1)
    win32gui.SetWindowPos(hwnd, 0, x, y, width, height,
                          win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW)
    time.sleep(0.3)


def take_screenshot(hwnd, filepath=None):
    """对窗口进行截图"""
    if not filepath:
        filepath = os.path.join(os.path.expanduser('~'), 'Desktop', 'window_screenshot.png')

    left, top, right, bottom = GetWindowRect(hwnd)
    width = right - left
    height = bottom - top

    hwndDC = win32gui.GetWindowDC(hwnd)
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
    win32gui.ReleaseDC(hwnd, hwndDC)

    return filepath


def find_window_by_name(window_name):
    """根据窗口名称查找窗口"""
    hwnd = FindWindow(None, window_name)
    if hwnd:
        return hwnd

    # 枚举所有窗口进行模糊匹配
    def enum_callback(h, l):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if t and window_name in t:
                l.append((h, t))
    windows = []
    win32gui.EnumWindows(enum_callback, windows)
    return windows


def main():
    print("=" * 60)
    print("窗口控制工具")
    print("=" * 60)

    # 输入窗口信息
    print("\n请选择操作:")
    print("  1. 打开并控制抖音窗口")
    print("  2. 控制其他窗口")

    choice = input("\n请输入选项 (1/2): ").strip()

    hwnd = None

    if choice == '1':
        # 打开抖音窗口
        try:
            from douyin_auto import Douyin
            dy = Douyin.open()
            hwnd = dy.hwnd
            print(f"\n已打开抖音窗口: {dy.width}x{dy.height}")
        except Exception as e:
            print(f"\n连接失败: {e}")
            print("请先打开抖音精选电脑版")
            input("\n按回车键退出...")
            return

    elif choice == '2':
        # 查找其他窗口
        window_name = input("\n请输入窗口名称 (支持模糊匹配): ").strip()
        if not window_name:
            print("窗口名称不能为空")
            input("\n按回车键退出...")
            return

        results = find_window_by_name(window_name)
        if not results:
            print(f"未找到包含 '{window_name}' 的窗口")
            input("\n按回车键退出...")
            return
        elif len(results) == 1:
            hwnd = results[0][0]
            print(f"\n找到窗口: {results[0][1]}")
        else:
            print(f"\n找到 {len(results)} 个匹配的窗口:")
            for i, (h, title) in enumerate(results, 1):
                print(f"  {i}. {title}")
            idx = input("\n请选择窗口编号: ").strip()
            try:
                idx = int(idx) - 1
                if 0 <= idx < len(results):
                    hwnd = results[idx][0]
                    print(f"\n已选择: {results[idx][1]}")
                else:
                    print("无效的选择")
                    return
            except ValueError:
                print("无效输入")
                return
    else:
        print("无效选项")
        return

    # 获取当前窗口信息
    left, top, right, bottom = GetWindowRect(hwnd)
    width, height = GetWindowSize(hwnd)
    title = win32gui.GetWindowText(hwnd)

    print(f"\n当前窗口信息:")
    print(f"  标题: {title}")
    print(f"  位置: ({left}, {top})")
    print(f"  大小: {width}x{height}")

    # 设置位置和大小
    print("\n" + "-" * 40)
    print("设置窗口位置和大小:")

    try:
        x = int(input(f"  X坐标 [默认 {left}]: ").strip() or left)
        y = int(input(f"  Y坐标 [默认 {top}]: ").strip() or top)
        w = int(input(f"  宽度 [默认 {width}]: ").strip() or width)
        h = int(input(f"  高度 [默认 {height}]: ").strip() or height)
    except ValueError:
        print("输入无效，使用默认值")
        x, y, w, h = left, top, width, height

    set_window_pos(hwnd, x, y, w, h)
    SetForegroundWindow(hwnd)

    # 验证设置
    time.sleep(0.5)
    left, top, right, bottom = GetWindowRect(hwnd)
    width, height = GetWindowSize(hwnd)
    print(f"\n窗口已固定:")
    print(f"  位置: ({left}, {top})")
    print(f"  大小: {width}x{height}")

    # 截图
    print("\n" + "-" * 40)
    screenshot = input("是否截图? (y/n) [默认 y]: ").strip().lower() or 'y'

    if screenshot == 'y':
        default_path = os.path.join(os.path.expanduser('~'), 'Desktop', f'screenshot_{int(time.time())}.png')
        filepath = input(f"截图保存路径 [默认 {default_path}]: ").strip() or default_path
        try:
            result = take_screenshot(hwnd, filepath)
            print(f"\n截图已保存: {result}")
        except Exception as e:
            print(f"\n截图失败: {e}")

    print("\n操作完成！")
    input("\n按回车键退出...")


if __name__ == '__main__':
    main()
