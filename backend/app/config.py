"""
配置文件 - 遵循技术升级指南的优化配置
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    APP_NAME: str = Field(default="申论智能判卷系统", description="应用名称")
    DEBUG: bool = Field(default=False, description="调试模式")
    ENVIRONMENT: str = Field(default="production", description="环境")
    LOG_TO_FILE: bool = Field(default=False, description="是否记录日志到文件")
    
    # 内存优化配置（遵循指南1.1.1）
    UVICORN_WORKERS: int = Field(default=1, description="Uvicorn workers数量，512MB内存下设为1")
    UVICORN_LIMIT_CONCURRENCY: int = Field(default=15, description="限制并发连接数")
    UVICORN_TIMEOUT_KEEP_ALIVE: int = Field(default=65, description="连接保持超时时间")
    
    # 内存监控配置
    MEMORY_WARNING_THRESHOLD_MB: int = Field(default=400, description="内存警告阈值(MB)")
    MEMORY_CRITICAL_THRESHOLD_MB: int = Field(default=450, description="内存临界阈值(MB)")
    PDF_MAX_SIZE_MB: int = Field(default=10, description="PDF最大大小(MB)")
    PDF_CHUNK_SIZE_KB: int = Field(default=1024, description="PDF分块大小(KB)")
    
    # 上下文长度控制（遵循指南1.1.3）
    DEEPSEEK_MAX_CONTEXT_LENGTH: int = Field(default=8000, description="DeepSeek最大上下文长度")
    MATERIAL_SUMMARY_LENGTH: int = Field(default=4000, description="材料摘要长度")
    
    # CORS配置
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="CORS允许的源，逗号分隔"
    )
    
    # Supabase配置
    SUPABASE_URL: Optional[str] = Field(default=None, description="Supabase URL")
    SUPABASE_KEY: Optional[str] = Field(default=None, description="Supabase密钥")
    SUPABASE_POOL_SIZE: int = Field(default=10, description="连接池大小")
    SUPABASE_MAX_OVERFLOW: int = Field(default=5, description="最大溢出连接")
    SUPABASE_POOL_TIMEOUT: int = Field(default=30, description="连接超时")
    SUPABASE_POOL_RECYCLE: int = Field(default=3600, description="连接回收时间")
    
    # Redis配置
    REDIS_URL: Optional[str] = Field(default=None, description="Redis URL")
    REDIS_MAX_CONNECTIONS: int = Field(default=20, description="Redis最大连接数")
    REDIS_TASK_QUEUE_NAME: str = Field(default="grade_tasks", description="任务队列名称")
    REDIS_RESULT_TTL: int = Field(default=86400, description="结果缓存TTL(秒)")
    
    # DeepSeek配置
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None, description="DeepSeek API密钥")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com", description="DeepSeek API基础URL")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat", description="DeepSeek模型")
    DEEPSEEK_MAX_TOKENS: int = Field(default=2000, description="最大生成token数")
    DEEPSEEK_TEMPERATURE: float = Field(default=0.7, description="温度参数")
    
    # Cloudflare R2配置（遵循指南1.2.2）
    CLOUDFLARE_R2_ACCOUNT_ID: Optional[str] = Field(default=None, description="Cloudflare R2账户ID")
    CLOUDFLARE_R2_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="R2访问密钥ID")
    CLOUDFLARE_R2_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="R2秘密访问密钥")
    CLOUDFLARE_R2_BUCKET_NAME: str = Field(default="shenlun-ai-results", description="R2存储桶名称")
    CLOUDFLARE_R2_PUBLIC_URL: Optional[str] = Field(default=None, description="R2公共URL")
    
    # 文件上传配置
    UPLOAD_DIR: str = Field(default="uploads", description="上传文件目录")
    MAX_UPLOAD_SIZE: int = Field(default=20 * 1024 * 1024, description="最大上传大小(20MB)")
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".pdf", ".png", ".jpg", ".jpeg"],
        description="允许的文件扩展名"
    )
    
    # 安全配置
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="密钥")
    ALGORITHM: str = Field(default="HS256", description="JWT算法")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="访问token过期时间")
    
    # 性能配置
    QUERY_PAGE_SIZE: int = Field(default=20, description="查询分页大小")
    CACHE_TTL_USER_HISTORY: int = Field(default=300, description="用户历史缓存TTL(秒)")
    CACHE_TTL_QUESTION_BANK: int = Field(default=1800, description="题库缓存TTL(秒)")
    CACHE_TTL_CONFIG: int = Field(default=600, description="配置缓存TTL(秒)")
    
    # 监控配置
    MONITORING_INTERVAL: int = Field(default=60, description="监控间隔(秒)")
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @validator("UVICORN_WORKERS")
    def validate_workers(cls, v):
        """验证workers数量"""
        if v < 1:
            return 1
        return v
    

    
    @property
    def supabase_transaction_url(self) -> Optional[str]:
        """获取Supabase事务模式URL（遵循指南2.5.1）"""
        if self.SUPABASE_URL and "supabase.co" in self.SUPABASE_URL:
            return self.SUPABASE_URL.replace("5432", "6543")
        return self.SUPABASE_URL


# 创建全局配置实例
settings = Settings()

# 导出配置
__all__ = ["settings"]