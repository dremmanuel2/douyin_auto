# RabbitMQ 迁移说明

## 📋 概述

本项目已从 MySQL 队列迁移到 RabbitMQ 消息队列系统。

### 架构变化

**迁移前：**
- 队列存储：MySQL `message_queue` 表
- 日志存储：MySQL `message_logs` 表
- 生产者：轮询数据库插入消息
- 消费者：轮询数据库查询待执行消息

**迁移后：**
- 队列存储：RabbitMQ（持久化队列 + 死信队列）
- 日志存储：MySQL `message_logs` 表（保留）
- 生产者：发布消息到 RabbitMQ
- 消费者：从 RabbitMQ 消费消息

---

## 🔧 配置说明

### RabbitMQ 配置

配置文件：`douyin_auto/mq_config.py`

```python
MQ_CONFIG = {
    "host": "8.136.195.32",      # RabbitMQ 服务器地址
    "port": 5672,                 # AMQP 端口
    "user": "admin",              # 用户名
    "password": "FBREkFRESAGCffA", # 密码
    "virtual_host": "/",          # 虚拟主机
    "queue_name": "douyin_message_queue",      # 主队列
    "dlx_queue_name": "douyin_message_dlx",    # 死信队列
    "exchange_name": "douyin_message_exchange",         # 主交换机
    "dlx_exchange_name": "douyin_message_dlx_exchange", # 死信交换机
}
```

### 重试配置

```python
RETRY_CONFIG = {
    "max_retries": 3,        # 最大重试次数
    "retry_delay": 2,        # 重试间隔（秒）
    "dlx_ttl": 5000,         # 死信队列 TTL（毫秒）
}
```

---

## 📦 依赖安装

```bash
pip install -r requirements.txt
```

新增依赖：
- `pika==1.3.2` - RabbitMQ Python 客户端

---

## 🚀 使用方法

### 1. 运行测试脚本

首先测试 RabbitMQ 连接和配置：

```bash
python app/test_rabbitmq.py
```

测试内容：
- ✓ RabbitMQ 连接测试
- ✓ 队列初始化测试
- ✓ 消息发布测试
- ✓ 消息消费测试
- ✓ 死信队列测试
- ✓ 队列数量查询

### 2. 启动自动执行程序

```bash
python app/auto_executor.py
```

程序将：
1. 连接数据库（用于日志记录）
2. 连接 RabbitMQ（用于队列）
3. 初始化队列（主队列 + 死信队列）
4. 打开抖音窗口
5. 进入主循环：
   - 监听私信红点并自动回复
   - 从 RabbitMQ 消费消息并执行
   - 失败消息自动进入死信队列重试

### 3. 上传命令（GUI）

```bash
python app/upload_command_gui.py
```

图形界面用于：
- 输入目标抖音 ID 和消息内容
- 选择发送方式（加入队列/立即发送）
- 查看队列状态和今日发送数量

---

## 🔄 消息流程

### 正常流程

```
生产者 (upload_command_gui.py)
    ↓ 发布消息
RabbitMQ 主队列 (douyin_message_queue)
    ↓ 消费消息
消费者 (auto_executor.py)
    ↓ 执行成功
记录日志到 MySQL (message_logs)
    ↓ 确认消息
RabbitMQ 删除消息
```

### 失败重试流程

```
消费者执行失败
    ↓ 重试次数 < 3
发送到死信队列 (douyin_message_dlx)
    ↓ 等待 5 秒 (TTL)
重新发布到主队列
    ↓ 重试
消费者再次执行
```

### 达到最大重试次数

```
消费者执行失败
    ↓ 重试次数 >= 3
记录失败日志到 MySQL
    ↓ 确认消息
RabbitMQ 删除消息
```

---

## 📊 队列设计

### 主队列 (douyin_message_queue)

- **类型**：持久化队列
- **特性**：
  - `durable=True` - 队列持久化
  - `x-dead-letter-exchange` - 死信交换机
  - `x-dead-letter-routing-key` - 死信路由键

### 死信队列 (douyin_message_dlx)

