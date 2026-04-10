#!/usr/bin/env python3
"""
判满分软件 - 申论智能辅助判卷系统
主启动文件，包含内存优化配置
"""

import os
import sys
import gc
import asyncio
from contextlib import asynccontextmanager

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from backend.app.config import settings
from backend.app.api import api_router
from backend.app.middleware.memory_middleware import MemoryMiddleware
from backend.app.middleware.rate_limit_middleware import RateLimitMiddleware
from backend.app.services.monitoring_service import MonitoringService

# 内存优化：提前导入关键服务
import backend.app.services.pdf_parser as pdf_parser_module
import backend.app.services.deepseek_client as deepseek_client_module
import backend.app.services.redis_service as redis_service_module

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    print("🚀 启动判满分申论智能判卷系统...")
    print(f"📊 内存优化配置: workers={settings.UVICORN_WORKERS}, limit_concurrency={settings.UVICORN_LIMIT_CONCURRENCY}")
    
    # 启动时执行一次GC
    gc.collect()
    
    # 初始化监控服务
    monitoring_service = MonitoringService()
    app.state.monitoring_service = monitoring_service
    
    # 启动监控任务
    monitoring_task = asyncio.create_task(monitoring_service.start_monitoring())
    app.state.monitoring_task = monitoring_task
    
    yield
    
    # 关闭时清理
    print("🛑 正在关闭系统...")
    if hasattr(app.state, 'monitoring_task'):
        app.state.monitoring_task.cancel()
        try:
            await app.state.monitoring_task
        except asyncio.CancelledError:
            pass
    
    # 强制GC清理
    gc.collect()
    print("✅ 系统已安全关闭")

# 创建FastAPI应用
app = FastAPI(
    title="判满分申论智能辅助判卷系统",
    description="基于AI的申论智能判卷系统，支持PDF上传、AI评分、成长跟踪等功能",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(MemoryMiddleware)
app.add_middleware(RateLimitMiddleware)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# 设置模板
templates = Jinja2Templates(directory="frontend/templates")

# 包含API路由
app.include_router(api_router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "memory_optimized": True,
        "timestamp": asyncio.get_event_loop().time()
    }

@app.get("/memory")
async def memory_status():
    """内存状态接口"""
    import psutil
    process = psutil.Process()
    memory_info = process.memory_info()
    
    return {
        "rss_mb": memory_info.rss / 1024 / 1024,
        "vms_mb": memory_info.vms / 1024 / 1024,
        "percent": process.memory_percent(),
        "available_mb": psutil.virtual_memory().available / 1024 / 1024,
        "total_mb": psutil.virtual_memory().total / 1024 / 1024,
    }

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """添加安全头"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

if __name__ == "__main__":
    import uvicorn
    
    # 使用优化配置启动
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        workers=settings.UVICORN_WORKERS,
        limit_concurrency=settings.UVICORN_LIMIT_CONCURRENCY,
        timeout_keep_alive=settings.UVICORN_TIMEOUT_KEEP_ALIVE,
        log_level="info" if settings.DEBUG else "warning",
        access_log=settings.DEBUG,
    )