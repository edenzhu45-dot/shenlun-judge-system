"""
API端点 - 申论智能判卷系统的主要接口
"""

import os
import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse

from backend.app.config import settings
from backend.app.services.pdf_parser import pdf_parser
from backend.app.services.deepseek_client import deepseek_client
from backend.app.services.redis_service import redis_service
from backend.app.services.supabase_service import supabase_service
from backend.app.services.cloudflare_r2_service import cloudflare_r2_service
from backend.app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload/pdf")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: int = Form(...),
    activation_code: str = Form(...),
    question: str = Form(""),
):
    """
    上传PDF文件并启动判卷任务
    
    Args:
        file: PDF文件
        user_id: 用户ID
        activation_code: 激活码
        question: 题目（可选，如果PDF中已包含）
        
    Returns:
        任务ID和状态
    """
    # 验证激活码
    is_valid, error_msg = await supabase_service.validate_activation_code(activation_code, user_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # 验证文件类型
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持PDF文件")
    
    # 验证文件大小
    file_size = 0
    temp_file_path = None
    
    try:
        # 创建临时文件
        import tempfile
        import aiofiles
        
        temp_dir = settings.UPLOAD_DIR
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file_path = os.path.join(temp_dir, f"temp_{uuid.uuid4()}.pdf")
        
        # 保存上传的文件
        async with aiofiles.open(temp_file_path, 'wb') as f:
            content = await file.read()
            file_size = len(content)
            
            if file_size > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(status_code=400, detail=f"文件太大，最大支持{settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB")
            
            await f.write(content)
        
        # 解析PDF
        logger.info(f"开始解析PDF: {file.filename}, 大小: {file_size}字节")
        pdf_text = await pdf_parser.parse_pdf_to_text(temp_file_path)
        
        if not pdf_text or len(pdf_text.strip()) < 50:
            raise HTTPException(status_code=400, detail="PDF解析失败或内容过少")
        
        # 创建判卷任务
        task_data = {
            "type": "grade",
            "user_id": user_id,
            "activation_code": activation_code,
            "question": question,
            "pdf_text": pdf_text,
            "original_filename": file.filename,
            "file_size": file_size,
        }
        
        # 提交到任务队列
        task_id = await redis_service.submit_task(task_data, priority="normal")
        
        # 后台处理任务
        background_tasks.add_task(process_grade_task, task_id, task_data)
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "判卷任务已提交，请稍后查询结果",
            "file_info": {
                "filename": file.filename,
                "size_bytes": file_size,
                "text_length": len(pdf_text),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传PDF失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass


@router.get("/task/status/{task_id}")
async def get_task_status(task_id: str):
    """
    获取任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态和结果
    """
    try:
        result = await redis_service.get_task_result(task_id)
        
        if not result:
            return {
                "task_id": task_id,
                "status": "not_found",
                "message": "任务不存在或已过期",
            }
        
        return {
            "task_id": task_id,
            "status": result.get("status", "unknown"),
            "result": result,
            "timestamp": result.get("meta", {}).get("updated_at"),
        }
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/grade/direct")
async def grade_direct(
    material_text: str = Form(...),
    question: str = Form(...),
    answer_text: str = Form(...),
    user_id: int = Form(...),
    activation_code: str = Form(...),
):
    """
    直接判卷（不通过文件上传）
    
    Args:
        material_text: 材料文本
        question: 题目
        answer_text: 答案文本
        user_id: 用户ID
        activation_code: 激活码
        
    Returns:
        评分结果
    """
    # 验证激活码
    is_valid, error_msg = await supabase_service.validate_activation_code(activation_code, user_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        # 直接调用DeepSeek进行评分
        result = await deepseek_client.grade_with_json(material_text, question, answer_text)
        
        # 保存结果
        task_id = str(uuid.uuid4())
        total_score = result.get("total_score", 0)
        
        # 提取摘要
        summary = result.get("evaluation", "")[:200]
        if not summary and "scores" in result:
            summary = f"总分: {total_score}, 各项得分: {result['scores']}"
        
        # 保存到R2
        r2_url = None
        if cloudflare_r2_service:
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
        
        return {
            "success": True,
            "task_id": task_id,
            "result": result,
            "r2_url": r2_url,
        }
        
    except Exception as e:
        logger.error(f"直接判卷失败: {e}")
        raise HTTPException(status_code=500, detail=f"判卷失败: {str(e)}")


@router.get("/grade/stream")
async def grade_stream(
    material_text: str,
    question: str,
    answer_text: str,
):
    """
    流式判卷
    
    Args:
        material_text: 材料文本
        question: 题目
        answer_text: 答案文本
        
    Returns:
        流式响应
    """
    async def generate():
        async for chunk in deepseek_client.stream_grade(material_text, question, answer_text):
            yield chunk
    
    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache",
        }
    )


@router.get("/user/history/{user_id}")
async def get_user_history(
    user_id: int,
    page: int = 0,
    limit: Optional[int] = None,
):
    """
    获取用户历史记录（分页优化）
    
    Args:
        user_id: 用户ID
        page: 页码
        limit: 每页数量
        
    Returns:
        用户历史记录
    """
    try:
        # 尝试从缓存获取
        cache_key = f"{user_id}:{page}:{limit or settings.QUERY_PAGE_SIZE}"
        cached = await redis_service.get_with_cache(cache_key, "user_history")
        
        if cached:
            logger.debug(f"用户历史缓存命中: {cache_key}")
            return cached
        
        # 从数据库获取
        result = await supabase_service.get_user_results(user_id, page, limit)
        
        # 缓存结果
        await redis_service.set_with_cache(cache_key, result, "user_history")
        
        return result
        
    except Exception as e:
        logger.error(f"获取用户历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.get("/result/full/{task_id}")
async def get_full_result(task_id: str):
    """
    获取完整结果（从R2加载）
    
    Args:
        task_id: 任务ID
        
    Returns:
        完整结果
    """
    try:
        # 先从数据库获取记录
        record = await supabase_service.get_user_result_by_task_id(task_id)
        
        if not record:
            raise HTTPException(status_code=404, detail="结果不存在")
        
        # 如果有R2 URL，从R2加载完整结果
        r2_url = record.get("r2_url")
        if r2_url and cloudflare_r2_service:
            full_result = await cloudflare_r2_service.download_json(r2_url)
            if full_result:
                return full_result
        
        # 如果数据库中有完整结果，直接返回
        if "full_result" in record and record["full_result"]:
            return record["full_result"]
        
        # 只有摘要信息
        return {
            "summary": record.get("summary", ""),
            "total_score": record.get("total_score", 0),
            "created_at": record.get("created_at"),
            "message": "完整结果未找到，可能已过期",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取完整结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取结果失败: {str(e)}")


@router.get("/system/health")
async def system_health():
    """
    系统健康检查
    
    Returns:
        系统健康状态
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {},
        }
        
        # 检查各服务状态
        services_to_check = [
            ("supabase", supabase_service.health_check),
            ("redis", redis_service.health_check),
            ("deepseek", deepseek_client.health_check),
            ("r2", cloudflare_r2_service.health_check if cloudflare_r2_service else lambda: False),
        ]
        
        for service_name, check_func in services_to_check:
            try:
                is_healthy = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
                health_status["services"][service_name] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "checked": True,
                }
            except Exception as e:
                health_status["services"][service_name] = {
                    "status": "error",
                    "error": str(e),
                    "checked": False,
                }
        
        # 检查内存状态
        current_metrics = monitoring_service.get_current_metrics()
        memory_mb = current_metrics.get("memory", {}).get("rss_mb", 0)
        
        if memory_mb > settings.MEMORY_CRITICAL_THRESHOLD_MB:
            health_status["status"] = "degraded"
            health_status["memory_warning"] = f"内存使用过高: {memory_mb:.1f}MB"
        elif memory_mb > settings.MEMORY_WARNING_THRESHOLD_MB:
            health_status["status"] = "warning"
            health_status["memory_warning"] = f"内存使用警告: {memory_mb:.1f}MB"
        
        health_status["metrics"] = current_metrics
        
        return health_status
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/system/metrics")
async def system_metrics(limit: int = 50):
    """
    获取系统监控指标
    
    Args:
        limit: 数据点数量限制
        
    Returns:
        监控指标
    """
    try:
        return {
            "current": monitoring_service.get_current_metrics(),
            "historical": monitoring_service.get_historical_metrics(limit),
            "settings": {
                "memory_warning_threshold_mb": settings.MEMORY_WARNING_THRESHOLD_MB,
                "memory_critical_threshold_mb": settings.MEMORY_CRITICAL_THRESHOLD_MB,
                "monitoring_interval": settings.MONITORING_INTERVAL,
            },
        }
    except Exception as e:
        logger.error(f"获取监控指标失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取指标失败: {str(e)}")


@router.post("/system/gc")
async def trigger_gc():
    """
    触发垃圾回收
    
    Returns:
        GC结果
    """
    try:
        result = await monitoring_service.force_gc()
        return {
            "success": True,
            "message": "垃圾回收完成",
            "result": result,
        }
    except Exception as e:
        logger.error(f"触发GC失败: {e}")
        raise HTTPException(status_code=500, detail=f"GC失败: {str(e)}")


@router.post("/activation/generate")
async def generate_activation_codes(
    count: int = Form(10),
    expires_days: int = Form(30),
):
    """
    生成激活码（管理员功能）
    
    Args:
        count: 生成数量
        expires_days: 过期天数
        
    Returns:
        生成的激活码列表
    """
    # 这里可以添加管理员验证逻辑
    # 暂时跳过验证，生产环境必须添加
    
    try:
        if count > 100:
            raise HTTPException(status_code=400, detail="一次最多生成100个激活码")
        
        codes = await supabase_service.create_activation_codes(count, expires_days)
        
        return {
            "success": True,
            "count": len(codes),
            "expires_days": expires_days,
            "codes": codes,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成激活码失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


# 后台任务处理函数
async def process_grade_task(task_id: str, task_data: dict):
    """
    处理判卷任务
    
    Args:
        task_id: 任务ID
        task_data: 任务数据
    """
    logger.info(f"开始处理判卷任务: {task_id}")
    
    try:
        # 更新任务状态为处理中
        await redis_service.update_task_status(task_id, "processing")
        
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
        
        logger.info(f"判卷任务完成: {task_id}, 总分: {total_score}")
        
    except Exception as e:
        logger.error(f"处理判卷任务失败: {task_id}, 错误: {e}")
        
        # 更新任务状态为失败
        await redis_service.update_task_status(task_id, "failed", {"error": str(e)})


# 导入必要的模块
import json
from datetime import datetime
import asyncio

# 导出路由
__all__ = ["router"]