- **类型**：持久化队列
- **特性**：
  - `durable=True` - 队列持久化
  - `x-message-ttl=5000` - 消息 TTL 5 秒
  - 失败消息延迟 5 秒后重新处理

### 交换机

- **主交换机**：`douyin_message_exchange` (direct 类型)
- **死信交换机**：`douyin_message_dlx_exchange` (direct 类型)

---

## 🔍 消息格式

```json
{
    "douyin_id": "用户抖音 ID",
    "message": "消息内容",
    "retry_count": 0,
    "created_at": null
}
```

字段说明：
- `douyin_id` - 目标用户抖音 ID
- `message` - 要发送的消息内容
- `retry_count` - 当前重试次数
- `created_at` - 创建时间（保留字段）

---

## ⚙️ 数据库表（保留）

### message_logs

仅用于记录发送日志，不再存储队列消息。

```sql
CREATE TABLE message_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    douyin_id VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    send_status TINYINT DEFAULT 0,  -- 0-失败，1-成功
    retry_count TINYINT DEFAULT 0,
    error_message VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🛠️ 常见问题

### Q1: RabbitMQ 连接失败

**检查项：**
1. 网络是否通畅：`telnet 8.136.195.32 5672`
2. 用户名密码是否正确
3. RabbitMQ 服务是否运行
4. 防火墙是否开放 5672 端口

### Q2: 消息无法消费

**检查项：**
1. 队列是否初始化成功
2. 消息是否正确发布
3. 消费者是否正确连接
4. 查看 RabbitMQ 管理界面确认队列状态

### Q3: 死信队列不工作

**检查项：**
1. 主队列是否正确配置死信交换机
2. 消息是否被拒绝（basic_nack）
3. 死信队列是否正确绑定

### Q4: 如何清空队列

**方法 1：使用测试脚本**
```python
from douyin_auto.mq_utils import RabbitMQManager

mq = RabbitMQManager()
mq.connect()
while mq.consume_one(auto_ack=True):
    pass
mq.disconnect()
```

**方法 2：使用 RabbitMQ 管理界面**
访问 `http://8.136.195.32:15672`，登录后台管理界面清空队列。

---

## 📈 监控建议

### 1. 使用 RabbitMQ 管理界面

访问：`http://8.136.195.32:15672`
- 用户名：`admin`
- 密码：`FBREkFRESAGCffA`

监控指标：
- 队列消息数量
- 消息发布/消费速率
- 连接状态
- 通道状态

### 2. 日志监控

查看日志文件：
- `logs/executor_YYYYMMDD.log` - 执行日志
- `logs/error_YYYYMMDD.log` - 错误日志
- `logs/upload_YYYYMMDD.log` - 上传日志

### 3. 数据库监控

```sql
-- 查看今日发送数量
SELECT COUNT(*) FROM message_logs 
WHERE DATE(created_at) = CURDATE() AND send_status = 1;

-- 查看失败记录
SELECT * FROM message_logs 
WHERE send_status = 0 
ORDER BY created_at DESC 
LIMIT 10;
```

---

## 📝 迁移清单

- [x] 创建 `mq_config.py` - RabbitMQ 配置
- [x] 创建 `mq_utils.py` - RabbitMQ 管理器
- [x] 修改 `db_utils.py` - 移除队列功能，保留日志
- [x] 修改 `upload_command_gui.py` - 使用 MQ 发布消息
- [x] 修改 `auto_executor.py` - 从 MQ 消费消息
- [x] 创建 `test_rabbitmq.py` - 测试脚本
- [x] 更新 `requirements.txt` - 添加 pika 依赖

---

## 🔙 回滚方案

如需回滚到 MySQL 队列：

1. 恢复 `db_utils.py` 的队列功能
2. 恢复 `upload_command_gui.py` 使用 MySQLDBManager
3. 恢复 `auto_executor.py` 从数据库查询消息
4. 移除 `mq_config.py` 和 `mq_utils.py`
5. 从 `requirements.txt` 移除 pika

---

## 📞 技术支持

如有问题，请查看：
1. RabbitMQ 官方文档：https://www.rabbitmq.com/documentation.html
2. Pika 文档：https://pika.readthedocs.io/
3. 项目日志文件