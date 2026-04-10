"""
Redis服务 - 实现任务队列和缓存优化
遵循技术升级指南1.1.3和1.2.3
"""

import json
import asyncio
import logging
import uuid
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from backend.app.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """优化的Redis服务，实现任务队列和缓存管理"""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.max_connections = settings.REDIS_MAX_CONNECTIONS
        self.task_queue_name = settings.REDIS_TASK_QUEUE_NAME
        self.result_ttl = settings.REDIS_RESULT_TTL
        
        # 连接池
        self.pool: Optional[ConnectionPool] = None
        self.redis_client: Optional[redis.Redis] = None
        
        # 缓存TTL配置（遵循指南1.2.3）
        self.cache_ttl = {
            "user_history": settings.CACHE_TTL_USER_HISTORY,  # 5分钟
            "question_bank": settings.CACHE_TTL_QUESTION_BANK,  # 30分钟
            "config": settings.CACHE_TTL_CONFIG,  # 10分钟
            "daily_checkin": 3600,  # 1小时
        }
    
    async def initialize(self):
        """初始化Redis连接"""
        if not self.redis_url:
            logger.warning("Redis URL未配置，使用内存模拟")
            return
        
        try:
            self.pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                decode_responses=True,
            )
            
            self.redis_client = redis.Redis(connection_pool=self.pool)
            
            # 测试连接
            await self.redis_client.ping()
            logger.info("Redis连接成功")
            
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self.redis_client = None
    
    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
        if self.pool:
            await self.pool.disconnect()
    
    async def get_client(self) -> Optional[redis.Redis]:
        """获取Redis客户端"""
        if not self.redis_client:
            await self.initialize()
        return self.redis_client
    
    # 任务队列方法（遵循指南2.3.2）
    
    async def submit_task(self, task_data: Dict[str, Any], priority: str = "normal") -> str:
        """
        提交任务到队列
        
        Args:
            task_data: 任务数据
            priority: 任务优先级（high/normal）
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        # 任务元数据
        task_meta = {
            "id": task_id,
            "type": task_data.get("type", "grade"),
            "priority": priority,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "retry_count": 0,
            "max_retries": 3,
        }
        
        client = await self.get_client()
        if not client:
            logger.error("Redis不可用，无法提交任务")
            return task_id
        
        try:
            # 存储任务数据
            await client.setex(
                f"task:{task_id}:data",
                3600,  # 1小时过期
                json.dumps(task_data, ensure_ascii=False)
            )
            
            # 存储任务元数据
            await client.setex(
                f"task:{task_id}:meta",
                3600,
                json.dumps(task_meta, ensure_ascii=False)
            )
            
            # 根据优先级放入不同队列
            queue_name = f"{self.task_queue_name}:{priority}"
            await client.lpush(queue_name, task_id)
            
            logger.info(f"任务提交成功: {task_id}, 优先级: {priority}")
            return task_id
            
        except Exception as e:
            logger.error(f"提交任务失败: {e}")
            return task_id
    
    async def get_next_task(self, priority: str = "normal") -> Optional[Dict[str, Any]]:
        """
        获取下一个任务
        
        Args:
            priority: 任务优先级
            
        Returns:
            任务数据，包含data和meta
        """
        client = await self.get_client()
        if not client:
            return None
        
        try:
            # 从队列获取任务ID
            queue_name = f"{self.task_queue_name}:{priority}"
            task_id = await client.rpop(queue_name)
            
            if not task_id:
                # 尝试从另一个优先级队列获取
                other_priority = "high" if priority == "normal" else "normal"
                other_queue = f"{self.task_queue_name}:{other_priority}"
                task_id = await client.rpop(other_queue)
                
                if not task_id:
                    return None
            
            # 获取任务数据
            task_data_key = f"task:{task_id}:data"
            task_meta_key = f"task:{task_id}:meta"
            
            task_data_str = await client.get(task_data_key)
            task_meta_str = await client.get(task_meta_key)
            
            if not task_data_str or not task_meta_str:
                logger.warning(f"任务数据缺失: {task_id}")
                return None
            
            task_data = json.loads(task_data_str)
            task_meta = json.loads(task_meta_str)
            
            # 更新任务状态
            task_meta["status"] = "processing"
            task_meta["started_at"] = datetime.now().isoformat()
            
            await client.setex(
                task_meta_key,
                3600,
                json.dumps(task_meta, ensure_ascii=False)
            )
            
            return {
                "id": task_id,
                "data": task_data,
                "meta": task_meta,
            }
            
        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            return None
    
    async def update_task_status(self, task_id: str, status: str, result: Optional[Dict] = None):
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 状态（processing/completed/failed）
            result: 任务结果
        """
        client = await self.get_client()
        if not client:
            return
        
        try:
            task_meta_key = f"task:{task_id}:meta"
            task_meta_str = await client.get(task_meta_key)
            
            if not task_meta_str:
                logger.warning(f"任务元数据不存在: {task_id}")
                return
            
            task_meta = json.loads(task_meta_str)
            task_meta["status"] = status
            task_meta["updated_at"] = datetime.now().isoformat()
            
            if status == "completed":
                task_meta["completed_at"] = datetime.now().isoformat()
            elif status == "failed":
                task_meta["failed_at"] = datetime.now().isoformat()
                # 重试逻辑
                retry_count = task_meta.get("retry_count", 0) + 1
                task_meta["retry_count"] = retry_count
                
                if retry_count < task_meta.get("max_retries", 3):
                    # 重新放入队列
                    queue_name = f"{self.task_queue_name}:{task_meta.get('priority', 'normal')}"
                    await client.lpush(queue_name, task_id)
                    logger.info(f"任务重试: {task_id}, 重试次数: {retry_count}")
            
            # 保存更新后的元数据
            await client.setex(
                task_meta_key,
                3600,
                json.dumps(task_meta, ensure_ascii=False)
            )
            
            # 保存结果
            if result:
                result_key = f"task:{task_id}:result"
                await client.setex(
                    result_key,
                    self.result_ttl,
                    json.dumps(result, ensure_ascii=False)
                )
            
            logger.info(f"任务状态更新: {task_id} -> {status}")
            
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
    
    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务结果
        """
        client = await self.get_client()
        if not client:
            return None
        
        try:
            result_key = f"task:{task_id}:result"
            result_str = await client.get(result_key)
            
            if result_str:
                return json.loads(result_str)
            
            # 检查任务状态
            meta_key = f"task:{task_id}:meta"
            meta_str = await client.get(meta_key)
            
            if meta_str:
                meta = json.loads(meta_str)
                return {
                    "status": meta.get("status", "unknown"),
                    "meta": meta,
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            return None
    
    # 缓存方法（遵循指南1.2.3）
    
    async def get_with_cache(self, cache_key: str, cache_type: str = "user_history") -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            cache_key: 缓存键
            cache_type: 缓存类型
            
        Returns:
            缓存数据
        """
        client = await self.get_client()
        if not client:
            return None
        
        try:
            full_key = f"cache:{cache_type}:{cache_key}"
            cached = await client.get(full_key)
            
            if cached:
                logger.debug(f"缓存命中: {full_key}")
                return json.loads(cached)
            
            return None
            
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None
    
    async def set_with_cache(self, cache_key: str, data: Any, cache_type: str = "user_history"):
        """
        设置缓存数据
        
        Args:
            cache_key: 缓存键
            data: 缓存数据
            cache_type: 缓存类型
        """
        client = await self.get_client()
        if not client:
            return
        
        try:
            full_key = f"cache:{cache_type}:{cache_key}"
            ttl = self.cache_ttl.get(cache_type, 300)
            
            await client.setex(
                full_key,
                ttl,
                json.dumps(data, ensure_ascii=False)
            )
            
            logger.debug(f"缓存设置: {full_key}, TTL: {ttl}秒")
            
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
    
    async def delete_cache(self, cache_key: str, cache_type: str = "user_history"):
        """
        删除缓存数据
        
        Args:
            cache_key: 缓存键
            cache_type: 缓存类型
        """
        client = await self.get_client()
        if not client:
            return
        
        try:
            full_key = f"cache:{cache_type}:{cache_key}"
            await client.delete(full_key)
            logger.debug(f"缓存删除: {full_key}")
            
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
    
    async def clear_cache_by_type(self, cache_type: str):
        """
        按类型清除缓存
        
        Args:
            cache_type: 缓存类型
        """
        client = await self.get_client()
        if not client:
            return
        
        try:
            pattern = f"cache:{cache_type}:*"
            keys = await client.keys(pattern)
            
            if keys:
                await client.delete(*keys)
                logger.info(f"清除缓存类型: {cache_type}, 数量: {len(keys)}")
            
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
    
    # 队列监控方法
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        获取队列统计信息
        
        Returns:
            队列统计信息
        """
        client = await self.get_client()
        if not client:
            return {"error": "Redis不可用"}
        
        try:
            stats = {}
            
            for priority in ["high", "normal"]:
                queue_name = f"{self.task_queue_name}:{priority}"
                queue_length = await client.llen(queue_name)
                stats[f"{priority}_queue_length"] = queue_length
            
            # 获取处理中的任务数量
            processing_tasks = 0
            task_keys = await client.keys("task:*:meta")
            
            for key in task_keys:
                meta_str = await client.get(key)
                if meta_str:
                    meta = json.loads(meta_str)
                    if meta.get("status") == "processing":
                        processing_tasks += 1
            
            stats["processing_tasks"] = processing_tasks
            stats["total_cached_keys"] = len(await client.keys("*"))
            
            return stats
            
        except Exception as e:
            logger.error(f"获取队列统计失败: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            Redis是否可用
        """
        client = await self.get_client()
        if not client:
            return False
        
        try:
            await client.ping()
            return True
        except:
            return False


# 创建全局实例
redis_service = RedisService()

# 导出
__all__ = ["RedisService", "redis_service"]