#!/usr/bin/env python3
"""
本地启动测试 - 验证系统可以正常运行
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def check_dependencies():
    """检查依赖是否安装"""
    print("检查依赖...")
    
    required_packages = [
        ("fastapi", "FastAPI"),
        ("uvicorn", ""),  # uvicorn是模块，没有Uvicorn类
        ("fitz", ""),  # pymupdf导入为fitz
        ("redis", "Redis"),
        ("supabase", "create_client"),
        ("httpx", "AsyncClient"),
        ("pydantic", "BaseModel"),
        ("pydantic_settings", "BaseSettings"),
    ]
    
    missing = []
    for package, class_name in required_packages:
        try:
            if class_name:
                # 检查特定类
                module = __import__(package, fromlist=[class_name])
                if hasattr(module, class_name):
                    print(f"  ✓ {package} ({class_name})")
                else:
                    print(f"  ⚠ {package} (缺少{class_name})")
                    missing.append(package)
            else:
                # 只检查模块
                __import__(package)
                print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n缺少依赖: {missing}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    print("所有依赖已安装 ✓")
    return True

def check_config():
    """检查配置文件"""
    print("\n检查配置文件...")
    
    try:
        # 添加项目路径
        sys.path.insert(0, str(Path(__file__).parent))
        
        from backend.app.config import settings
        
        print(f"  ✓ 配置文件加载成功")
        print(f"    - APP_NAME: {settings.APP_NAME}")
        print(f"    - ENVIRONMENT: {settings.ENVIRONMENT}")
        print(f"    - DEBUG: {settings.DEBUG}")
        print(f"    - CORS_ORIGINS: {settings.CORS_ORIGINS}")
        
        return True
    except Exception as e:
        print(f"  ✗ 配置文件加载失败: {e}")
        return False

def check_services():
    """检查服务初始化"""
    print("\n检查服务初始化...")
    
    try:
        from backend.app.services.pdf_parser import pdf_parser
        from backend.app.services.redis_service import redis_service
        from backend.app.services.supabase_service import supabase_service
        
        print(f"  ✓ PDF解析器: {pdf_parser.__class__.__name__}")
        print(f"  ✓ Redis服务: {redis_service.__class__.__name__}")
        print(f"  ✓ Supabase服务: {supabase_service.__class__.__name__}")
        
        return True
    except Exception as e:
        print(f"  ✗ 服务初始化失败: {e}")
        return False

def start_fastapi():
    """启动FastAPI应用"""
    print("\n启动FastAPI应用...")
    
    try:
        # 切换到项目目录
        os.chdir(Path(__file__).parent)
        
        # 启动命令
        cmd = [
            sys.executable, "-m", "uvicorn",
            "backend.app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--workers", "1",
            "--reload"
        ]
        
        print(f"启动命令: {' '.join(cmd)}")
        print(f"应用将在 http://localhost:8000 启动")
        print(f"API文档: http://localhost:8000/docs")
        print(f"前端界面: http://localhost:8000/")
        print("\n按 Ctrl+C 停止服务")
        
        # 启动服务
        process = subprocess.Popen(cmd)
        
        # 等待一段时间让服务启动
        time.sleep(5)
        
        # 检查服务是否运行
        import requests
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print(f"\n✓ 服务启动成功！")
                print(f"  健康检查: {response.json()}")
            else:
                print(f"\n⚠ 服务启动但健康检查失败: {response.status_code}")
        except:
            print(f"\n⚠ 无法连接到服务，可能仍在启动中...")
        
        # 等待用户中断
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n停止服务...")
            process.terminate()
            process.wait()
        
        return True
    except Exception as e:
        print(f"  ✗ 启动失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("申论智能判卷系统 - 本地启动测试")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        return 1
    
    # 检查配置
    if not check_config():
        return 1
    
    # 检查服务
    if not check_services():
        return 1
    
    print("\n" + "=" * 60)
    print("所有检查通过！准备启动应用...")
    print("=" * 60)
    
    # 启动FastAPI
    return 0 if start_fastapi() else 1

if __name__ == "__main__":
    sys.exit(main())