# app 文件夹说明

## 目录结构

```
app/
├── __init__.py                # Python 包初始化文件
├── upload_command_gui.py      # 图形化命令上传工具
├── auto_executor.py           # 自动化执行程序
├── test_database.py           # 数据库测试脚本
├── send_message.py            # 私信发送工具（原有）
├── listen_messages.py         # 消息监听工具（原有）
├── calibrate_position.py      # 点位校准工具（原有）
└── test_message_detection.py  # 消息检测测试（原有）
```

## 文件分类

### 数据库队列系统（新增核心功能）
- **upload_command_gui.py** - 图形化命令上传工具
- **auto_executor.py** - 自动化执行程序
- **test_database.py** - 数据库测试脚本

### 抖音自动化功能（原有功能）
- **send_message.py** - 私信发送工具
- **listen_messages.py** - 消息监听工具
- **calibrate_position.py** - 点位校准工具
- **test_message_detection.py** - 消息检测测试

## 快速启动

### 上传命令
```bash
python app\upload_command_gui.py
```

### 自动执行
```bash
python app\auto_executor.py
```

### 测试数据库
```bash
python app\test_database.py
```

## 使用说明

### 1. 上传命令到数据库
运行 `upload_command_gui.py`，通过图形界面输入：
- 目标抖音 ID
- 消息内容
- 选择发送方式

### 2. 启动自动执行
运行 `auto_executor.py`，程序会：
- 自动检查数据库队列
- 按时间顺序执行发送任务
- 控制发送频率
- 记录发送日志

### 3. 测试数据库连接
运行 `test_database.py`，验证：
- 数据库连接
- 表结构
- 基本操作

## 注意事项

1. 运行自动执行程序前，确保抖音 PC 客户端已打开
2. 确保已校准必要的 UI 点位
3. 确保能访问 MySQL 数据库 (8.136.195.32:3306)
4. 日志文件保存在 `logs/` 目录

## 相关文档

- 快速开始：`QUICKSTART.md`
- 详细文档：`README_DB_QUEUE.md`
- 系统架构：`ARCHITECTURE.md`
- 项目总结：`DELIVERY_SUMMARY.md`