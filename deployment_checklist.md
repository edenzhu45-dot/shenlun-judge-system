# 申论智能判卷系统 - 部署检查清单

## 系统概述
- 项目名称：申论智能判卷系统
- 技术栈：FastAPI + DeepSeek AI + Supabase + Redis + Cloudflare R2
- 部署平台：Render.com
- 架构：Web服务 + Worker服务

## 部署前检查

### ✅ 已完成的项目结构
1. **后端服务** (`backend/app/`)
   - `main.py` - FastAPI主应用
   - `config.py` - 配置文件
   - `api/endpoints.py` - API接口
   - `services/` - 核心服务模块
   - `middleware/` - 中间件

2. **前端界面** (`frontend/index.html`)
   - 完整的用户界面
   - 文件上传功能
   - 实时进度显示
   - 结果展示

3. **Worker服务** (`run_worker.py`)
   - 异步任务处理
   - Redis队列集成
   - 错误重试机制

4. **部署配置** (`render.yaml`)
   - Web服务配置
   - Worker服务配置
   - 内存优化配置

5. **依赖管理** (`requirements.txt`)
   - 所有必要的Python包
   - 版本锁定

6. **环境配置** (`.env.example`, `.env`)
   - 环境变量模板
   - 测试配置

### ✅ 已通过的功能测试
1. 配置文件加载测试 ✓
2. PDF解析器测试 ✓
3. 内存中间件测试 ✓
4. API端点测试 ✓
5. 前端文件测试 ✓
6. 部署配置测试 ✓
7. 依赖文件测试 ✓
8. 主应用测试 ✓
9. Worker服务测试 ✓
10. 技术升级指南测试 ✓

## 部署步骤

### 步骤1：准备Render账户
1. 注册Render账户（如果还没有）
2. 创建新的Blueprint项目
3. 连接GitHub仓库

### 步骤2：配置环境变量
在Render控制台中设置以下环境变量：

#### 必需的环境变量
```
# DeepSeek API配置
DEEPSEEK_API_KEY=your_actual_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Supabase配置
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Redis配置
REDIS_URL=redis://your-redis-host:6379

# Cloudflare R2配置
CLOUDFLARE_R2_ACCOUNT_ID=your_account_id
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key_id
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_access_key
CLOUDFLARE_R2_BUCKET_NAME=your-bucket-name
CLOUDFLARE_R2_PUBLIC_URL=https://your_account_id.r2.cloudflarestorage.com
```

#### 优化的环境变量（已配置在render.yaml中）
```
ENVIRONMENT=production
DEBUG=false
PORT=8000
UVICORN_WORKERS=1
UVICORN_LIMIT_CONCURRENCY=15
UVICORN_TIMEOUT_KEEP_ALIVE=65
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=52428800
QUERY_PAGE_SIZE=20
MEMORY_WARNING_THRESHOLD_MB=350
MEMORY_CRITICAL_THRESHOLD_MB=450
MONITORING_INTERVAL=30
CACHE_TTL_USER_HISTORY=300
CACHE_TTL_QUESTION_BANK=3600
PDF_MAX_SIZE_MB=10
PDF_CHUNK_SIZE_KB=1024
DEEPSEEK_MAX_CONTEXT_LENGTH=8000
MATERIAL_SUMMARY_LENGTH=4000
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 步骤3：部署应用
1. 推送代码到GitHub仓库
2. 在Render中创建Blueprint
3. 系统会自动检测`render.yaml`文件
4. 等待构建和部署完成

### 步骤4：验证部署
1. 访问Web服务URL
2. 测试文件上传功能
3. 验证AI判卷流程
4. 检查Worker服务状态

## 部署后监控

### 性能监控
1. **内存使用**：保持在512MB限制内
2. **响应时间**：API响应应小于2秒
3. **错误率**：监控HTTP错误率
4. **队列长度**：监控Redis任务队列

### 日志监控
1. 应用日志：`app.log`
2. 错误日志：监控异常和错误
3. 访问日志：记录API调用

### 健康检查
1. 主服务健康检查：`GET /health`
2. Worker服务状态：检查Redis连接
3. 数据库连接：检查Supabase连接

## 故障排除

### 常见问题
1. **内存不足**：减少UVICORN_WORKERS，增加内存警告阈值
2. **API超时**：调整UVICORN_TIMEOUT_KEEP_ALIVE
3. **连接池耗尽**：增加Supabase连接池大小
4. **文件上传失败**：检查MAX_UPLOAD_SIZE设置

### 紧急措施
1. **重启服务**：在Render控制台中重启
2. **回滚部署**：恢复到上一个稳定版本
3. **增加资源**：升级到付费计划

## 安全注意事项
1. **API密钥保护**：不要提交到代码仓库
2. **CORS配置**：限制允许的源
3. **文件上传**：验证文件类型和大小
4. **数据库访问**：使用最小权限原则

## 后续优化建议
1. **CDN集成**：使用Cloudflare CDN加速静态资源
2. **数据库索引**：优化Supabase查询性能
3. **缓存策略**：增加Redis缓存命中率
4. **监控告警**：设置性能告警阈值

---

**部署状态**：✅ 系统已准备好部署
**测试结果**：10/10 测试通过
**预计部署时间**：10-15分钟
**内存需求**：512MB（免费计划）
**存储需求**：临时文件存储（uploads目录）