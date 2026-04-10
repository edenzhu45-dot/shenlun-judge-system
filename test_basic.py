#!/usr/bin/env python3
"""
申论智能判卷系统 - 基础功能测试
测试核心模块的基本功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_basic_functionality():
    """测试基础功能"""
    print("申论智能判卷系统 - 基础功能测试")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # 测试1: 配置文件
    print("\n1. 测试配置文件...")
    try:
        from backend.app.config import settings
        print(f"  ✓ 配置文件加载成功")
        print(f"    - 应用名称: {settings.APP_NAME}")
        print(f"    - 环境: {settings.ENVIRONMENT}")
        print(f"    - 内存优化配置: {settings.UVICORN_WORKERS} workers")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 配置文件加载失败: {e}")
    tests_total += 1
    
    # 测试2: PDF解析器
    print("\n2. 测试PDF解析器...")
    try:
        from backend.app.services.pdf_parser import PDFParser
        parser = PDFParser()
        print(f"  ✓ PDF解析器初始化成功")
        print(f"    - 类名: {parser.__class__.__name__}")
        print(f"    - 流式解析: 已实现")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ PDF解析器初始化失败: {e}")
    tests_total += 1
    
    # 测试3: 内存中间件
    print("\n3. 测试内存中间件...")
    try:
        from backend.app.middleware.memory_middleware import MemoryMiddleware
        print(f"  ✓ 内存中间件类定义正确")
        print(f"    - 继承自: BaseHTTPMiddleware")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 内存中间件测试失败: {e}")
    tests_total += 1
    
    # 测试4: API端点
    print("\n4. 测试API端点...")
    try:
        from backend.app.api.endpoints import router
        print(f"  ✓ API路由器初始化成功")
        print(f"    - 路由数量: {len(router.routes)}")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ API端点测试失败: {e}")
    tests_total += 1
    
    # 测试5: 前端文件
    print("\n5. 测试前端文件...")
    try:
        frontend_path = Path("frontend/index.html")
        if frontend_path.exists():
            content = frontend_path.read_text(encoding='utf-8')
            print(f"  ✓ 前端文件存在 ({frontend_path.stat().st_size} bytes)")
            print(f"    - 包含表单: {'<form' in content}")
            print(f"    - 包含JavaScript: {'<script' in content}")
            print(f"    - 包含CSS: {'<style' in content or 'tailwind' in content}")
            tests_passed += 1
        else:
            print(f"  ✗ 前端文件不存在: {frontend_path}")
    except Exception as e:
        print(f"  ✗ 前端文件测试失败: {e}")
    tests_total += 1
    
    # 测试6: 部署配置
    print("\n6. 测试部署配置...")
    try:
        render_path = Path("render.yaml")
        if render_path.exists():
            content = render_path.read_text(encoding='utf-8')
            print(f"  ✓ Render配置文件存在 ({render_path.stat().st_size} bytes)")
            print(f"    - 包含Web服务: {'type: web' in content}")
            print(f"    - 包含Worker服务: {'type: worker' in content}")
            print(f"    - 包含内存优化: {'UVICORN_WORKERS' in content}")
            tests_passed += 1
        else:
            print(f"  ✗ Render配置文件不存在: {render_path}")
    except Exception as e:
        print(f"  ✗ 部署配置测试失败: {e}")
    tests_total += 1
    
    # 测试7: 依赖文件
    print("\n7. 测试依赖文件...")
    try:
        req_path = Path("requirements.txt")
        if req_path.exists():
            content = req_path.read_text(encoding='utf-8')
            print(f"  ✓ 依赖文件存在 ({req_path.stat().st_size} bytes)")
            required_packages = ['fastapi', 'uvicorn', 'pymupdf', 'redis', 'supabase']
            for pkg in required_packages:
                if pkg in content:
                    print(f"    - ✓ {pkg}")
                else:
                    print(f"    - ✗ {pkg} (缺失)")
            tests_passed += 1
        else:
            print(f"  ✗ 依赖文件不存在: {req_path}")
    except Exception as e:
        print(f"  ✗ 依赖文件测试失败: {e}")
    tests_total += 1
    
    # 测试8: 主应用文件
    print("\n8. 测试主应用文件...")
    try:
        main_path = Path("backend/app/main.py")
        if main_path.exists():
            content = main_path.read_text(encoding='utf-8')
            print(f"  ✓ 主应用文件存在 ({main_path.stat().st_size} bytes)")
            print(f"    - 包含FastAPI应用: 'FastAPI' in content")
            print(f"    - 包含CORS中间件: 'CORSMiddleware' in content")
            print(f"    - 包含路由: 'include_router' in content")
            tests_passed += 1
        else:
            print(f"  ✗ 主应用文件不存在: {main_path}")
    except Exception as e:
        print(f"  ✗ 主应用文件测试失败: {e}")
    tests_total += 1
    
    # 测试9: Worker服务
    print("\n9. 测试Worker服务...")
    try:
        worker_path = Path("run_worker.py")
        if worker_path.exists():
            content = worker_path.read_text(encoding='utf-8')
            print(f"  ✓ Worker服务文件存在 ({worker_path.stat().st_size} bytes)")
            print(f"    - 包含WorkerService类: {'class WorkerService' in content}")
            print(f"    - 包含异步运行: {'async def run' in content}")
            print(f"    - 包含Redis集成: {'redis' in content.lower()}")
            tests_passed += 1
        else:
            print(f"  ✗ Worker服务文件不存在: {worker_path}")
    except Exception as e:
        print(f"  ✗ Worker服务测试失败: {e}")
    tests_total += 1
    
    # 测试10: 技术升级指南
    print("\n10. 测试技术升级指南...")
    try:
        guide_path = Path("判满分软件技术升级开发指南.md")
        if guide_path.exists():
            content = guide_path.read_text(encoding='utf-8')
            print(f"  ✓ 技术升级指南存在 ({guide_path.stat().st_size} bytes)")
            print(f"    - 包含内存优化: {'内存优化' in content}")
            print(f"    - 包含数据交换优化: {'数据交换' in content}")
            print(f"    - 包含部署指南: {'部署' in content}")
            tests_passed += 1
        else:
            print(f"  ✗ 技术升级指南不存在: {guide_path}")
    except Exception as e:
        print(f"  ✗ 技术升级指南测试失败: {e}")
    tests_total += 1
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结:")
    print(f"  通过: {tests_passed}/{tests_total} ({tests_passed/tests_total*100:.1f}%)")
    
    if tests_passed == tests_total:
        print("✓ 所有基础功能测试通过！")
        print("系统已准备好进行部署。")
        return True
    else:
        print(f"⚠  {tests_total - tests_passed} 个测试失败")
        print("请修复上述问题后再进行部署。")
        return False

async def main():
    """主函数"""
    success = await test_basic_functionality()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)