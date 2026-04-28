# -*- coding: utf-8 -*-
"""
抖音私信命令上传工具 - 图形界面版本
用于将私信命令发布到 RabbitMQ 队列
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from douyin_auto.mq_utils import RabbitMQManager
from douyin_auto.mq_config import RATE_LIMIT_CONFIG, LOG_CONFIG
import logging


def setup_logger():
    """配置日志记录器"""
    log_dir = LOG_CONFIG.get("log_dir", "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    today = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f"upload_{today}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("UploadCommand")


logger = setup_logger()


class UploadCommandGUI:
    """命令上传图形界面"""

    def __init__(self, root):
        """
        初始化图形界面

        Args:
            root: Tkinter 根窗口
        """
        self.root = root
        self.root.title("抖音私信命令上传工具")
        self.root.geometry("500x450")
        self.root.resizable(False, False)

        self.mq_manager = None
        self._init_mq()

        self._create_widgets()
        self._update_status()

    def _init_mq(self):
        """初始化 RabbitMQ 连接"""
        try:
            self.mq_manager = RabbitMQManager()
            if self.mq_manager.connect():
                if self.mq_manager.initialize_queues():
                    logger.info("RabbitMQ 初始化成功")
                else:
                    logger.error("RabbitMQ 队列初始化失败")
                    messagebox.showerror("错误", "RabbitMQ 队列初始化失败，请检查配置")
            else:
                logger.error("RabbitMQ 连接失败")
                messagebox.showerror("错误", "RabbitMQ 连接失败，请检查配置")
        except Exception as e:
            logger.error(f"RabbitMQ 初始化异常：{e}")
            messagebox.showerror("错误", f"RabbitMQ 连接失败：{str(e)}")

    def _create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        title_label = ttk.Label(
            main_frame,
            text="抖音私信命令上传工具",
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        ttk.Label(main_frame, text="目标抖音 ID：").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.douyin_id_var = tk.StringVar()
        self.douyin_id_entry = ttk.Entry(
            main_frame,
            textvariable=self.douyin_id_var,
            width=40,
        )
        self.douyin_id_entry.grid(row=1, column=1, pady=5, padx=(10, 0))

        ttk.Label(main_frame, text="消息内容：").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        self.message_text = tk.Text(main_frame, width=40, height=6)
        self.message_text.grid(row=2, column=1, pady=5, padx=(10, 0))

        ttk.Label(main_frame, text="发送方式：").grid(
            row=3, column=0, sticky=tk.W, pady=5
        )
        self.send_method_var = tk.StringVar(value="queue")
        method_frame = ttk.Frame(main_frame)
        method_frame.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        ttk.Radiobutton(
            method_frame,
            text="加入队列 (推荐)",
            variable=self.send_method_var,
            value="queue",
        ).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Radiobutton(
            method_frame,
            text="立即发送",
            variable=self.send_method_var,
            value="immediate",
        ).pack(side=tk.LEFT)

        status_frame = ttk.LabelFrame(main_frame, text="状态信息", padding="10")
        status_frame.grid(row=4, column=0, columnspan=2, pady=15, sticky=(tk.W, tk.E))

        self.status_label = ttk.Label(status_frame, text="状态：就绪")
        self.status_label.grid(row=0, column=0, sticky=tk.W)

        self.count_label = ttk.Label(
            status_frame,
            text=f"今日已发送：0/{RATE_LIMIT_CONFIG['daily_limit']}",
        )
        self.count_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        self.queue_label = ttk.Label(status_frame, text="队列待执行：0")
        self.queue_label.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        self.upload_button = ttk.Button(
            button_frame, text="上传命令", command=self._upload_command, width=15
        )
        self.upload_button.grid(row=0, column=0, padx=(0, 10))

        ttk.Button(
            button_frame, text="取消", command=self._close_window, width=15
        ).grid(row=0, column=1)

        ttk.Button(
            button_frame, text="刷新状态", command=self._update_status, width=15
        ).grid(row=0, column=2, padx=(10, 0))

        for child in main_frame.winfo_children():
            child.grid_configure(padx=5, pady=5)

    def _validate_douyin_id(self, douyin_id):
        """
        验证抖音 ID 格式

        Args:
            douyin_id: 抖音 ID 字符串

        Returns:
            bool: 是否有效
        """
        douyin_id = douyin_id.strip()
        if not douyin_id:
            return False
        if len(douyin_id) < 6 or len(douyin_id) > 20:
            return False
        if not re.match(r"^[a-zA-Z0-9]+$", douyin_id):
            return False
        return True

    def _upload_command(self):
        """上传命令到数据库"""
        douyin_id = self.douyin_id_var.get().strip()
        message = self.message_text.get("1.0", tk.END).strip()

        if not self._validate_douyin_id(douyin_id):
            messagebox.showwarning(
                "警告",
                "抖音 ID 格式不正确\n\n"
                "要求：\n"
                "- 长度 6-20 个字符\n"
                "- 只能包含字母和数字",
            )
            logger.warning(f"抖音 ID 格式验证失败：{douyin_id}")
            return

        if not message:
            messagebox.showwarning("警告", "消息内容不能为空")
            logger.warning("消息内容为空")
            return

        if len(message) > 500:
            messagebox.showwarning("警告", "消息内容不能超过 500 字")
            logger.warning(f"消息内容过长：{len(message)}字")
            return

        send_method = self.send_method_var.get()

        try:
            if not self.mq_manager or not self.mq_manager.check_connection():
                logger.error("RabbitMQ 连接失效")
                messagebox.showerror("错误", "RabbitMQ 连接失效，请重启程序")
                return

            if send_method == "immediate":
                today_count = self._get_today_count()
                if today_count >= RATE_LIMIT_CONFIG["daily_limit"]:
                    messagebox.showwarning(
                        "警告",
                        f"已达到今日发送上限：{today_count}/{RATE_LIMIT_CONFIG['daily_limit']}\n"
                        f"建议：加入队列，稍后自动发送",
                    )
                    logger.warning(f"达到今日发送上限：{today_count}")
                    return

            success = self.mq_manager.publish_message(douyin_id, message)

            if success:
                logger.info(f"命令发布成功：抖音 ID={douyin_id}")

                messagebox.showinfo(
                    "成功",
                    f"✓ 命令已成功发布到 RabbitMQ\n\n"
                    f"抖音 ID: {douyin_id}\n"
                    f"消息内容：{message[:50]}{'...' if len(message) > 50 else ''}\n"
                    f"发布时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                )

                self.douyin_id_var.set("")
                self.message_text.delete("1.0", tk.END)

                self._update_status()
            else:
                logger.error("命令发布失败")
                messagebox.showerror("错误", "命令发布失败，请重试")

        except Exception as e:
            logger.error(f"上传命令异常：{e}")
            messagebox.showerror("错误", f"上传失败：{str(e)}")

    def _update_status(self):
        """更新状态显示"""
        if not self.mq_manager or not self.mq_manager.check_connection():
            self.status_label.config(text="状态：RabbitMQ 未连接", foreground="red")
            return

        self.status_label.config(text="状态：就绪", foreground="green")

        try:
            today_count = self._get_today_count()
            queue_count = self.mq_manager.get_queue_count()

            self.count_label.config(
                text=f"今日已发送：{today_count}/{RATE_LIMIT_CONFIG['daily_limit']}"
            )
            self.queue_label.config(text=f"队列待执行：{queue_count}")

            if today_count >= RATE_LIMIT_CONFIG["daily_limit"]:
                self.count_label.config(foreground="red")
            else:
                self.count_label.config(foreground="black")

            logger.debug(f"状态更新：今日={today_count}, 队列={queue_count}")

        except Exception as e:
            logger.error(f"更新状态失败：{e}")

    def _get_today_count(self):
        """获取今日发送数量（从数据库日志表）"""
        try:
            from douyin_auto.db_utils import MySQLDBManager
            from douyin_auto.db_config import MYSQL_DB_CONFIG
            
            db_manager = MySQLDBManager()
            if db_manager.connect():
                count = db_manager.get_today_send_count()
                db_manager.disconnect()
                return count
        except Exception as e:
            logger.debug(f"获取今日发送数量失败：{e}")
        return 0

    def _close_window(self):
        """关闭窗口"""
        if self.mq_manager:
            self.mq_manager.disconnect()
        self.root.destroy()


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("启动抖音私信命令上传工具")
    logger.info("=" * 50)

    root = tk.Tk()

    try:
        app = UploadCommandGUI(root)
        root.mainloop()
    except Exception as e:
        logger.error(f"程序异常：{e}")
        messagebox.showerror("错误", f"程序异常：{str(e)}")
    finally:
        logger.info("程序退出")


if __name__ == "__main__":
    main()
