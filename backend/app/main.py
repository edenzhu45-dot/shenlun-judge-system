"""
主应用文件 - FastAPI应用入口
遵循技术升级指南的优化方案
"""

import os
import gc
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.api.endpoints import router as api_router
from backend.app.middleware.memory_middleware import MemoryMiddleware
from backend.app.services.monitoring_service import monitoring_service
from backend.app.services.redis_service import redis_service
from backend.app.services.supabase_service import supabase_service
from backend.app.services.cloudflare_r2_service import cloudflare_r2_service

# 配置日志
handlers = [logging.StreamHandler()]
if settings.LOG_TO_FILE:
    handlers.append(logging.FileHandler("app.log"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    遵循技术升级指南1.1.1和1.1.2
    """
    logger.info("应用启动中...")
    
    # 启动时内存优化
    gc.enable()
    gc.set_threshold(700, 10, 10)  # 优化GC阈值
    
    # 初始化服务
    try:
        # 初始化Redis连接池
        await redis_service.initialize()
        logger.info("Redis服务初始化完成")
        
        # 初始化Supabase连接
        await supabase_service.initialize()
        logger.info("Supabase服务初始化完成")
        
        # 初始化R2服务
        if cloudflare_r2_service:
            cloudflare_r2_service.initialize()
            logger.info("Cloudflare R2服务初始化完成")
        
        # 启动监控服务
        await monitoring_service.start_monitoring()
        logger.info("监控服务启动完成")
        
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        # 继续启动，部分服务可能不可用
    
    logger.info(f"应用启动完成，环境: {settings.ENVIRONMENT}")
    
    yield  # 应用运行
    
    logger.info("应用关闭中...")
    
    # 关闭时清理
    try:
        # 停止监控服务
        await monitoring_service.stop_monitoring()
        
        # 关闭Redis连接
        await redis_service.close()
        
        # 强制垃圾回收
        gc.collect()
        
    except Exception as e:
        logger.error(f"应用关闭时出错: {e}")
    
    logger.info("应用关闭完成")


# 创建FastAPI应用
app = FastAPI(
    title="申论智能辅助判卷系统",
    description="基于DeepSeek AI的申论智能判卷系统，支持PDF上传和实时评分",
    version="2.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加内存监控中间件
app.add_middleware(MemoryMiddleware)

# 添加安全头中间件
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    
    # 添加安全头
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # 添加性能监控头
    response.headers["Server-Timing"] = "app;dur=0"
    
    return response

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request, call_next):
    import time
    
    start_time = time.time()
    
    # 记录请求开始
    logger.debug(f"请求开始: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        
        # 计算请求时间
        process_time = time.time() - start_time
        
        # 记录请求完成
        logger.info(
            f"请求完成: {request.method} {request.url.path} "
            f"- 状态: {response.status_code} "
            f"- 时间: {process_time:.3f}s"
        )
        
        return response
        
    except Exception as e:
        # 记录请求错误
        process_time = time.time() - start_time
        logger.error(
            f"请求错误: {request.method} {request.url.path} "
            f"- 错误: {str(e)} "
            f"- 时间: {process_time:.3f}s"
        )
        raise


# 挂载静态文件（用于前端）
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
else:
    # 创建简单的根路由
    @app.get("/")
    async def root():
        return {
            "message": "申论智能辅助判卷系统 API",
            "version": "2.0.0",
            "docs": "/docs",
            "health": "/api/system/health"
        }


# 挂载API路由
app.include_router(api_router, prefix="/api", tags=["api"])


# 健康检查端点
@app.get("/health")
async def health_check():
    """
    简单的健康检查端点
    """
    return {
        "status": "healthy",
        "service": "申论智能判卷系统",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
    }


# 错误处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    全局异常处理器
    """
    logger.error(f"全局异常: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "服务器内部错误",
            "message": str(exc) if settings.DEBUG else "请稍后重试",
            "request_id": request.headers.get("X-Request-ID", "unknown"),
        }
    )


# 导入必要的模块
from datetime import datetime

# 应用信息
__version__ = "2.0.0"
__author__ = "申论智能判卷系统团队"
__description__ = "基于DeepSeek AI的申论智能判卷系统"

# 导出应用
__all__ = ["app"]