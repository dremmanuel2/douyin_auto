"""抖音位置校准工具 - 交互式获取准确坐标"""

import win32gui
import win32api
import win32con
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from douyin_auto import Douyin


def get_window_info():
    """获取抖音窗口信息"""
    titles = ("抖音", "douyin")
    hwnd = win32gui.FindWindow("Chrome_WidgetWin_1", titles[0])
    if not hwnd:
        hwnd = win32gui.FindWindow(None, titles[0])

    if not hwnd:

        def enum_callback(h, l):
            if win32gui.IsWindowVisible(h):
                t = win32gui.GetWindowText(h)
                if t and any(title in t for title in titles):
                    l.append(h)

        windows = []
        win32gui.EnumWindows(enum_callback, windows)
        if windows:
            hwnd = windows[0]

    if hwnd:
        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top
        return hwnd, rect, width, height
    return None, None, None, None


def set_window_position(hwnd, x, y, width, height):
    """设置窗口位置和大小"""
    win32gui.SetWindowPos(
        hwnd, 0, x, y, width, height, win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW
    )


def get_mouse_pos():
    """获取当前鼠标位置"""
    return win32api.GetCursorPos()


def main():
    print("=" * 60)
    print("抖音位置校准工具")
    print("=" * 60)

    print("\n正在打开并固定抖音窗口...")
    try:
        dy = Douyin.open()
        hwnd = dy.hwnd
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width, height = dy.width, dy.height
        print(f"窗口已固定: ({left}, {top}) {width}x{height}")
    except Exception as e:
        print(f"\n连接失败: {e}")
        print("请先打开抖音精选电脑版")
        input("\n按回车键退出...")
        return

    print("\n" + "=" * 60)
    print("校准说明:")
    print("  1. 窗口已固定在左上角 (0, 0)，大小为 800x900")
    print("  2. 输入每个按钮的名称（支持中文，如: 点赞, 评论, 关注）")
    print("  3. 移动鼠标到目标位置，按回车获取坐标")
    print("  4. 输入 'done' 结束校准")
    print("=" * 60)

    # 加载已有点位，避免覆盖丢失
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "douyin_auto", "positions.txt"
    )
    results = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and ":" in line:
                        name, coords = line.split(":", 1)
                        name = name.strip().strip("'\"")
                        coords = coords.strip().strip("()")
                        rx, ry = map(float, coords.split(","))
                        results[name] = (rx, ry)
                if results:
                    print(f"\n已加载 {len(results)} 个已有点位:")
                    for n, (rx, ry) in sorted(results.items()):
                        print(f"  - {n}: ({rx:.4f}, {ry:.4f})")
        except Exception:
            pass

    print()

    while True:
        print("\n" + "-" * 40)

        # 输入按钮名称（支持中文）
        name = input(
            "请输入按钮名称 (如: 点赞, 评论按钮, 关注, 或 'done' 结束): "
        ).strip()

        if name.lower() == "done":
            break

        if not name:
            print("名称不能为空，请重新输入")
            continue

        # 检查名称是否重复
        if name in results:
            print(f"警告: '{name}' 已存在，将覆盖之前的数据")

        # 获取坐标
        print(f"\n  现在请移动鼠标到 [{name}] 按钮位置...")
        print("  移动到位后按回车获取坐标")

        input("  按回车键获取坐标...")

        x, y = get_mouse_pos()

        if left <= x <= right and top <= y <= bottom:
            rel_x = (x - left) / width if width > 0 else 0
            rel_y = (y - top) / height if height > 0 else 0
            results[name] = (rel_x, rel_y)
            print(f"\n  ✓ 已保存: {name} = ({rel_x:.4f}, {rel_y:.4f})")
            print(f"    屏幕坐标: ({x}, {y})")
        else:
            print(f"\n  ✗ 错误: 鼠标在窗口外 ({x}, {y})")
            print("    请将鼠标移到窗口内后重新输入名称")

    # 输出结果
    if not results:
        print("\n没有校准任何位置，退出")
        return

    print("\n" + "=" * 60)
    print("校准结果:")
    print("=" * 60)
    for name, (rx, ry) in results.items():
        print(f"  {name}: ({rx:.4f}, {ry:.4f})")

    # 保存到文件
    print("\n" + "=" * 60)
    save = input("是否保存到文件? (y/n): ").strip().lower()

    if save == "y":
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "douyin_auto", "positions.txt"
        )

        existing_positions = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and ":" in line:
                            name, coords = line.split(":", 1)
                            name = name.strip().strip("'\"")
                            coords = coords.strip().strip("()")
                            rx, ry = map(float, coords.split(","))
                            existing_positions[name] = (rx, ry)
            except Exception:
                pass

        all_positions = {**existing_positions, **results}

        with open(config_path, "w", encoding="utf-8") as f:
            f.write("# 抖音按钮位置配置文件（由校准工具自动生成）\n")
            f.write("# 窗口大小: 800x900\n\n")
            for name, (rx, ry) in all_positions.items():
                f.write(f"{name}: ({rx:.4f}, {ry:.4f})\n")
        print(f"配置已保存到: {config_path}")

        # 生成 Python 代码片段，方便复制使用
        print("\n" + "=" * 60)
        print("可复制使用的代码:")
        print("=" * 60)
        print("\n# 在 douyin.py 中引用:")
        print("from .positions import POSITIONS")
        print("\n# 使用示例:")
        for name in results.keys():
            print(f"# dy.Click(POSITIONS['{name}'][0], POSITIONS['{name}'][1])")

        print("\n" + "=" * 60)
        update = (
            input("是否用这些坐标更新 douyin.py 中的硬编码位置? (y/n): ")
            .strip()
            .lower()
        )

        if update == "y":
            # 读取当前 douyin.py
            douyin_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "douyin_auto", "douyin.py"
            )
            with open(douyin_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 定义一些常见的替换映射（用户可能定义的名称）
            replacements = {
                "like_btn": ("_click_relative(0.94, 0.38)", "Like()"),
                "comment_btn": ("_click_relative(0.94, 0.52)", "OpenComments()"),
                "collect_btn": ("_click_relative(0.94, 0.65)", "Collect()"),
                "share_btn": ("_click_relative(0.94, 0.78)", "Share()"),
                "comment_input": ("_click_relative(0.50, 0.85)", "SendComment()"),
                "author_area": ("_click_relative(0.05, 0.50)", "Follow()"),
                "search_btn": ("_click_relative(0.36, 0.04)", "Search()"),
            }

            for name, (old_pattern, method_name) in replacements.items():
                if name in results:
                    rx, ry = results[name]
                    new_pattern = f"_click_relative({rx:.2f}, {ry:.2f})"
                    if old_pattern in content:
                        content = content.replace(old_pattern, new_pattern)
                        print(f"已更新 {method_name}: {old_pattern} -> {new_pattern}")

            # 保存更新后的 douyin.py
            with open(douyin_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"\ndouyin.py 已更新!")

    print("\n校准完成！")
    input("\n按回车键退出...")


if __name__ == "__main__":
    main()
