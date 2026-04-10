"""
监控服务 - 实现内存监控和性能监控
遵循技术升级指南1.1.4
"""

import asyncio
import psutil
import logging
from typing import Dict, Any
from datetime import datetime

from backend.app.config import settings

logger = logging.getLogger(__name__)


class MonitoringService:
    """监控服务，用于监控内存使用和系统性能"""
    
    def __init__(self):
        self.monitoring_interval = settings.MONITORING_INTERVAL
        self.memory_warning_threshold = settings.MEMORY_WARNING_THRESHOLD_MB
        self.memory_critical_threshold = settings.MEMORY_CRITICAL_THRESHOLD_MB
        
        self.monitoring_task = None
        self.is_running = False
        
        # 监控数据
        self.metrics = {
            "memory_usage": [],
            "cpu_usage": [],
            "disk_usage": [],
            "network_io": [],
            "active_connections": 0,
            "last_alert": None,
        }
        
        # 进程信息
        self.process = psutil.Process()
    
    async def start_monitoring(self):
        """启动监控"""
        if self.is_running:
            logger.warning("监控服务已在运行")
            return
        
        self.is_running = True
        logger.info(f"启动监控服务，间隔: {self.monitoring_interval}秒")
        
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("监控服务已停止")
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                await self._collect_metrics()
                await self._check_thresholds()
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _collect_metrics(self):
        """收集指标"""
        try:
            # 内存使用
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = self.process.memory_percent()
            
            # CPU使用
            cpu_percent = self.process.cpu_percent(interval=0.1)
            
            # 磁盘使用
            disk_usage = psutil.disk_usage('/')
            
            # 网络IO
            net_io = psutil.net_io_counters()
            
            # 保存指标（保留最近100个数据点）
            timestamp = datetime.now().isoformat()
            
            self.metrics["memory_usage"].append({
                "timestamp": timestamp,
                "rss_mb": memory_mb,
                "percent": memory_percent,
            })
            
            self.metrics["cpu_usage"].append({
                "timestamp": timestamp,
                "percent": cpu_percent,
            })
            
            self.metrics["disk_usage"].append({
                "timestamp": timestamp,
                "total_gb": disk_usage.total / 1024 / 1024 / 1024,
                "used_gb": disk_usage.used / 1024 / 1024 / 1024,
                "free_gb": disk_usage.free / 1024 / 1024 / 1024,
                "percent": disk_usage.percent,
            })
            
            self.metrics["network_io"].append({
                "timestamp": timestamp,
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
            })
            
            # 限制数据点数量
            for key in ["memory_usage", "cpu_usage", "disk_usage", "network_io"]:
                if len(self.metrics[key]) > 100:
                    self.metrics[key] = self.metrics[key][-100:]
            
            # 记录调试信息（每10次记录一次）
            if len(self.metrics["memory_usage"]) % 10 == 0:
                logger.debug(f"监控数据 - 内存: {memory_mb:.1f}MB, CPU: {cpu_percent:.1f}%, 磁盘: {disk_usage.percent:.1f}%")
                
        except Exception as e:
            logger.error(f"收集指标失败: {e}")
    
    async def _check_thresholds(self):
        """检查阈值"""
        try:
            if not self.metrics["memory_usage"]:
                return
            
            latest_memory = self.metrics["memory_usage"][-1]
            memory_mb = latest_memory["rss_mb"]
            
            # 检查内存阈值
            if memory_mb > self.memory_critical_threshold:
                await self._send_alert("CRITICAL", f"内存使用过高: {memory_mb:.1f}MB > {self.memory_critical_threshold}MB")
            elif memory_mb > self.memory_warning_threshold:
                if not self.metrics["last_alert"] or "WARNING" not in self.metrics["last_alert"]:
                    await self._send_alert("WARNING", f"内存使用警告: {memory_mb:.1f}MB > {self.memory_warning_threshold}MB")
            
        except Exception as e:
            logger.error(f"检查阈值失败: {e}")
    
    async def _send_alert(self, level: str, message: str):
        """发送警报"""
        alert_time = datetime.now().isoformat()
        alert_data = {
            "level": level,
            "message": message,
            "timestamp": alert_time,
            "metrics": self.get_current_metrics(),
        }
        
        self.metrics["last_alert"] = f"{level}: {message}"
        
        # 这里可以集成到外部告警系统（如Slack、邮件等）
        logger.warning(f"系统警报 [{level}]: {message}")
        
        # 记录到文件（生产环境应该使用专门的日志系统）
        try:
            with open("monitoring_alerts.log", "a") as f:
                f.write(f"{alert_time} [{level}] {message}\n")
        except:
            pass
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前指标"""
        if not self.metrics["memory_usage"]:
            return {"error": "暂无监控数据"}
        
        latest_memory = self.metrics["memory_usage"][-1]
        latest_cpu = self.metrics["cpu_usage"][-1] if self.metrics["cpu_usage"] else {}
        latest_disk = self.metrics["disk_usage"][-1] if self.metrics["disk_usage"] else {}
        
        return {
            "memory": {
                "rss_mb": latest_memory.get("rss_mb", 0),
                "percent": latest_memory.get("percent", 0),
                "warning_threshold_mb": self.memory_warning_threshold,
                "critical_threshold_mb": self.memory_critical_threshold,
            },
            "cpu": {
                "percent": latest_cpu.get("percent", 0),
            },
            "disk": {
                "total_gb": latest_disk.get("total_gb", 0),
                "used_gb": latest_disk.get("used_gb", 0),
                "free_gb": latest_disk.get("free_gb", 0),
                "percent": latest_disk.get("percent", 0),
            },
            "process": {
                "pid": self.process.pid,
                "name": self.process.name(),
                "status": self.process.status(),
                "create_time": datetime.fromtimestamp(self.process.create_time()).isoformat() if self.process.create_time() else None,
            },
            "system": {
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                "cpu_count": psutil.cpu_count(),
                "total_memory_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
                "available_memory_gb": psutil.virtual_memory().available / 1024 / 1024 / 1024,
            },
            "timestamp": datetime.now().isoformat(),
        }
    
    def get_historical_metrics(self, limit: int = 50) -> Dict[str, Any]:
        """获取历史指标"""
        return {
            "memory_usage": self.metrics["memory_usage"][-limit:] if self.metrics["memory_usage"] else [],
            "cpu_usage": self.metrics["cpu_usage"][-limit:] if self.metrics["cpu_usage"] else [],
            "disk_usage": self.metrics["disk_usage"][-limit:] if self.metrics["disk_usage"] else [],
            "network_io": self.metrics["network_io"][-limit:] if self.metrics["network_io"] else [],
            "last_alert": self.metrics["last_alert"],
        }
    
    async def force_gc(self):
        """强制垃圾回收"""
        import gc
        
        before_memory = self.process.memory_info().rss / 1024 / 1024
        
        # 执行GC
        collected = gc.collect()
        
        after_memory = self.process.memory_info().rss / 1024 / 1024
        memory_saved = before_memory - after_memory
        
        logger.info(f"强制GC完成，回收对象: {collected}, 释放内存: {memory_saved:.1f}MB")
        
        return {
            "collected_objects": collected,
            "memory_saved_mb": memory_saved,
            "before_memory_mb": before_memory,
            "after_memory_mb": after_memory,
        }
    
    def is_healthy(self) -> bool:
        """检查系统是否健康"""
        try:
            if not self.metrics["memory_usage"]:
                return True
            
            latest_memory = self.metrics["memory_usage"][-1]
            memory_mb = latest_memory.get("rss_mb", 0)
            
            # 如果内存超过临界阈值，认为不健康
            return memory_mb <= self.memory_critical_threshold
            
        except:
            return True


# 创建全局实例
monitoring_service = MonitoringService()

# 导出
__all__ = ["MonitoringService", "monitoring_service"]