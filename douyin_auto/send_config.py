# -*- coding: utf-8 -*-
"""
发送私信流程的时间间隔配置
可以根据需要调整这些参数
"""

# 搜索用户流程时间配置
SEARCH_CONFIG = {
    # 点击搜索框后等待时间（秒）
    "click_search_box_delay": 2.0,
    # 清空搜索框后等待时间（秒）
    "clear_search_delay": 0.5,
    # 粘贴抖音 ID 后等待时间（秒）
    "paste_id_delay": 1.0,
    # 点击搜索按钮后等待时间（秒）
    "click_search_delay": 3.0,
    # 点击用户头像后等待时间（秒）
    "click_avatar_delay": 5.0,
    # 点击私信按钮后等待时间（秒）
    "click_message_btn_delay": 2.0,
    # 点击消息输入框后等待时间（秒）
    "click_input_box_delay": 1.0,
    # 粘贴消息内容后等待时间（秒）
    "paste_message_delay": 0.5,
    # 发送消息后等待时间（秒）
    "send_message_delay": 1.0,
}

# 总体配置
GENERAL_CONFIG = {
    # 确保窗口在前台的等待时间（秒）
    "ensure_foreground_delay": 1.0,
    # 每个步骤之间的基础等待时间（秒）
    "base_delay": 0.5,
}

# 频率控制配置（来自 db_config.py）
RATE_LIMIT_CONFIG = {
    "send_interval": 30,  # 每条消息间隔 30 秒
    "daily_limit": 100,  # 每日发送上限 100 条
}

# 重试配置（来自 db_config.py）
RETRY_CONFIG = {
    "max_retries": 3,  # 最大重试次数
    "retry_interval": 3,  # 重试间隔 3 秒（已增加）
}

# 监听配置（来自 db_config.py）
LISTEN_CONFIG = {
    "check_interval": 5,  # 监听循环间隔 5 秒
}
