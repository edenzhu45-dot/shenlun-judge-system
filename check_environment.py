#!/usr/bin/env python3
"""
环境检查脚本
检查系统环境和依赖
"""

import sys
import os
import platform

def check_python_version():
    """检查Python版本"""
    print("=== Python环境检查 ===")
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    
    # 检查Python版本要求
    version_info = sys.version_info
    if version_info.major >= 3 and version_info.minor >= 8:
        print("✓ Python版本符合要求 (>= 3.8)")
        return True
    else:
        print(f"✗ Python版本过低: {version_info.major}.{version_info.minor}")
        return False

def check_os():
    """检查操作系统"""
    print("\n=== 操作系统检查 ===")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"平台: {platform.platform()}")
    return True

def check_project_structure():
    """检查项目结构"""
    print("\n=== 项目结构检查 ===")
    
    required_dirs = [
        "backend",
        "backend/app",
        "backend/app/api",
        "backend/app/middleware",
        "backend/app/services",
        "frontend",
    ]
    
    required_files = [
        "requirements.txt",
        "render.yaml",
        "run_worker.py",
        "backend/app/main.py",
        "backend/app/config.py",
        "frontend/index.html",
    ]
    
    all_ok = True
    
    # 检查目录
    print("检查目录结构:")
    for dir_path in required_dirs:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            print(f"  ✓ {dir_path}/")
        else:
            print(f"  ✗ {dir_path}/ (缺失)")
            all_ok = False
    
    # 检查文件
    print("\n检查文件:")
    for file_path in required_files:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            file_size = os.path.getsize(file_path)
            print(f"  ✓ {file_path} ({file_size} bytes)")
        else:
            print(f"  ✗ {file_path} (缺失)")
            all_ok = False
    
    return all_ok

def check_imports():
    """检查Python导入"""
    print("\n=== Python导入检查 ===")
    
    imports_to_check = [
        ("fastapi", "FastAPI"),
        ("uvicorn", ""),  # uvicorn是模块，没有Uvicorn类
        ("fitz", ""),  # pymupdf导入为fitz
        ("redis", "Redis"),
        ("supabase", "create_client"),
        ("httpx", "AsyncClient"),
        ("asyncio", "run"),
    ]
    
    all_ok = True
    
    for module_name, item_name in imports_to_check:
        try:
            if item_name:
                # 尝试导入特定项目
                exec(f"from {module_name} import {item_name}")
                print(f"  ✓ {module_name}.{item_name}")
            else:
                # 尝试导入整个模块
                exec(f"import {module_name}")
                print(f"  ✓ {module_name}")
        except ImportError as e:
            print(f"  ✗ {module_name}: {e}")
            all_ok = False
    
    return all_ok

def check_config_files():
    """检查配置文件内容"""
    print("\n=== 配置文件检查 ===")
    
    config_files = [
        ("requirements.txt", ["fastapi", "uvicorn", "pymupdf", "redis", "supabase"]),
        ("render.yaml", ["type: web", "type: worker", "UVICORN_WORKERS"]),
    ]
    
    all_ok = True
    
    for file_name, required_content in config_files:
        if os.path.exists(file_name):
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                print(f"检查 {file_name}:")
                for req in required_content:
                    if req in content:
                        print(f"  ✓ 包含: {req}")
                    else:
                        print(f"  ✗ 缺失: {req}")
                        all_ok = False
            except Exception as e:
                print(f"  ✗ 读取 {file_name} 失败: {e}")
                all_ok = False
        else:
            print(f"  ✗ {file_name} 不存在")
            all_ok = False
    
    return all_ok

def main():
    """主函数"""
    print("申论智能判卷系统 - 环境检查")
    print("=" * 60)
    
    checks = [
        ("Python版本", check_python_version),
        ("操作系统", check_os),
        ("项目结构", check_project_structure),
        ("Python导入", check_imports),
        ("配置文件", check_config_files),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"检查 {check_name} 时发生错误: {e}")
            results.append((check_name, False))
    
    print("\n" + "=" * 60)
    print("环境检查总结:")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "通过" if result else "失败"
        print(f"{check_name:15} {status}")
    
    print("-" * 60)
    print(f"总计: {passed}/{total} 项检查通过")
    
    if passed == total:
        print("\n✓ 环境检查完全通过！")
        print("系统已准备好进行部署。")
        return 0
    else:
        print(f"\n⚠  {total - passed} 项检查失败")
        print("请修复上述问题后再进行部署。")
        
        # 提供修复建议
        print("\n修复建议:")
        if not any(r[0] == "Python版本" and r[1] for r in results):
            print("1. 安装Python 3.8或更高版本")
            print("2. 确保Python已添加到系统PATH")
        
        if not any(r[0] == "Python导入" and r[1] for r in results):
            print("3. 安装依赖包: pip install -r requirements.txt")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())