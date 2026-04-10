"""
Cloudflare R2服务 - 实现大字段存储优化
遵循技术升级指南1.2.2和2.2.2
"""

import json
import boto3
import logging
from typing import Optional, Dict, Any, BinaryIO, List
from datetime import datetime
from botocore.config import Config
from botocore.exceptions import ClientError

from backend.app.config import settings

logger = logging.getLogger(__name__)


class CloudflareR2Service:
    """Cloudflare R2存储服务，用于存储大字段数据"""
    
    def __init__(self):
        self.account_id = settings.CLOUDFLARE_R2_ACCOUNT_ID
        self.access_key_id = settings.CLOUDFLARE_R2_ACCESS_KEY_ID
        self.secret_access_key = settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY
        self.bucket_name = settings.CLOUDFLARE_R2_BUCKET_NAME
        self.public_url = settings.CLOUDFLARE_R2_PUBLIC_URL
        
        self.s3_client = None
        self.resource = None
        
        # 存储路径配置
        self.storage_paths = {
            "results": "results",  # 评分结果
            "analyses": "analyses",  # 分析报告
            "growth_data": "growth",  # 成长数据
            "user_data": "users",  # 用户数据
            "temp": "temp",  # 临时文件
        }
    
    def initialize(self):
        """初始化R2客户端"""
        if not all([self.account_id, self.access_key_id, self.secret_access_key, self.bucket_name]):
            logger.warning("R2配置不完整，跳过初始化")
            return
        
        try:
            # 创建S3兼容客户端
            self.s3_client = boto3.client(
                's3',
                endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                config=Config(
                    s3={'addressing_style': 'virtual'},
                    signature_version='s3v4'
                )
            )
            
            self.resource = boto3.resource(
                's3',
                endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                config=Config(
                    s3={'addressing_style': 'virtual'},
                    signature_version='s3v4'
                )
            )
            
            # 测试连接
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"R2连接成功，存储桶: {self.bucket_name}")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.warning(f"存储桶不存在: {self.bucket_name}")
            else:
                logger.error(f"R2连接失败: {e}")
            self.s3_client = None
            self.resource = None
        except Exception as e:
            logger.error(f"R2初始化失败: {e}")
            self.s3_client = None
            self.resource = None
    
    def get_client(self):
        """获取S3客户端"""
        if not self.s3_client:
            self.initialize()
        return self.s3_client
    
    def get_resource(self):
        """获取S3资源"""
        if not self.resource:
            self.initialize()
        return self.resource
    
    async def upload_json(self, filename: str, content: Dict[str, Any], path_type: str = "results") -> Optional[str]:
        """
        上传JSON数据到R2
        
        Args:
            filename: 文件名（不含路径）
            content: JSON内容
            path_type: 存储路径类型
            
        Returns:
            文件URL或None
        """
        client = self.get_client()
        if not client:
            logger.error("R2客户端不可用")
            return None
        
        try:
            # 构建完整路径
            path_prefix = self.storage_paths.get(path_type, "others")
            object_key = f"{path_prefix}/{filename}"
            
            # 转换为JSON字符串
            json_str = json.dumps(content, ensure_ascii=False, indent=2)
            
            # 上传到R2
            client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=json_str.encode('utf-8'),
                ContentType='application/json',
                ContentDisposition='inline'
            )
            
            # 生成URL
            if self.public_url:
                url = f"{self.public_url.rstrip('/')}/{object_key}"
            else:
                url = f"https://{self.account_id}.r2.cloudflarestorage.com/{self.bucket_name}/{object_key}"
            
            logger.info(f"JSON上传成功: {object_key}, 大小: {len(json_str)}字节")
            return url
            
        except Exception as e:
            logger.error(f"上传JSON失败: {e}")
            return None
    
    async def download_json(self, url: str) -> Optional[Dict[str, Any]]:
        """
        从R2下载JSON数据
        
        Args:
            url: 文件URL
            
        Returns:
            JSON内容或None
        """
        client = self.get_client()
        if not client:
            logger.error("R2客户端不可用")
            return None
        
        try:
            # 从URL提取对象键
            if self.public_url and url.startswith(self.public_url):
                object_key = url[len(self.public_url.rstrip('/') + '/'):]
            elif f"r2.cloudflarestorage.com/{self.bucket_name}/" in url:
                parts = url.split(f"r2.cloudflarestorage.com/{self.bucket_name}/")
                object_key = parts[1] if len(parts) > 1 else ""
            else:
                logger.error(f"无法解析R2 URL: {url}")
                return None
            
            if not object_key:
                logger.error("无法提取对象键")
                return None
            
            # 下载对象
            response = client.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            # 读取内容
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            
            logger.debug(f"JSON下载成功: {object_key}")
            return data
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.error(f"文件不存在: {url}")
            else:
                logger.error(f"下载JSON失败: {e}")
            return None
        except Exception as e:
            logger.error(f"下载JSON失败: {e}")
            return None
    
    async def upload_file(self, file_path: str, filename: Optional[str] = None, path_type: str = "temp") -> Optional[str]:
        """
        上传文件到R2
        
        Args:
            file_path: 本地文件路径
            filename: 目标文件名（可选）
            path_type: 存储路径类型
            
        Returns:
            文件URL或None
        """
        client = self.get_client()
        if not client:
            logger.error("R2客户端不可用")
            return None
        
        try:
            import os
            from pathlib import Path
            
            # 确定文件名
            if not filename:
                filename = Path(file_path).name
            
            # 构建完整路径
            path_prefix = self.storage_paths.get(path_type, "others")
            object_key = f"{path_prefix}/{filename}"
            
            # 上传文件
            with open(file_path, 'rb') as file:
                client.upload_fileobj(
                    file,
                    self.bucket_name,
                    object_key
                )
            
            # 生成URL
            if self.public_url:
                url = f"{self.public_url.rstrip('/')}/{object_key}"
            else:
                url = f"https://{self.account_id}.r2.cloudflarestorage.com/{self.bucket_name}/{object_key}"
            
            file_size = os.path.getsize(file_path)
            logger.info(f"文件上传成功: {object_key}, 大小: {file_size}字节")
            return url
            
        except Exception as e:
            logger.error(f"上传文件失败: {e}")
            return None
    
    async def download_file(self, url: str, local_path: str) -> bool:
        """
        从R2下载文件
        
        Args:
            url: 文件URL
            local_path: 本地保存路径
            
        Returns:
            是否成功
        """
        client = self.get_client()
        if not client:
            logger.error("R2客户端不可用")
            return False
        
        try:
            # 从URL提取对象键
            if self.public_url and url.startswith(self.public_url):
                object_key = url[len(self.public_url.rstrip('/') + '/'):]
            elif f"r2.cloudflarestorage.com/{self.bucket_name}/" in url:
                parts = url.split(f"r2.cloudflarestorage.com/{self.bucket_name}/")
                object_key = parts[1] if len(parts) > 1 else ""
            else:
                logger.error(f"无法解析R2 URL: {url}")
                return False
            
            if not object_key:
                logger.error("无法提取对象键")
                return False
            
            # 下载文件
            with open(local_path, 'wb') as file:
                client.download_fileobj(
                    self.bucket_name,
                    object_key,
                    file
                )
            
            logger.info(f"文件下载成功: {object_key} -> {local_path}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.error(f"文件不存在: {url}")
            else:
                logger.error(f"下载文件失败: {e}")
            return False
        except Exception as e:
            logger.error(f"下载文件失败: {e}")
            return False
    
    async def delete_file(self, url: str) -> bool:
        """
        删除R2中的文件
        
        Args:
            url: 文件URL
            
        Returns:
            是否成功
        """
        client = self.get_client()
        if not client:
            logger.error("R2客户端不可用")
            return False
        
        try:
            # 从URL提取对象键
            if self.public_url and url.startswith(self.public_url):
                object_key = url[len(self.public_url.rstrip('/') + '/'):]
            elif f"r2.cloudflarestorage.com/{self.bucket_name}/" in url:
                parts = url.split(f"r2.cloudflarestorage.com/{self.bucket_name}/")
                object_key = parts[1] if len(parts) > 1 else ""
            else:
                logger.error(f"无法解析R2 URL: {url}")
                return False
            
            if not object_key:
                logger.error("无法提取对象键")
                return False
            
            # 删除对象
            client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"文件删除成功: {object_key}")
            return True
            
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return False
    
    async def list_files(self, path_type: str = "results", prefix: str = "") -> List[Dict[str, Any]]:
        """
        列出R2中的文件
        
        Args:
            path_type: 存储路径类型
            prefix: 文件名前缀
            
        Returns:
            文件列表
        """
        client = self.get_client()
        if not client:
            logger.error("R2客户端不可用")
            return []
        
        try:
            path_prefix = self.storage_paths.get(path_type, "others")
            full_prefix = f"{path_prefix}/{prefix}" if prefix else path_prefix
            
            response = client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=full_prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                file_info = {
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat() if 'LastModified' in obj else None,
                }
                
                # 生成URL
                if self.public_url:
                    file_info['url'] = f"{self.public_url.rstrip('/')}/{obj['Key']}"
                else:
                    file_info['url'] = f"https://{self.account_id}.r2.cloudflarestorage.com/{self.bucket_name}/{obj['Key']}"
                
                files.append(file_info)
            
            logger.debug(f"列出文件: {full_prefix}, 数量: {len(files)}")
            return files
            
        except Exception as e:
            logger.error(f"列出文件失败: {e}")
            return []
    
    async def get_file_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            url: 文件URL
            
        Returns:
            文件信息或None
        """
        client = self.get_client()
        if not client:
            logger.error("R2客户端不可用")
            return None
        
        try:
            # 从URL提取对象键
            if self.public_url and url.startswith(self.public_url):
                object_key = url[len(self.public_url.rstrip('/') + '/'):]
            elif f"r2.cloudflarestorage.com/{self.bucket_name}/" in url:
                parts = url.split(f"r2.cloudflarestorage.com/{self.bucket_name}/")
                object_key = parts[1] if len(parts) > 1 else ""
            else:
                logger.error(f"无法解析R2 URL: {url}")
                return None
            
            if not object_key:
                logger.error("无法提取对象键")
                return None
            
            # 获取对象信息
            response = client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            info = {
                'key': object_key,
                'size': response['ContentLength'],
                'content_type': response.get('ContentType', ''),
                'last_modified': response['LastModified'].isoformat() if 'LastModified' in response else None,
                'etag': response.get('ETag', ''),
            }
            
            # 生成URL
            if self.public_url:
                info['url'] = f"{self.public_url.rstrip('/')}/{object_key}"
            else:
                info['url'] = f"https://{self.account_id}.r2.cloudflarestorage.com/{self.bucket_name}/{object_key}"
            
            return info
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.error(f"文件不存在: {url}")
            else:
                logger.error(f"获取文件信息失败: {e}")
            return None
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return None
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            R2是否可用
        """
        client = self.get_client()
        if not client:
            return False
        
        try:
            client.head_bucket(Bucket=self.bucket_name)
            return True
        except:
            return False


# 创建全局实例
cloudflare_r2_service = CloudflareR2Service()

# 导出
__all__ = ["CloudflareR2Service", "cloudflare_r2_service"]