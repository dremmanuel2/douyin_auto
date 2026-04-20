# 抖音私信自动化系统 - 完整使用指南

## 🚀 快速开始

### 1. 上传命令（图形界面）
```bash
# 双击运行
bin\启动上传工具.bat

# 或命令行
python app\upload_command_gui.py
```

### 2. 自动执行
```bash
# 双击运行
bin\启动自动执行.bat

# 或命令行
python app\auto_executor.py
```

### 3. 测试数据库
```bash
python app\test_database.py
```

---

## 📋 系统功能

### 功能一：数据库消息队列
- ✅ 图形化上传发送命令
- ✅ 按时间顺序执行（从早到晚）
- ✅ 频率控制（30 秒/条）
- ✅ 每日上限（100 条/天）
- ✅ 重试机制（最多 3 次）
- ✅ 完整的日志记录

### 功能二：私信监听回复
- ✅ 自动检测消息红点
- ✅ OCR 识别未读消息数量
- ✅ 点击用户进入聊天
- ✅ 识别消息内容
- ✅ 自动回复"你好"
- ✅ 点击置顶用户返回列表

---

## ⚙️ 系统配置

### 数据库配置
文件：`douyin_auto/db_config.py`

```python
MYSQL_DB_CONFIG = {
    "user": 'root',
    "password": 'chatbi123',
    "host": "8.136.195.32",
    "port": 3306,
    "db_name": 'DY_database',
}
```

### 频率控制
- 发送间隔：30 秒/条
- 每日上限：100 条/天
- 监听间隔：5 秒
- 重试次数：3 次

### 发送流程时间（已调慢）
| 步骤 | 等待时间 |
|------|---------|
| 点击搜索框 | 2.0 秒 |
| 清空搜索框 | 0.5 秒 |
| 输入抖音 ID | 1.0 秒 |
| 执行搜索 | 3.0 秒 |
| 点击用户头像 | 2.0 秒 |
| 点击私信按钮 | 2.0 秒 |
| 点击消息输入框 | 1.0 秒 |
| 输入消息内容 | 0.5 秒 |
| 发送消息 | 1.0 秒 |
| 点击置顶用户返回 | 1.0 秒 |
| **总计** | **约 15 秒/条** |

---

## 📁 项目结构

```
douyinauto/
├── app/                              # 应用程序文件夹
│   ├── upload_command_gui.py         # 图形化上传工具
│   ├── auto_executor.py              # 自动化执行程序
│   ├── test_database.py              # 数据库测试
│   ├── send_message.py               # 私信发送工具
│   ├── listen_messages.py            # 消息监听工具
│   ├── calibrate_position.py         # 点位校准工具
│   └── README.md                     # app 说明
│
├── douyin_auto/                      # 核心库
│   ├── db_config.py                  # 数据库配置
│   ├── db_utils.py                   # 数据库工具
│   ├── douyin.py                     # 抖音自动化
│   ├── positions.py                  # UI 点位
│   ├── utils.py                      # 工具函数
│   └── ...
│
├── logs/                             # 日志目录
│   ├── executor_YYYYMMDD.log         # 执行日志
│   ├── upload_YYYYMMDD.log           # 上传日志
│   └── error_YYYYMMDD.log            # 错误日志
│
├── bin/                              # 启动脚本文件夹
│   ├── 启动上传工具.bat              # 快速启动上传
│   └── 启动自动执行.bat              # 快速启动执行
├── requirements.txt                  # Python 依赖
└── README.md                         # 本文档
```

---

## 🎯 使用流程

### 完整工作流程

```
步骤 1: 上传命令
  └─► 运行"启动上传工具.bat"
  └─► 输入抖音 ID 和消息
  └─► 点击"上传命令"
  └─► 数据写入 message_queue 表 ✓

步骤 2: 启动自动执行
  └─► 打开抖音 PC 客户端
  └─► 运行"启动自动执行.bat"
  └─► 程序自动执行 ✓

步骤 3: 查看结果
  └─► 查看 logs/ 目录的日志
  └─► 查看状态面板
```

### 自动执行流程

```
主循环（每 5 秒）：
│
├─► 监听私信红点
│   └─► 检测到红点？
│       ├─ 是 → 识别数字 → 点击进入 → 识别消息 → 回复"你好" → 返回
│       └─ 否 → 继续
│
├─► 查询数据库队列
│   └─► 有待执行消息？
│       ├─ 是 → 按时间排序 → 检查频率 → 执行发送 → 记录日志 → 删除
│       └─ 否 → 继续监听
│
└─► 等待 5 秒，进入下一轮
```

---

## 📊 数据库表

### message_queue - 消息队列
```sql
CREATE TABLE message_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    douyin_id VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TINYINT DEFAULT 0,
    retry_count TINYINT DEFAULT 0
);
```

