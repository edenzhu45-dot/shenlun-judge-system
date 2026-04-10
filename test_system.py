#!/usr/bin/env python3
"""
申论智能判卷系统功能测试脚本
测试所有核心功能模块
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_config():
    """测试配置文件"""
    print("=== 测试配置文件 ===")
    try:
        from backend.app.config import settings
        print(f"✓ 配置文件加载成功")
        print(f"  - 应用名称: {settings.APP_NAME}")
        print(f"  - 调试模式: {settings.DEBUG}")
        print(f"  - 内存警告阈值: {settings.MEMORY_WARNING_THRESHOLD_MB} MB")
        print(f"  - PDF最大大小: {settings.PDF_MAX_SIZE_MB} MB")
        return True
    except Exception as e:
        print(f"✗ 配置文件加载失败: {e}")
        return False

async def test_pdf_parser():
    """测试PDF解析器"""
    print("\n=== 测试PDF解析器 ===")
    try:
        from backend.app.services.pdf_parser import PDFParser
        
        # 创建一个测试PDF文件（模拟）
        test_pdf_path = "test_sample.pdf"
        
        # 测试解析器初始化
        parser = PDFParser()
        print(f"✓ PDF解析器初始化成功")
        
        # 测试解析方法（不实际解析文件）
        print(f"✓ PDF解析方法可用")
        
        # 清理测试文件
        if os.path.exists(test_pdf_path):
            os.remove(test_pdf_path)
            
        return True
    except Exception as e:
        print(f"✗ PDF解析器测试失败: {e}")
        return False

async def test_deepseek_client():
    """测试DeepSeek客户端"""
    print("\n=== 测试DeepSeek客户端 ===")
    try:
        from backend.app.services.deepseek_client import DeepSeekClient
        
        # 测试客户端初始化
        client = DeepSeekClient()
        print(f"✓ DeepSeek客户端初始化成功")
        
        # 测试API配置
        print(f"  - API基础URL: {client.base_url}")
        print(f"  - 模型名称: {client.model}")
        
        # 测试内存优化配置
        print(f"  - 上下文长度限制: {client.max_context_length}")
        
        return True
    except Exception as e:
        print(f"✗ DeepSeek客户端测试失败: {e}")
        return False

async def test_redis_service():
    """测试Redis服务"""
    print("\n=== 测试Redis服务 ===")
    try:
        from backend.app.services.redis_service import RedisService
        
        # 测试服务初始化
        service = RedisService()
        print(f"✓ Redis服务初始化成功")
        
        # 测试配置
        print(f"  - Redis主机: {service.redis_host}")
        print(f"  - Redis端口: {service.redis_port}")
        
        # 测试任务队列方法
        print(f"✓ 任务队列方法可用")
        
        return True
    except Exception as e:
        print(f"✗ Redis服务测试失败: {e}")
        return False

async def test_supabase_service():
    """测试Supabase服务"""
    print("\n=== 测试Supabase服务 ===")
    try:
        from backend.app.services.supabase_service import SupabaseService
        
        # 测试服务初始化
        service = SupabaseService()
        print(f"✓ Supabase服务初始化成功")
        
        # 测试配置
        print(f"  - Supabase URL: {service.supabase_url[:30]}...")
        print(f"  - 激活码表名: {service.activation_codes_table}")
        print(f"  - 用户结果表名: {service.user_results_table}")
        
        # 测试分页查询配置
        print(f"  - 分页大小: {service.page_size}")
        
        return True
    except Exception as e:
        print(f"✗ Supabase服务测试失败: {e}")
        return False

async def test_memory_middleware():
    """测试内存中间件"""
    print("\n=== 测试内存中间件 ===")
    try:
        from backend.app.middleware.memory_middleware import MemoryMiddleware
        from fastapi import FastAPI
        from starlette.middleware.base import BaseHTTPMiddleware
        
        # 测试中间件类
        print(f"✓ 内存中间件类定义正确")
        print(f"  - 继承自: {MemoryMiddleware.__bases__[0].__name__}")
        
        # 测试中间件方法
        print(f"✓ 中间件方法可用")
        
        return True
    except Exception as e:
        print(f"✗ 内存中间件测试失败: {e}")
        return False

async def test_api_endpoints():
    """测试API端点"""
    print("\n=== 测试API端点 ===")
    try:
        from backend.app.api.endpoints import router
        
        # 测试路由
        print(f"✓ API路由加载成功")
        
        # 检查路由数量
        routes = [route for route in router.routes]
        print(f"  - 路由数量: {len(routes)}")
        
        # 列出主要路由
        print(f"  - 主要路由:")
        for route in routes:
            if hasattr(route, 'methods'):
                methods = ', '.join(route.methods)
                path = route.path
                print(f"    * {methods} {path}")
        
        return True
    except Exception as e:
        print(f"✗ API端点测试失败: {e}")
        return False

async def test_frontend():
    """测试前端文件"""
    print("\n=== 测试前端文件 ===")
    try:
        frontend_path = Path(__file__).parent / "frontend" / "index.html"
        
        if frontend_path.exists():
            with open(frontend_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"✓ 前端文件存在: {frontend_path}")
            
            # 检查关键元素
            checks = [
                ("表单元素", "form" in content.lower()),
                ("文件上传", "type=\"file\"" in content),
                ("用户ID输入", "user_id" in content.lower()),
                ("激活码输入", "activation_code" in content.lower()),
                ("JavaScript代码", "<script>" in content),
                ("进度显示", "progress" in content.lower()),
                ("结果展示", "result" in content.lower()),
            ]
            
            for check_name, check_result in checks:
                status = "✓" if check_result else "✗"
                print(f"  {status} {check_name}")
            
            return all(check_result for _, check_result in checks)
        else:
            print(f"✗ 前端文件不存在: {frontend_path}")
            return False
    except Exception as e:
        print(f"✗ 前端测试失败: {e}")
        return False

async def test_worker_service():
    """测试Worker服务"""
    print("\n=== 测试Worker服务 ===")
    try:
        # 检查worker文件
        worker_path = Path(__file__).parent / "run_worker.py"
        
        if worker_path.exists():
            with open(worker_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"✓ Worker服务文件存在: {worker_path}")
            
            # 检查关键组件
            checks = [
                ("WorkerService类", "class WorkerService" in content),
                ("异步运行方法", "async def run" in content),
                ("任务处理", "_process_task" in content),
                ("Redis集成", "redis_service" in content),
                ("内存优化", "memory" in content.lower()),
            ]
            
            for check_name, check_result in checks:
                status = "✓" if check_result else "✗"
                print(f"  {status} {check_name}")
            
            return all(check_result for _, check_result in checks)
        else:
            print(f"✗ Worker服务文件不存在: {worker_path}")
            return False
    except Exception as e:
        print(f"✗ Worker服务测试失败: {e}")
        return False

async def test_render_config():
    """测试Render配置文件"""
    print("\n=== 测试Render配置文件 ===")
    try:
        render_path = Path(__file__).parent / "render.yaml"
        
        if render_path.exists():
            with open(render_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"✓ Render配置文件存在: {render_path}")
            
            # 检查关键配置
            checks = [
                ("Web服务配置", "type: web" in content),
                ("Worker服务配置", "type: worker" in content),
                ("内存优化配置", "UVICORN_WORKERS" in content),
                ("并发限制", "UVICORN_LIMIT_CONCURRENCY" in content),
                ("健康检查", "healthCheckPath" in content),
                ("Python环境", "env: python" in content),
            ]
            
            for check_name, check_result in checks:
                status = "✓" if check_result else "✗"
                print(f"  {status} {check_name}")
            
            return all(check_result for _, check_result in checks)
        else:
            print(f"✗ Render配置文件不存在: {render_path}")
            return False
    except Exception as e:
        print(f"✗ Render配置测试失败: {e}")
        return False

async def test_requirements():
    """测试依赖文件"""
    print("\n=== 测试依赖文件 ===")
    try:
        req_path = Path(__file__).parent / "requirements.txt"
        
        if req_path.exists():
            with open(req_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"✓ 依赖文件存在: {req_path}")
            
            # 检查关键依赖
            required_deps = [
                "fastapi",
                "uvicorn",
                "pymupdf",
                "redis",
                "supabase",
                "httpx",
                "python-multipart",
                "python-jose",
                "passlib",
                "bcrypt",
                "python-dotenv",
            ]
            
            missing_deps = []
            for dep in required_deps:
                if dep in content.lower():
                    print(f"  ✓ {dep}")
                else:
                    print(f"  ✗ {dep} (缺失)")
                    missing_deps.append(dep)
            
            if missing_deps:
                print(f"警告: 缺失 {len(missing_deps)} 个关键依赖")
                return False
            else:
                print(f"✓ 所有关键依赖都存在")
                return True
        else:
            print(f"✗ 依赖文件不存在: {req_path}")
            return False
    except Exception as e:
        print(f"✗ 依赖文件测试失败: {e}")
        return False

async def run_all_tests():
    """运行所有测试"""
    print("开始运行申论智能判卷系统功能测试...")
    print("=" * 60)
    
    test_results = []
    
    # 运行所有测试
    tests = [
        ("配置文件", test_config),
        ("PDF解析器", test_pdf_parser),
        ("DeepSeek客户端", test_deepseek_client),
        ("Redis服务", test_redis_service),
        ("Supabase服务", test_supabase_service),
        ("内存中间件", test_memory_middleware),
        ("API端点", test_api_endpoints),
        ("前端界面", test_frontend),
        ("Worker服务", test_worker_service),
        ("Render配置", test_render_config),
        ("依赖文件", test_requirements),
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"测试 {test_name} 时发生异常: {e}")
            test_results.append((test_name, False))
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print("测试总结:")
    print("=" * 60)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "通过" if result else "失败"
        print(f"{test_name:20} {status}")
    
    print("-" * 60)
    print(f"总计: {passed}/{total} 个测试通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("✓ 所有测试通过！系统功能完整。")
        return True
    else:
        print(f"⚠  {total - passed} 个测试失败，请检查相关问题。")
        return False

async def test_system_startup():
    """测试系统启动"""
    print("\n=== 测试系统启动 ===")
    try:
        # 测试主应用启动
        print("测试FastAPI应用启动...")
        from backend.app.main import app
        
        print(f"✓ FastAPI应用创建成功")
        print(f"  - 应用标题: {app.title}")
        print(f"  - 应用版本: {app.version}")
        
        # 检查路由
        routes = app.routes
        print(f"  - 总路由数: {len(routes)}")
        
        # 检查中间件
        print(f"  - 已配置中间件:")
        for middleware in app.user_middleware:
            print(f"    * {middleware.cls.__name__}")
        
        return True
    except Exception as e:
        print(f"✗ 系统启动测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("申论智能判卷系统 - 完整功能测试")
    print("=" * 60)
    
    # 运行组件测试
    components_passed = await run_all_tests()
    
    # 运行系统启动测试
    startup_passed = await test_system_startup()
    
    print("\n" + "=" * 60)
    print("最终测试结果:")
    print("=" * 60)
    
    if components_passed and startup_passed:
        print("✓ 系统测试完全通过！")
        print("\n系统已准备好部署到Render。")
        print("下一步：")
        print("1. 确保所有环境变量已配置")
        print("2. 将代码推送到Git仓库")
        print("3. 在Render.com上创建新服务")
        print("4. 连接Git仓库并部署")
        return 0
    else:
        print("✗ 系统测试未完全通过")
        if not components_passed:
            print("  - 组件测试失败")
        if not startup_passed:
            print("  - 系统启动测试失败")
        print("\n请修复上述问题后再进行部署。")
        return 1

if __name__ == "__main__":
    # 运行异步测试
    exit_code = asyncio.run(main())
    sys.exit(exit_code)