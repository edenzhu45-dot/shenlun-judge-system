# Redis 极简配置指南

## 方法一：使用Render自带的Redis（最简单）

### 步骤1：登录Render
1. 访问：https://render.com
2. 登录您的账号

### 步骤2：创建Redis服务
1. 在Dashboard页面，点击右上角 **"New +"**
2. 选择 **"Redis"**（在列表里找）

### 步骤3：填写信息
如果找不到"Redis"选项，说明界面更新了。请这样操作：
1. 点击 **"New +"**
2. 选择 **"Web Service"**（先选这个）
3. 然后搜索 "Redis" 或查看所有服务类型

**如果还是找不到**，使用备用方案：

## 方法二：使用免费的Redis云服务

### 方案A：Redis Cloud（免费）
1. 访问：https://redis.com/try-free
2. 点击 **"Get Started"** 或 **"Start Free"**
3. 注册账号
4. 创建免费数据库：
   - 选择 **"Free"** 计划
   - 填写数据库名称：`shenlun-judge`
   - 点击创建
5. 获取连接信息：
   - **Public endpoint**：类似 `redis-12345.c1.asia-northeast1-1.gce.cloud.redislabs.com:12345`
   - **Password**：系统生成的密码

### 方案B：Aiven Redis（免费）
1. 访问：https://console.aiven.io/signup
2. 注册账号（有免费额度）
3. 创建Redis服务
4. 获取连接信息

### 方案C：不使用Redis（简化版）
如果您觉得Redis太复杂，我们可以修改代码不使用Redis：

1. 修改 `backend/app/config.py`：
```python
# 将REDIS_URL改为本地内存队列
REDIS_URL = "memory://"  # 使用内存队列，不依赖外部Redis
```

2. 修改 `backend/app/services/redis_service.py`：
```python
# 如果使用内存队列，简化实现
import queue
import threading

class SimpleMemoryQueue:
    def __init__(self):
        self.queue = queue.Queue()
    
    def enqueue(self, task_id, data):
        self.queue.put((task_id, data))
    
    def dequeue(self):
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None

# 使用内存队列替代Redis
redis_queue = SimpleMemoryQueue()
```

## 需要的信息
如果使用外部Redis，需要：
```
REDIS_URL: redis://:密码@主机:端口
示例：redis://:abc123@redis-12345.c1.asia-northeast1-1.gce.cloud.redislabs.com:12345
```

**建议**：先尝试方法一（Render Redis），如果找不到就使用方法二的方案A（Redis Cloud免费版）。