# Supabase 极简配置指南

## 步骤1：访问Supabase
1. 打开浏览器，访问：https://supabase.com
2. 点击右上角 "Sign in" 或 "Start your project"

## 步骤2：创建新项目
1. 登录后，点击 "New project"
2. 填写信息：
   - **Name**: `shenlun-judge`（随便起名）
   - **Database Password**: 设置一个密码（记住它！）
   - **Region**: 选择 "Southeast Asia (Singapore)" 或离您近的
   - **Pricing Plan**: 选择 **Free**
3. 点击 "Create new project"
4. 等待2-3分钟创建完成

## 步骤3：找到API密钥（重要！）
项目创建完成后，您会看到这个页面：

![Supabase Dashboard](https://supabase.com/docs/img/supabase-dashboard.png)

**找到这两个地方**：
1. **URL**：在 "Project URL" 下面，类似：`https://xxxxxx.supabase.co`
2. **API Keys**：在 "Project API keys" 下面
   - **anon public**：公钥（以 `eyJ` 开头）
   - **service_role secret**：私钥（以 `eyJ` 开头，**不要泄露！**）

## 步骤4：创建数据库表
1. 点击左侧菜单 **"SQL Editor"**
2. 点击 **"New query"**
3. 复制粘贴下面的SQL代码：

```sql
-- 创建激活码表
CREATE TABLE IF NOT EXISTS activation_codes (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(100),
    is_used BOOLEAN DEFAULT false,
    is_valid BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    market VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建用户结果表
CREATE TABLE IF NOT EXISTS user_results (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    activation_code VARCHAR(50) NOT NULL,
    file_name VARCHAR(255),
    file_size INTEGER,
    status VARCHAR(50) DEFAULT 'pending',
    score INTEGER,
    feedback TEXT,
    r2_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    processing_time INTEGER
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_activation_codes_code ON activation_codes(code);
CREATE INDEX IF NOT EXISTS idx_activation_codes_user_id ON activation_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_user_results_user_id ON user_results(user_id);
CREATE INDEX IF NOT EXISTS idx_user_results_activation_code ON user_results(activation_code);
CREATE INDEX IF NOT EXISTS idx_user_results_status ON user_results(status);

-- 插入测试激活码
INSERT INTO activation_codes (code, user_id, is_used, is_valid, expires_at, market)
VALUES 
    ('TEST123456', 'test_user', false, true, NOW() + INTERVAL '30 days', 'test'),
    ('TEST789012', 'test_user2', false, true, NOW() + INTERVAL '30 days', 'test')
ON CONFLICT (code) DO NOTHING;
```

4. 点击 **"Run"** 按钮（在右上角）

## 步骤5：验证表创建成功
1. 点击左侧菜单 **"Table Editor"**
2. 应该能看到两个表：`activation_codes` 和 `user_results`
3. 点击表名可以查看数据

## 需要的信息（复制保存）
完成以上步骤后，您需要保存这些信息：

```
SUPABASE_URL: https://xxxxxx.supabase.co
SUPABASE_KEY: eyJ...（公钥）
SUPABASE_SERVICE_KEY: eyJ...（私钥）
```

这些信息将在Render部署时用到。