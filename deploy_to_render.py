#!/usr/bin/env python3
"""
部署到Render的准备工作脚本
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_git_status():
    """检查Git状态"""
    print("检查Git状态...")
    
    try:
        # 检查是否在Git仓库中
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        if result.returncode != 0:
            print("  ✗ 当前目录不是Git仓库")
            return False
        
        print("  ✓ Git仓库已初始化")
        
        # 检查是否有未提交的更改
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if result.stdout.strip():
            print("  ⚠ 有未提交的更改:")
            for line in result.stdout.strip().split('\n'):
                if line:
                    print(f"    {line}")
            return True
        else:
            print("  ✓ 所有更改已提交")
            return True
            
    except FileNotFoundError:
        print("  ✗ Git未安装")
        return False

def check_render_config():
    """检查Render配置"""
    print("\n检查Render配置...")
    
    render_yaml = Path("render.yaml")
    if not render_yaml.exists():
        print("  ✗ render.yaml文件不存在")
        return False
    
    print("  ✓ render.yaml文件存在")
    
    # 检查文件内容
    try:
        with open(render_yaml, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查基本配置
        required_sections = ["services", "name", "type"]
        for section in required_sections:
            if section in content:
                print(f"  ✓ 包含{section}配置")
            else:
                print(f"  ⚠ 缺少{section}配置")
        
        return True
    except Exception as e:
        print(f"  ✗ 读取render.yaml失败: {e}")
        return False

def check_requirements():
    """检查依赖文件"""
    print("\n检查依赖文件...")
    
    requirements_files = ["requirements.txt", "requirements_simple.txt"]
    found = False
    
    for req_file in requirements_files:
        if Path(req_file).exists():
            print(f"  ✓ {req_file}文件存在")
            found = True
            
            # 检查文件大小
            size = Path(req_file).stat().st_size
            if size > 0:
                print(f"    - 文件大小: {size}字节")
            else:
                print(f"    ⚠ 文件为空")
    
    if not found:
        print("  ✗ 未找到requirements文件")
        return False
    
    return True

def check_project_structure():
    """检查项目结构"""
    print("\n检查项目结构...")
    
    required_dirs = [
        "backend/app",
        "backend/app/api",
        "backend/app/services",
        "backend/app/middleware",
        "frontend"
    ]
    
    required_files = [
        "backend/app/main.py",
        "backend/app/config.py",
        "backend/app/api/endpoints.py",
        "frontend/index.html",
        "run_worker.py",
        ".env.example"
    ]
    
    all_ok = True
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"  ✓ 目录: {dir_path}")
        else:
            print(f"  ✗ 目录不存在: {dir_path}")
            all_ok = False
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"  ✓ 文件: {file_path}")
        else:
            print(f"  ✗ 文件不存在: {file_path}")
            all_ok = False
    
    return all_ok

def check_environment_vars():
    """检查环境变量配置"""
    print("\n检查环境变量配置...")
    
    env_example = Path(".env.example")
    if not env_example.exists():
        print("  ✗ .env.example文件不存在")
        return False
    
    print("  ✓ .env.example文件存在")
    
    # 读取示例文件
    try:
        with open(env_example, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        required_vars = [
            "DEEPSEEK_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "REDIS_URL"
        ]
        
        found_vars = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    var_name = line.split("=")[0].strip()
                    found_vars.append(var_name)
        
        print(f"  - 找到{len(found_vars)}个环境变量")
        
        missing = []
        for var in required_vars:
            if var in found_vars:
                print(f"    ✓ {var}")
            else:
                print(f"    ⚠ {var} (建议添加)")
                missing.append(var)
        
        if missing:
            print(f"  ⚠ 缺少{len(missing)}个建议的环境变量")
        
        return True
    except Exception as e:
        print(f"  ✗ 读取.env.example失败: {e}")
        return False

def generate_deployment_instructions():
    """生成部署说明"""
    print("\n" + "=" * 60)
    print("部署到Render的步骤")
    print("=" * 60)
    
    instructions = """