### message_logs - 发送日志
```sql
CREATE TABLE message_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    douyin_id VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    send_status TINYINT DEFAULT 0,
    retry_count TINYINT DEFAULT 0,
    error_message VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔧 点位校准

### 必要点位
以下点位必须校准才能正常工作：

1. **点击搜索框** - 搜索用户
2. **点击用户头像** - 进入用户主页
3. **点击头像内的私信** - 打开私信
4. **点击发送消息框** - 输入消息
5. **私信聊天框左侧用户区域置顶用户** - 返回列表

### 校准方法
```bash
python app\calibrate_position.py
```

---

## 📝 日志示例

### 上传命令日志
```
2026-04-20 15:30:45 - UploadCommand - INFO - 启动抖音私信命令上传工具
2026-04-20 15:30:50 - UploadCommand - INFO - 数据库初始化成功
2026-04-20 15:31:00 - UploadCommand - INFO - 命令上传成功：ID=1
```

### 自动执行日志
```
2026-04-20 15:35:00 - AutoExecutor - INFO - 启动抖音私信自动化执行程序
2026-04-20 15:35:01 - AutoExecutor - INFO - 数据库初始化成功
2026-04-20 15:35:02 - AutoExecutor - INFO - 抖音窗口已打开：1080x900
2026-04-20 15:35:05 - AutoExecutor - DEBUG - === 开始监听私信消息 ===
2026-04-20 15:35:06 - AutoExecutor - INFO - ✓ 识别到未读消息数量：3 条
2026-04-20 15:35:08 - AutoExecutor - INFO - ✓ 成功识别 3 条消息
2026-04-20 15:35:09 - AutoExecutor - INFO - 自动回复消息：你好
2026-04-20 15:35:10 - AutoExecutor - INFO - ✓ 监听完成
2026-04-20 15:35:15 - AutoExecutor - INFO - 查询到 2 条待执行消息
2026-04-20 15:35:16 - AutoExecutor - INFO - 正在发送消息给 86759655452: 你好...
2026-04-20 15:35:31 - AutoExecutor - INFO - 消息发送成功
```

---

## ⚠️ 注意事项

### 1. 抖音窗口
- 运行自动执行时必须打开抖音 PC 客户端
- 窗口保持在前景，不要最小化
- 窗口尺寸建议：1080x900

### 2. 频率控制
- 不要修改为更激进的数值
- 抖音风控较严，建议保守设置
- 如遇封号风险，增大发送间隔

### 3. 点位校准
- 定期检查和校准点位
- 抖音更新后需重新校准
- 确保坐标准确

### 4. 日志管理
- 定期清理 logs 目录
- 建议保留最近 30 天日志
- 重要日志及时备份

### 5. 数据库备份
- 定期备份 message_logs 表
- 可用于数据分析和审计
- 建议每周备份一次

---

## 🔍 故障排除

### 问题 1：数据库连接失败
**解决方法：**
- 检查网络连接
- 确认数据库配置正确
- 测试能否访问 8.136.195.32:3306

### 问题 2：缺少必要点位
**解决方法：**
```bash
python app\calibrate_position.py
```
校准所有必要点位

### 问题 3：图形界面启动失败
**解决方法：**
- 错误"unknown option -font"已修复
- 如仍有问题，检查 Python 版本
- 确保安装了 tkinter

### 问题 4：发送失败
**解决方法：**
- 查看 logs/error_*.log 错误日志
- 确认抖音窗口已打开
- 检查点位是否准确
- 增大发送时间间隔

### 问题 5：识别不到红点
**解决方法：**
- 检查私信窗口是否打开
- 调整红点检测参数（tolerance, min_area）
- 确保抖音界面布局未变化

---

## 📦 依赖安装

### 安装依赖
```bash
pip install -r requirements.txt
```

### requirements.txt
```txt
pywin32
Pillow
opencv-python
numpy
PyMySQL>=1.0.0
rapidocr  # OCR 识别
```

---

## 🎯 应用场景

### 1. 自动客服
- 监听用户私信
- 自动回复常见问题
- 7x24 小时在线

### 2. 批量通知
- 上传发送队列
- 自动执行发送
- 控制发送频率

### 3. 消息分析
- 识别消息内容
- 分析用户需求
- 数据统计

### 4. 智能对话
- 获取最新消息
- 对接 AI 接口
- 智能回复

---

## 📖 快速参考

### 启动程序
| 程序 | 命令 |
|------|------|
| 上传工具 | `bin\启动上传工具.bat` |
| 自动执行 | `bin\启动自动执行.bat` |
| 测试数据库 | `python app\test_database.py` |
| 点位校准 | `python app\calibrate_position.py` |

### 配置位置
| 配置 | 文件 |
|------|------|
| 数据库 | `douyin_auto/db_config.py` |
| 发送速度 | `app/auto_executor.py` |
| 点位 | `douyin_auto/positions.py` |

### 日志位置
| 日志 | 文件 |
|------|------|
| 上传日志 | `logs/upload_YYYYMMDD.log` |
| 执行日志 | `logs/executor_YYYYMMDD.log` |
| 错误日志 | `logs/error_YYYYMMDD.log` |

---

## 📞 技术支持

### 查看日志
遇到问题先查看日志文件：
```bash
# 查看最新执行日志
type logs\executor_*.log

# 查看错误日志
type logs\error_*.log
```

### 测试数据库
```bash
python app\test_database.py
```

### 检查配置
```bash
python test_send_config.py
```

---

**版本：** v2.0  
**更新日期：** 2026-04-20  
**环境：** D:\anaconda3\envs\eav  
**数据库：** MySQL 8.136.195.32:3306/DY_database