"""
内存中间件 - 监控请求内存使用
"""

import gc
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.config import settings

logger = logging.getLogger(__name__)


class MemoryMiddleware(BaseHTTPMiddleware):
    """内存监控中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录请求开始时间
        start_time = time.time()
        
        # 记录请求前内存
        import psutil
        process = psutil.Process()
        memory_before = process.memory_info().rss
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 记录请求后内存
            memory_after = process.memory_info().rss
            memory_used = (memory_after - memory_before) / 1024 / 1024  # MB
            
            # 计算请求时间
            request_time = time.time() - start_time
            
            # 记录慢请求和大内存请求
            if request_time > 5.0:  # 5秒以上
                logger.warning(f"慢请求: {request.method} {request.url.path} - {request_time:.2f}秒")
            
            if memory_used > 50:  # 使用超过50MB内存
                logger.warning(f"大内存请求: {request.method} {request.url.path} - 使用内存: {memory_used:.1f}MB")
            
            # 如果内存使用过高，触发GC
            if memory_after > settings.MEMORY_WARNING_THRESHOLD_MB * 1024 * 1024:
                logger.debug(f"内存使用较高，触发GC: {memory_after / 1024 / 1024:.1f}MB")
                gc.collect()
            
            # 添加监控头
            response.headers["X-Request-Time"] = f"{request_time:.3f}"
            response.headers["X-Memory-Used-MB"] = f"{memory_used:.1f}"
            
            return response
            
        except Exception as e:
            # 记录错误
            logger.error(f"请求处理错误: {request.method} {request.url.path} - {str(e)}")
            raise