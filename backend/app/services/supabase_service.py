"""
Supabase服务 - 实现数据交换优化和分页查询
遵循技术升级指南1.2.1和2.5.1
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from supabase import create_client, Client

from backend.app.config import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """优化的Supabase服务，实现分页查询和字段筛选"""
    
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.supabase_client: Optional[Client] = None
        
        # 查询优化配置
        self.default_page_size = settings.QUERY_PAGE_SIZE
        self.max_page_size = 100
        
        # 字段映射：避免SELECT *，只选择必要字段
        self.field_mappings = {
            "user_results": [
                "id", "user_id", "task_id", "total_score", 
                "summary", "created_at", "updated_at", "r2_url"
            ],
            "activation_codes": [
                "id", "code", "user_id", "is_used", 
                "used_at", "expires_at", "created_at"
            ],
            "user_profiles": [
                "id", "user_id", "name", "email", 
                "exam_type", "target_score", "created_at"
            ],
        }
    
    async def initialize(self):
        """初始化Supabase客户端"""
        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase配置缺失")
            return
        
        try:
            # 使用事务模式URL（遵循指南2.5.1）
            transaction_url = settings.supabase_transaction_url
            
            self.supabase_client = create_client(
                transaction_url or self.supabase_url,
                self.supabase_key
            )
            
            # 测试连接
            test_result = self.supabase_client.table("user_results").select("count", count="exact").limit(1).execute()
            logger.info(f"Supabase连接成功，现有记录数: {test_result.count}")
            
        except Exception as e:
            logger.error(f"Supabase连接失败: {e}")
            self.supabase_client = None
    
    def get_client(self) -> Optional[Client]:
        """获取Supabase客户端"""
        if not self.supabase_client:
            # 同步初始化（注意：Supabase客户端是同步的）
            import asyncio
            asyncio.run(self.initialize())
        return self.supabase_client
    
    # 用户结果管理（遵循指南1.2.2）
    
    async def save_user_result(
        self,
        user_id: int,
        task_id: str,
        total_score: float,
        summary: str,
        full_result: Optional[Dict] = None,
        r2_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        保存用户结果（优化版：只存摘要，大结果存R2）
        
        Args:
            user_id: 用户ID
            task_id: 任务ID
            total_score: 总分
            summary: 结果摘要（200字符以内）
            full_result: 完整结果（可选，建议存R2）
            r2_url: R2存储URL
            
        Returns:
            保存的记录
        """
        client = self.get_client()
        if not client:
            logger.error("Supabase客户端不可用")
            return None
        
        try:
            # 准备数据
            data = {
                "user_id": user_id,
                "task_id": task_id,
                "total_score": total_score,
                "summary": summary[:200],  # 确保摘要不超过200字符
                "r2_url": r2_url,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            
            # 如果有完整结果且不大，可以存为JSON（< 10KB）
            if full_result and len(json.dumps(full_result)) < 10240:  # 10KB
                data["full_result"] = full_result
            
            # 插入数据
            result = client.table("user_results").insert(data).execute()
            
            if result.data:
                logger.info(f"用户结果保存成功: user_id={user_id}, task_id={task_id}, score={total_score}")
                return result.data[0]
            else:
                logger.error("保存用户结果失败：无返回数据")
                return None
                
        except Exception as e:
            logger.error(f"保存用户结果失败: {e}")
            return None
    
    async def get_user_results(
        self,
        user_id: int,
        page: int = 0,
        limit: Optional[int] = None,
        order_by: str = "created_at",
        descending: bool = True
    ) -> Dict[str, Any]:
        """
        获取用户结果列表（分页优化）
        
        Args:
            user_id: 用户ID
            page: 页码（从0开始）
            limit: 每页数量
            order_by: 排序字段
            descending: 是否降序
            
        Returns:
            分页结果
        """
        client = self.get_client()
        if not client:
            return {"error": "Supabase不可用", "data": [], "total": 0}
        
        try:
            # 设置分页参数
            page_size = limit or self.default_page_size
            if page_size > self.max_page_size:
                page_size = self.max_page_size
            
            start_idx = page * page_size
            end_idx = start_idx + page_size - 1
            
            # 构建查询（只选择必要字段）
            query = client.table("user_results") \
                .select(*self.field_mappings["user_results"]) \
                .eq("user_id", user_id)
            
            # 排序
            if descending:
                query = query.order(order_by, desc=True)
            else:
                query = query.order(order_by)
            
            # 分页
            query = query.range(start_idx, end_idx)
            
            # 执行查询
            result = query.execute()
            
            # 获取总数
            count_query = client.table("user_results") \
                .select("id", count="exact") \
                .eq("user_id", user_id)
            
            count_result = count_query.execute()
            total_count = count_result.count or 0
            
            logger.debug(f"获取用户结果: user_id={user_id}, page={page}, limit={page_size}, total={total_count}")
            
            return {
                "data": result.data,
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "has_more": (start_idx + page_size) < total_count,
            }
            
        except Exception as e:
            logger.error(f"获取用户结果失败: {e}")
            return {"error": str(e), "data": [], "total": 0}
    
    async def get_user_result_by_task_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        根据任务ID获取用户结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            用户结果
        """
        client = self.get_client()
        if not client:
            return None
        
        try:
            result = client.table("user_results") \
                .select(*self.field_mappings["user_results"]) \
                .eq("task_id", task_id) \
                .limit(1) \
                .execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"获取用户结果失败: {e}")
            return None
    
    # 激活码管理
    
    async def validate_activation_code(self, code: str, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        验证激活码
        
        Args:
            code: 激活码
            user_id: 用户ID
            
        Returns:
            (是否有效, 错误信息)
        """
        client = self.get_client()
        if not client:
            return False, "数据库连接失败"
        
        try:
            # 查询激活码
            result = client.table("activation_codes") \
                .select(*self.field_mappings["activation_codes"]) \
                .eq("code", code) \
                .limit(1) \
                .execute()
            
            if not result.data:
                return False, "激活码不存在"
            
            activation_code = result.data[0]
            
            # 检查是否已使用
            if activation_code.get("is_used"):
                used_user_id = activation_code.get("user_id")
                if used_user_id == user_id:
                    return True, "激活码已由当前用户使用"
                else:
                    return False, "激活码已被其他用户使用"
            
            # 检查是否过期
            expires_at = activation_code.get("expires_at")
            if expires_at:
                expires_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if datetime.now(expires_date.tzinfo) > expires_date:
                    return False, "激活码已过期"
            
            # 标记为已使用
            update_data = {
                "is_used": True,
                "user_id": user_id,
                "used_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            
            update_result = client.table("activation_codes") \
                .update(update_data) \
                .eq("id", activation_code["id"]) \
                .execute()
            
            if update_result.data:
                logger.info(f"激活码验证成功: code={code}, user_id={user_id}")
                return True, None
            else:
                return False, "激活码更新失败"
                
        except Exception as e:
            logger.error(f"验证激活码失败: {e}")
            return False, f"验证过程中出现错误: {str(e)}"
    
    async def create_activation_codes(self, count: int, expires_days: int = 30) -> List[str]:
        """
        批量创建激活码
        
        Args:
            count: 激活码数量
            expires_days: 过期天数
            
        Returns:
            创建的激活码列表
        """
        client = self.get_client()
        if not client:
            return []
        
        try:
            import secrets
            import string
            
            codes = []
            code_data = []
            
            now = datetime.now()
            expires_at = now + timedelta(days=expires_days)
            
            for _ in range(count):
                # 生成随机激活码（8位字母数字）
                code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                codes.append(code)
                
                code_data.append({
                    "code": code,
                    "is_used": False,
                    "expires_at": expires_at.isoformat(),
                    "created_at": now.isoformat(),
                })
            
            # 批量插入
            result = client.table("activation_codes").insert(code_data).execute()
            
            if result.data:
                logger.info(f"创建激活码成功: 数量={count}")
                return codes
            else:
                logger.error("创建激活码失败：无返回数据")
                return []
                
        except Exception as e:
            logger.error(f"创建激活码失败: {e}")
            return []
    
    # 用户档案管理
    
    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取用户档案
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户档案
        """
        client = self.get_client()
        if not client:
            return None
        
        try:
            result = client.table("user_profiles") \
                .select(*self.field_mappings["user_profiles"]) \
                .eq("user_id", user_id) \
                .limit(1) \
                .execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"获取用户档案失败: {e}")
            return None
    
    async def update_user_profile(self, user_id: int, profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        更新用户档案
        
        Args:
            user_id: 用户ID
            profile_data: 档案数据
            
        Returns:
            更新后的档案
        """
        client = self.get_client()
        if not client:
            return None
        
        try:
            # 检查是否存在
            existing = await self.get_user_profile(user_id)
            
            profile_data["user_id"] = user_id
            profile_data["updated_at"] = datetime.now().isoformat()
            
            if existing:
                # 更新
                result = client.table("user_profiles") \
                    .update(profile_data) \
                    .eq("id", existing["id"]) \
                    .execute()
            else:
                # 创建
                profile_data["created_at"] = datetime.now().isoformat()
                result = client.table("user_profiles") \
                    .insert(profile_data) \
                    .execute()
            
            if result.data:
                logger.info(f"用户档案更新成功: user_id={user_id}")
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"更新用户档案失败: {e}")
            return None
    
    # 统计和监控
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """
        获取系统统计信息
        
        Returns:
            系统统计
        """
        client = self.get_client()
        if not client:
            return {"error": "Supabase不可用"}
        
        try:
            stats = {}
            
            # 用户结果统计
            result_count = client.table("user_results") \
                .select("id", count="exact") \
                .execute()
            stats["total_results"] = result_count.count or 0
            
            # 激活码统计
            code_count = client.table("activation_codes") \
                .select("id", count="exact") \
                .execute()
            stats["total_codes"] = code_count.count or 0
            
            used_code_count = client.table("activation_codes") \
                .select("id", count="exact") \
                .eq("is_used", True) \
                .execute()
            stats["used_codes"] = used_code_count.count or 0
            
            # 用户统计
            user_count = client.table("user_profiles") \
                .select("id", count="exact") \
                .execute()
            stats["total_users"] = user_count.count or 0
            
            # 今日新增
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_results = client.table("user_results") \
                .select("id", count="exact") \
                .gte("created_at", today_start.isoformat()) \
                .execute()
            stats["today_results"] = today_results.count or 0
            
            return stats
            
        except Exception as e:
            logger.error(f"获取系统统计失败: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            Supabase是否可用
        """
        client = self.get_client()
        if not client:
            return False
        
        try:
            # 简单查询测试
            result = client.table("user_results").select("id").limit(1).execute()
            return True
        except:
            return False


# 创建全局实例
supabase_service = SupabaseService()

# 导出
__all__ = ["SupabaseService", "supabase_service"]