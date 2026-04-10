"""
DeepSeek客户端 - 实现内存优化和流式响应
遵循技术升级指南1.1.3
"""

import gc
import json
import asyncio
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI

from backend.app.config import settings

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """优化的DeepSeek客户端，实现内存优化和上下文控制"""
    
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL
        self.max_tokens = settings.DEEPSEEK_MAX_TOKENS
        self.temperature = settings.DEEPSEEK_TEMPERATURE
        self.max_context_length = settings.DEEPSEEK_MAX_CONTEXT_LENGTH
        
        # 初始化OpenAI客户端
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        
        # 内存优化：预定义提示模板
        self.prompt_templates = {
            "grade": """你是一位专业的申论阅卷老师。请根据以下材料、题目和考生答案进行评分：

材料：
{material}

题目：
{question}

考生答案：
{answer}

请按照以下标准进行评分：
1. 内容完整性（0-30分）：是否全面回答了题目要求
2. 逻辑结构（0-25分）：文章结构是否清晰，逻辑是否严密
3. 语言表达（0-20分）：语言是否准确、流畅、得体
4. 论证深度（0-15分）：分析是否深入，论证是否充分
5. 创新性（0-10分）：是否有独到见解或创新思考

请给出：
1. 各项得分及总分（满分100分）
2. 详细的评分理由
3. 具体的改进建议
4. 范文示例（可选）

请以JSON格式返回，包含以下字段：
- total_score: 总分
- scores: 各项得分字典
- evaluation: 评分理由
- suggestions: 改进建议
- model_answer: 范文示例（可选）""",
            
            "analyze": """请分析以下申论答案的特点：

答案：
{answer}

请分析：
1. 优点和亮点
2. 不足和问题
3. 改进方向
4. 同类题目的应对策略""",
            
            "summarize": """请将以下文本摘要到约{target_length}字：

文本：
{text}

要求：
1. 保留核心信息和关键观点
2. 保持原文的逻辑结构
3. 语言简洁明了""",
        }
    
    async def stream_grade(
        self, 
        material_text: str, 
        question: str, 
        answer_text: str
    ) -> AsyncGenerator[str, None]:
        """
        流式评分，实现内存优化
        
        Args:
            material_text: 材料文本
            question: 题目
            answer_text: 答案文本
            
        Yields:
            AI响应片段
        """
        logger.info("开始流式评分")
        
        try:
            # 上下文长度控制（遵循指南1.1.3）
            material_text = await self._control_context_length(
                material_text, 
                max_length=settings.MATERIAL_SUMMARY_LENGTH
            )
            
            # 构建完整上下文
            full_context = f"材料：\n{material_text}\n\n题目：\n{question}\n\n答案：\n{answer_text}"
            
            # 检查上下文长度
            if len(full_context) > self.max_context_length:
                logger.warning(f"上下文过长: {len(full_context)}字符，将进行摘要")
                full_context = await self.summarize_text(full_context, self.max_context_length)
            
            # 构建消息
            messages = [
                {
                    "role": "system",
                    "content": "你是一位专业的申论阅卷老师，请根据评分标准给出客观、专业的评分和建议。"
                },
                {
                    "role": "user",
                    "content": self.prompt_templates["grade"].format(
                        material=material_text,
                        question=question,
                        answer=answer_text
                    )
                }
            ]
            
            # 流式调用
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True,
            )
            
            # 流式返回结果
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    yield content
            
            logger.info("流式评分完成")
            
        except Exception as e:
            logger.error(f"流式评分出错: {e}")
            yield f"评分过程中出现错误: {str(e)}"
            
        finally:
            # 显式内存清理（遵循指南1.1.3）
            del material_text, question, answer_text
            gc.collect()
    
    async def grade_with_json(
        self, 
        material_text: str, 
        question: str, 
        answer_text: str
    ) -> Dict[str, Any]:
        """
        非流式评分，返回JSON格式结果
        
        Args:
            material_text: 材料文本
            question: 题目
            answer_text: 答案文本
            
        Returns:
            评分结果字典
        """
        logger.info("开始JSON格式评分")
        
        try:
            # 上下文长度控制
            material_text = await self._control_context_length(
                material_text, 
                max_length=settings.MATERIAL_SUMMARY_LENGTH
            )
            
            # 构建消息
            messages = [
                {
                    "role": "system",
                    "content": "你是一位专业的申论阅卷老师。请严格按照JSON格式返回评分结果，包含total_score、scores、evaluation、suggestions字段。"
                },
                {
                    "role": "user",
                    "content": self.prompt_templates["grade"].format(
                        material=material_text,
                        question=question,
                        answer=answer_text
                    )
                }
            ]
            
            # 调用API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )
            
            # 解析响应
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # 添加元数据
            result["metadata"] = {
                "model": self.model,
                "timestamp": asyncio.get_event_loop().time(),
                "context_length": len(material_text) + len(question) + len(answer_text),
            }
            
            logger.info(f"JSON评分完成，总分: {result.get('total_score', 'N/A')}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析JSON响应失败: {e}")
            return {
                "error": "解析AI响应失败",
                "raw_response": content if 'content' in locals() else None,
                "total_score": 0,
                "scores": {},
                "evaluation": "评分过程中出现解析错误",
                "suggestions": "请稍后重试或联系技术支持",
            }
            
        except Exception as e:
            logger.error(f"评分出错: {e}")
            return {
                "error": str(e),
                "total_score": 0,
                "scores": {},
                "evaluation": "评分过程中出现错误",
                "suggestions": "请稍后重试或联系技术支持",
            }
            
        finally:
            # 内存清理
            gc.collect()
    
    async def analyze_answer(self, answer_text: str) -> Dict[str, Any]:
        """
        分析答案特点
        
        Args:
            answer_text: 答案文本
            
        Returns:
            分析结果
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是一位申论辅导老师，请分析答案的特点并提供改进建议。"
                },
                {
                    "role": "user",
                    "content": self.prompt_templates["analyze"].format(answer=answer_text)
                }
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
            )
            
            content = response.choices[0].message.content
            return {"analysis": content}
            
        except Exception as e:
            logger.error(f"分析答案出错: {e}")
            return {"error": str(e)}
    
    async def summarize_text(self, text: str, target_length: int = 2000) -> str:
        """
        摘要文本，用于控制上下文长度
        
        Args:
            text: 原始文本
            target_length: 目标长度
            
        Returns:
            摘要后的文本
        """
        if len(text) <= target_length:
            return text
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是一位文本摘要专家，请将文本摘要到指定长度，保留核心信息。"
                },
                {
                    "role": "user",
                    "content": self.prompt_templates["summarize"].format(
                        text=text,
                        target_length=target_length
                    )
                }
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=target_length + 500,  # 留有余量
                temperature=0.3,  # 低温度以获得更确定的摘要
            )
            
            summary = response.choices[0].message.content
            logger.info(f"文本摘要完成: {len(text)} -> {len(summary)} 字符")
            return summary
            
        except Exception as e:
            logger.error(f"文本摘要出错: {e}")
            # 如果摘要失败，直接截断
            return text[:target_length] + "...[已截断]"
    
    async def _control_context_length(self, text: str, max_length: int) -> str:
        """
        控制上下文长度
        
        Args:
            text: 原始文本
            max_length: 最大长度
            
        Returns:
            处理后的文本
        """
        if len(text) <= max_length:
            return text
        
        logger.warning(f"文本过长: {len(text)}字符，将进行摘要")
        return await self.summarize_text(text, max_length)
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            服务是否可用
        """
        try:
            # 发送一个简单的测试请求
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )
            
            return response.choices[0].message.content is not None
            
        except Exception as e:
            logger.error(f"DeepSeek健康检查失败: {e}")
            return False
    
    async def get_usage_info(self) -> Dict[str, Any]:
        """
        获取使用情况信息
        
        Returns:
            使用情况信息
        """
        # 注意：DeepSeek API可能没有直接的usage接口
        # 这里返回基本状态信息
        return {
            "model": self.model,
            "max_context_length": self.max_context_length,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "status": "active" if self.api_key else "inactive",
        }


# 创建全局实例
deepseek_client = DeepSeekClient()

# 导出
__all__ = ["DeepSeekClient", "deepseek_client"]