"""
Worker服务 - 后台任务处理
遵循技术升级指南1.1.3和2.1.2
"""

import os
import sys
import asyncio
import logging
import signal
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app.config import settings
from backend.app.services.redis_service import redis_service
from backend.app.services.supabase_service import supabase_service
from backend.app.services.deepseek_client import deepseek_client
from backend.app.services.cloudflare_r2_service import cloudflare_r2_service
from backend.app.services.monitoring_service import monitoring_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("worker.log"),
    ]
)
logger = logging.getLogger(__name__)


class WorkerService:
    """后台任务处理服务"""
    
    def __init__(self):
        self.is_running = False
        self.processing_tasks = set()
        self.shutdown_event = asyncio.Event()
        
        # 配置
        self.poll_interval = settings.WORKER_POLL_INTERVAL
        self.max_concurrent_tasks = settings.WORKER_MAX_CONCURRENT_TASKS
        self.task_timeout = settings.WORKER_TASK_TIMEOUT
        
        # 统计信息
        self.stats = {
            "started_at": None,
            "tasks_processed": 0,
            "tasks_failed": 0,
            "tasks_succeeded": 0,
            "last_task_time": None,
        }
    
    async def initialize(self):
        """初始化服务"""
        logger.info("Worker服务初始化中...")
        
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
            
            # 设置信号处理
            self._setup_signal_handlers()
            
            self.stats["started_at"] = datetime.now().isoformat()
            logger.info("Worker服务初始化完成")
            
        except Exception as e:
            logger.error(f"Worker服务初始化失败: {e}")
            raise
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        logger.info(f"收到信号 {signum}，准备关闭...")
        self.shutdown_event.set()
    
    async def run(self):
        """运行Worker服务"""
        logger.info("Worker服务启动...")
        logger.info(f"配置: 最大并发任务={self.max_concurrent_tasks}, 轮询间隔={self.poll_interval}秒")
        
        self.is_running = True
        
        try:
            # 主循环
            while not self.shutdown_event.is_set():
                try:
                    # 检查当前处理中的任务数量
                    current_tasks = len(self.processing_tasks)
                    
                    if current_tasks < self.max_concurrent_tasks:
                        # 可以处理更多任务
                        available_slots = self.max_concurrent_tasks - current_tasks
                        
                        for _ in range(available_slots):
                            # 从队列获取任务
                            task = await redis_service.get_next_task()
                            
                            if task:
                                # 启动任务处理
                                task_id = task.get("task_id")
                                task_data = task.get("data", {})
                                
                                logger.info(f"开始处理任务: {task_id}")
                                
                                # 创建任务处理协程
                                task_coro = self._process_task(task_id, task_data)
                                task_handle = asyncio.create_task(task_coro)
                                
                                # 添加到处理中集合
                                self.processing_tasks.add(task_handle)
                                
                                # 设置回调
                                task_handle.add_done_callback(
                                    lambda f, th=task_handle: self._task_done_callback(f, th)
                                )
                    
                    # 等待一段时间
                    await asyncio.sleep(self.poll_interval)
                    
                    # 定期记录状态
                    if self.stats["tasks_processed"] % 10 == 0:
                        self._log_status()
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Worker主循环出错: {e}")
                    await asyncio.sleep(self.poll_interval)
            
            # 等待所有任务完成
            logger.info("等待处理中的任务完成...")
            if self.processing_tasks:
                await asyncio.wait(self.processing_tasks, timeout=30)
            
            logger.info("Worker服务正常关闭")
            
        except Exception as e:
            logger.error(f"Worker服务运行出错: {e}")
            raise
        
        finally:
            await self.shutdown()
    
    async def _process_task(self, task_id: str, task_data: dict):
        """处理单个任务"""
        try:
            # 更新任务状态为处理中
            await redis_service.update_task_status(task_id, "processing")
            
            # 记录开始时间
            start_time = datetime.now()
            
            # 根据任务类型处理
            task_type = task_data.get("type", "unknown")
            
            if task_type == "grade":
                result = await self._process_grade_task(task_id, task_data)
            else:
                result = {"error": f"未知任务类型: {task_type}"}
                await redis_service.update_task_status(task_id, "failed", result)
                self.stats["tasks_failed"] += 1
                return
            
            # 记录处理时间
            process_time = (datetime.now() - start_time).total_seconds()
            
            # 更新统计
            self.stats["tasks_processed"] += 1
            self.stats["tasks_succeeded"] += 1
            self.stats["last_task_time"] = datetime.now().isoformat()
            
            logger.info(f"任务完成: {task_id}, 类型: {task_type}, 时间: {process_time:.2f}秒")
            
        except asyncio.TimeoutError:
            error_msg = f"任务超时: {task_id}"
            logger.error(error_msg)
            
            result = {"error": error_msg}
            await redis_service.update_task_status(task_id, "failed", result)
            
            self.stats["tasks_processed"] += 1
            self.stats["tasks_failed"] += 1
            
        except Exception as e:
            error_msg = f"任务处理失败: {task_id}, 错误: {e}"
            logger.error(error_msg, exc_info=True)
            
            result = {"error": error_msg}
            await redis_service.update_task_status(task_id, "failed", result)
            
            self.stats["tasks_processed"] += 1
            self.stats["tasks_failed"] += 1
    
    async def _process_grade_task(self, task_id: str, task_data: dict):
        """处理判卷任务"""
        try:
            # 提取任务数据
            user_id = task_data.get("user_id")
            question = task_data.get("question", "")
            pdf_text = task_data.get("pdf_text", "")
            
            # 如果没有提供题目，从PDF中提取或使用默认题目
            if not question and pdf_text:
                # 这里可以添加从PDF中提取题目的逻辑
                # 暂时使用默认题目
                question = "请根据材料内容，写一篇申论文章。"
            
            # 假设PDF文本包含答案（实际应用中可能需要分离材料和答案）
            # 这里简化处理：整个PDF文本作为答案
            answer_text = pdf_text
            
            # 调用DeepSeek进行评分
            result = await deepseek_client.grade_with_json(pdf_text, question, answer_text)
            
            # 提取摘要
            total_score = result.get("total_score", 0)
            summary = result.get("evaluation", "")[:200]
            if not summary and "scores" in result:
                summary = f"总分: {total_score}, 各项得分: {result['scores']}"
            
            # 保存到R2
            r2_url = None
            if cloudflare_r2_service:
                import json
                r2_url = await cloudflare_r2_service.upload_json(
                    filename=f"{task_id}.json",
                    content=result,
                    path_type="results"
                )
            
            # 保存到数据库
            await supabase_service.save_user_result(
                user_id=user_id,
                task_id=task_id,
                total_score=total_score,
                summary=summary,
                full_result=result if len(json.dumps(result)) < 10240 else None,
                r2_url=r2_url
            )
            
            # 更新任务状态为完成
            await redis_service.update_task_status(task_id, "completed", result)
            
            return result
            
        except Exception as e:
            logger.error(f"处理判卷任务失败: {task_id}, 错误: {e}")
            raise
    
    def _task_done_callback(self, future, task_handle):
        """任务完成回调"""
        try:
            # 从处理中集合移除
            self.processing_tasks.discard(task_handle)
            
            # 检查是否有异常
            if future.exception():
                logger.error(f"任务处理异常: {future.exception()}")
        except Exception as e:
            logger.error(f"任务完成回调出错: {e}")
    
    def _log_status(self):
        """记录状态"""
        status = {
            "running": self.is_running,
            "processing_tasks": len(self.processing_tasks),
            "stats": self.stats,
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.info(f"Worker状态: {status}")
    
    async def shutdown(self):
        """关闭服务"""
        logger.info("Worker服务关闭中...")
        
        self.is_running = False
        
        try:
            # 停止监控服务
            await monitoring_service.stop_monitoring()
            
            # 关闭Redis连接
            await redis_service.close()
            
            # 记录最终统计
            logger.info(f"Worker服务统计: {self.stats}")
            
        except Exception as e:
            logger.error(f"Worker服务关闭时出错: {e}")
        
        logger.info("Worker服务关闭完成")


async def main():
    """主函数"""
    worker = WorkerService()
    
    try:
        # 初始化
        await worker.initialize()
        
        # 运行
        await worker.run()
        
    except KeyboardInterrupt:
        logger.info("收到键盘中断，准备关闭...")
        worker.shutdown_event.set()
        await worker.shutdown()
        
    except Exception as e:
        logger.error(f"Worker服务出错: {e}")
        await worker.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    # 设置事件循环策略（Windows需要）
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 运行主函数
    asyncio.run(main())