## 步骤1：准备GitHub仓库
1. 在GitHub上创建新的仓库
2. 将本地代码推送到GitHub：
   ```
   git init
   git add .
   git commit -m "Initial commit: 申论智能判卷系统"
   git branch -M main
   git remote add origin https://github.com/你的用户名/你的仓库名.git
   git push -u origin main
   ```

## 步骤2：配置Render账户
1. 访问 https://render.com 并注册/登录
2. 点击"New +"按钮，选择"Blueprint"
3. 连接你的GitHub账户并选择仓库

## 步骤3：配置环境变量
在Render控制台中设置以下环境变量：

### 必需的环境变量
- DEEPSEEK_API_KEY: 你的DeepSeek API密钥
- SUPABASE_URL: 你的Supabase项目URL
- SUPABASE_KEY: 你的Supabase API密钥
- REDIS_URL: Redis连接URL（可以使用Render的Redis服务）

### 可选的环境变量
- CLOUDFLARE_R2_ACCOUNT_ID: Cloudflare R2账户ID
- CLOUDFLARE_R2_ACCESS_KEY_ID: R2访问密钥ID
- CLOUDFLARE_R2_SECRET_ACCESS_KEY: R2密钥
- CLOUDFLARE_R2_BUCKET_NAME: R2存储桶名称
- CLOUDFLARE_R2_PUBLIC_URL: R2公共URL

## 步骤4：启动部署
1. Render会自动检测render.yaml文件
2. 点击"Apply"开始部署
3. 等待部署完成（约5-10分钟）

## 步骤5：验证部署
1. 访问Render提供的URL（如 https://your-app.onrender.com）
2. 检查健康端点：https://your-app.onrender.com/health
3. 测试文件上传功能

## 注意事项
1. **免费计划限制**：
   - 内存：512MB
   - 每月运行时间：750小时
   - 自动休眠：15分钟无流量后休眠
   - 唤醒时间：约30秒

2. **性能优化**：
   - 系统已配置单worker模式以节省内存
   - 使用流式PDF解析避免内存溢出
   - 大文件存储在R2，Supabase只存URL

3. **监控建议**：
   - 定期检查Render控制台的日志
   - 设置内存使用告警（>400MB）
   - 监控API响应时间
    """
    
    print(instructions)
    
    # 生成部署检查清单
    checklist_path = Path("deployment_checklist_completed.md")
    with open(checklist_path, 'w', encoding='utf-8') as f:
        f.write("# 部署检查清单 - 已完成\n\n")
        f.write("## 检查结果\n")
        f.write("- ✅ Git状态检查完成\n")
        f.write("- ✅ Render配置检查完成\n")
        f.write("- ✅ 依赖文件检查完成\n")
        f.write("- ✅ 项目结构检查完成\n")
        f.write("- ✅ 环境变量配置检查完成\n\n")
        f.write("## 下一步\n")
        f.write("按照上面的部署步骤将系统部署到Render平台。\n")
    
    print(f"\n✓ 已生成部署检查清单: {checklist_path}")

def main():
    """主函数"""
    print("=" * 60)
    print("申论智能判卷系统 - 部署准备检查")
    print("=" * 60)
    
    # 切换到项目目录
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    checks = [
        ("Git状态", check_git_status),
        ("Render配置", check_render_config),
        ("依赖文件", check_requirements),
        ("项目结构", check_project_structure),
        ("环境变量", check_environment_vars),
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        if not check_func():
            all_passed = False
    
    if all_passed:
        print("\n" + "=" * 60)
        print("✅ 所有检查通过！系统已准备好部署到Render。")
        print("=" * 60)
        
        # 生成部署说明
        generate_deployment_instructions()
        
        return 0
    else:
        print("\n" + "=" * 60)
        print("⚠ 部分检查未通过，请修复问题后再部署。")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())