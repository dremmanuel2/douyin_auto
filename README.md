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
douyinauto/
├── douyin_auto/              # 核心库
│   ├── __init__.py           # 包入口
│   ├── douyin.py             # 主类 Douyin
│   ├── elements.py           # 元素类定义
│   ├── errors.py             # 自定义异常
│   ├── positions.py          # 校准点位配置
│   ├── utils.py              # 工具函数
│   ├── vision.py             # 视觉识别模块
│   ├── test_basic.py         # 基础测试
│   └── templates/            # 按钮模板图片
├── scripts/                   # 脚本工具
│   ├── calibrate_position.py # 位置校准工具
│   ├── run_automation.py     # 自动化运行器
│   ├── send_message.py       # 批量发送私信工具
│   ├── window_controller.py  # 窗口控制工具
│   ├── listen_messages.py    # 私信监听工具
│   ├── test_message_detection.py # 消息检测测试
│   └── config.json           # 配置文件
├── screenshots/              # 截图输出目录
└── README.md
```

## 安装

```bash
pip install pywin32 Pillow opencv-python numpy
```

可选 OCR 依赖（文字识别）:

```bash
# 方案1: RapidOCR (推荐)
pip install rapidocr

# 方案2: cnocr
pip install cnocr

# 方案3: pytesseract (需要安装 Tesseract-OCR)
pip install pytesseract
```

或从源码安装:

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
dy.NextVideo()       # 下一个视频
dy.PreviousVideo()   # 上一个视频
dy.Like()            # 点赞
dy.Unlike()          # 取消点赞
dy.Collect()         # 收藏
dy.Share()           # 分享
dy.Pause()           # 暂停视频
dy.Play()            # 播放视频
dy.ScrollToTop()     # 滚动到顶部
dy.ScrollToBottom()  # 滚动到底部

# 评论操作
dy.SendComment('写的真好！')  # 发送评论
dy.OpenComments()            # 打开评论
dy.CloseComments()           # 关闭评论
dy.GetComments(count=20)     # 获取评论列表
dy.LikeComment(index=0)      # 点赞指定评论

# 用户操作
dy.Follow()         # 关注作者
dy.Unfollow()       # 取消关注
dy.ViewProfile()   # 查看资料
dy.GetUserProfile() # 获取用户资料

# 搜索与消息
dy.Search('关键词')           # 搜索
dy.SendMessage('用户名', '你好')  # 发送私信
dy.OpenMessages()              # 打开私信列表

# 私信消息处理（OCR+颜色检测）
dy.GetPrivateMessages(count=50)      # 获取当前会话私信消息
dy.GetPrivateMessagesByPosition()    # 使用已知位置获取私信
dy.GetSessionList()                  # 获取私信会话列表
dy.ClickSession(rel_y)               # 点击指定会话
dy.OpenMessageSession('用户名')       # 打开指定用户的私信会话
dy.GetAllNewMessage()                # 获取所有未读私信

# 截图
dy.TakeScreenshot()            # 截图

# 智能定位（CV方法）
dy.SmartClick('like')          # 智能点击点赞按钮
dy.LocateElement('comment')    # 定位评论按钮位置

# 消息监听
dy.CheckNewMessage()           # 检查是否有新消息（截图差异检测）
dy.CheckNewMessageByRedDot()   # 通过红点检测是否有新消息
dy.StartListening(callback)    # 开始监听新消息
dy.GetNewMessage(timeout=10)   # 等待获取新消息
dy.OnNewMessage(callback)      # 注册新消息回调
```

## 视觉识别模块 (vision.py)

提供多种计算机视觉功能：

### OCR 文字识别

```python
from douyin_auto.vision import recognize_text

results = recognize_text(image, lang="cn")
# 返回: [{"text": "文字", "bbox": [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]}, ...]
```

### 模板匹配

```python
from douyin_auto.vision import find_element_by_template

found, rel_x, rel_y, info = find_element_by_template(
    image, template_path, threshold=0.7
)
```

### 消息框检测

```python
from douyin_auto.vision import detect_message_box, extract_messages_from_box

# 检测消息气泡框
result = detect_message_box(image, debug=True)
# 返回: {"box": (x1,y1,x2,y2), "bubbles": [...], "debug_image": ...}

# 提取消息内容
messages = extract_messages_from_box(image, box, debug=True)
# 返回: [{"text": "内容", "is_self": False, "sender": "对方"}, ...]
```

### 智能定位器

```python
from douyin_auto.vision import SmartLocator

locator = SmartLocator(hwnd)
success, rx, ry, method = locator.locate("like_button")
locator.locate_click("like_button")
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

### 私信监听

```bash
python scripts/listen_messages.py
```

实时监听私信消息，支持：
- 打开私信弹窗
- 检测左侧用户区域红点
- OCR 识别未读数量
- 点击红点打开会话

## 元素类

```python
from douyin_auto.elements import (
    VideoElement,      # 视频元素
    CommentElement,   # 评论元素
    UserElement,      # 用户元素
    MessageElement,   # 私信消息元素
    SessionElement,   # 会话元素
)
```

## 注意事项

1. 所有操作需要抖音窗口在前台
2. 抖音使用 CEF 渲染，UIAutomation 无法访问内部元素
3. 推荐使用智能定位功能 `SmartClick()`，采用三层定位策略：
   - 模板匹配：使用 `templates/` 目录下的按钮截图
   - 颜色检测：基于按钮颜色特征定位
   - 相对坐标 fallback：使用校准的相对坐标
4. 消息监听使用截图差异检测，参考 wxauto 的 RuntimeId 思路
5. 首次使用需运行 `calibrate_position.py` 校准点位
6. 不同抖音客户端版本的按钮位置可能不同，需重新校准

## 许可证

MIT License

## 免责声明

代码仅供学习交流，请勿用于商业或非法用途。
