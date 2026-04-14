# douyin-auto

抖音 PC 客户端自动化控制库 (Douyin PC Automation Library)

### 基于 Python 的抖音自动化控制

通过 Python 代码控制 Windows 抖音客户端，实现自动化操作。

## 环境

| 环境 | 版本 |
| :--: | :--: |
| OS | Windows 10/11 |
| Python | >= 3.8 |
| 抖音 | 抖音精选电脑版 |

## 项目结构

```
wxauto/
├── douyin_auto/              # 核心库
│   ├── __init__.py
│   ├── douyin.py             # 主类
│   ├── elements.py           # 元素类
│   ├── errors.py             # 自定义异常
│   ├── positions.py           # 校准点位配置
│   ├── test_basic.py         # 基础测试
│   └── utils.py              # 工具函数
├── scripts/                   # 脚本工具
│   ├── __init__.py
│   ├── calibrate_position.py  # 位置校准工具
│   ├── run_automation.py      # 自动化运行器
│   ├── send_message.py        # 批量发送私信工具
│   ├── window_controller.py   # 窗口控制工具
│   └── config.json            # 配置文件
└── README.md
```

## 安装

```bash
pip install pywin32 Pillow
```

或从源码安装：

```bash
cd douyin_auto
pip install -e .
```

## 快速开始

```python
from douyin_auto import Douyin

# 方式一：查找窗口并固定大小（推荐）
dy = Douyin.open()                          # 窗口固定到 (0,0) 1080x900
dy = Douyin.open(x=100, y=50, width=960, height=1080)  # 自定义

# 方式二：仅查找窗口（不改变大小）
dy = Douyin()
dy.set_size()                                # 后续可调用 set_size() 固定大小


# 视频操作
dy.NextVideo()      # 下一个视频
dy.PreviousVideo()  # 上一个视频
dy.Like()           # 点赞
dy.Unlike()         # 取消点赞
dy.Collect()        # 收藏
dy.Share()          # 分享
dy.Pause()          # 暂停视频
dy.Play()           # 播放视频
dy.ScrollToTop()    # 滚动到顶部
dy.ScrollToBottom() # 滚动到底部

# 评论操作
dy.SendComment('写的真好！')  # 发送评论
dy.OpenComments()            # 打开评论
dy.CloseComments()           # 关闭评论
dy.GetComments(count=20)     # 获取评论列表（占位符）
dy.LikeComment(index=0)      # 点赞指定评论

# 用户操作
dy.Follow()      # 关注作者
dy.Unfollow()    # 取消关注
dy.ViewProfile() # 查看资料
dy.GetUserProfile() # 获取用户资料

# 搜索与消息
dy.Search('关键词')           # 搜索
dy.SendMessage('用户名', '你好')  # 发送私信
dy.OpenMessages()              # 打开私信列表

# 截图
dy.TakeScreenshoat()           # 截图
```

## 脚本工具

### 位置校准

```bash
python scripts/calibrate_position.py
```

将抖音窗口设置为 1080x900 大小，然后交互式校准各按钮位置。

### 自动化运行器

```bash
python scripts/run_automation.py
```

支持：
- 按点位名称排序执行所有校准点位
- 自定义选择点位顺序执行
- 自定义间隔时间和重复次数

### 批量发送私信

```bash
python scripts/send_message.py
```

从 user_list.txt 读取用户名列表，批量发送私信。

### 窗口控制工具

```bash
python scripts/window_controller.py
```

快速测试窗口控制功能，如查找窗口、调整大小等。

## 注意事项

1. 所有操作需要抖音窗口在前台
2. 抖音使用 CEF 渲染，UIAutomation 无法访问内部元素，所有操作基于相对坐标模拟
3. 建议使用相对坐标 (0-1) 以适配不同窗口大小
4. 首次使用需运行 `calibrate_position.py` 校准点位
5. 不同抖音客户端版本的按钮位置可能不同，需重新校准

## 免责声明

代码仅供学习交流，请勿用于商业或非法用途。