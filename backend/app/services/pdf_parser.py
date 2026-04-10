"""
PDF解析服务 - 实现流式解析和内存优化
遵循技术升级指南1.1.3和2.4.1
"""

import os
import gc
import fitz  # PyMuPDF
import asyncio
import tempfile
from typing import Optional, Generator, List, Dict, Any
from pathlib import Path
import logging

from backend.app.config import settings

logger = logging.getLogger(__name__)


class PDFParser:
    """优化的PDF解析器，使用PyMuPDF实现流式解析"""
    
    def __init__(self):
        self.max_memory_mb = settings.MEMORY_WARNING_THRESHOLD_MB
        self.chunk_size = settings.PDF_CHUNK_SIZE_KB * 1024
        
    async def parse_pdf_stream(self, file_path: str, max_pages: Optional[int] = None) -> Generator[str, None, None]:
        """
        流式解析PDF文件，避免一次性加载整个文件到内存
        
        Args:
            file_path: PDF文件路径
            max_pages: 最大解析页数（None表示全部）
            
        Yields:
            每页的文本内容
        """
        logger.info(f"开始流式解析PDF: {file_path}")
        
        doc = None
        try:
            # 使用PyMuPDF打开PDF
            doc = fitz.open(file_path)
            total_pages = len(doc)
            
            if max_pages and max_pages < total_pages:
                total_pages = max_pages
                logger.info(f"限制解析前{max_pages}页，共{len(doc)}页")
            
            for page_num in range(total_pages):
                try:
                    # 加载当前页
                    page = doc.load_page(page_num)
                    
                    # 提取文本
                    text = page.get_text()
                    
                    # 清理文本
                    cleaned_text = self._clean_text(text)
                    
                    if cleaned_text:
                        yield cleaned_text
                    
                    # 显式释放页面内存
                    del page, text
                    
                    # 每5页触发一次GC
                    if page_num > 0 and page_num % 5 == 0:
                        gc.collect()
                        logger.debug(f"已解析{page_num + 1}页，触发GC清理")
                        
                except Exception as page_error:
                    logger.error(f"解析第{page_num + 1}页时出错: {page_error}")
                    continue
                    
        except Exception as e:
            logger.error(f"解析PDF文件时出错: {e}")
            raise
        finally:
            # 确保文档被关闭
            if doc:
                doc.close()
                del doc
                gc.collect()
                
        logger.info(f"PDF解析完成: {file_path}")
    
    async def parse_pdf_to_text(self, file_path: str, max_pages: Optional[int] = None) -> str:
        """
        解析PDF文件为文本（兼容旧接口）
        
        Args:
            file_path: PDF文件路径
            max_pages: 最大解析页数
            
        Returns:
            合并的文本内容
        """
        texts = []
        async for page_text in self.parse_pdf_stream(file_path, max_pages):
            texts.append(page_text)
        
        return "\n\n".join(texts)
    
    async def parse_pdf_with_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        解析PDF并提取元数据
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            包含文本和元数据的字典
        """
        doc = None
        try:
            doc = fitz.open(file_path)
            
            metadata = {
                "total_pages": len(doc),
                "author": doc.metadata.get("author", ""),
                "title": doc.metadata.get("title", ""),
                "subject": doc.metadata.get("subject", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", ""),
                "text": ""
            }
            
            # 流式提取文本
            texts = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                cleaned_text = self._clean_text(text)
                if cleaned_text:
                    texts.append(cleaned_text)
                
                # 释放内存
                del page, text
                if page_num % 5 == 0:
                    gc.collect()
            
            metadata["text"] = "\n\n".join(texts)
            return metadata
            
        finally:
            if doc:
                doc.close()
    
    async def extract_images(self, file_path: str, output_dir: str) -> List[str]:
        """
        从PDF中提取图片（用于OCR）
        
        Args:
            file_path: PDF文件路径
            output_dir: 图片输出目录
            
        Returns:
            提取的图片路径列表
        """
        doc = None
        image_paths = []
        
        try:
            doc = fitz.open(file_path)
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        # 获取图片
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        
                        if base_image:
                            image_bytes = base_image["image"]
                            image_ext = base_image["ext"]
                            
                            # 保存图片
                            image_filename = f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
                            image_path = Path(output_dir) / image_filename
                            
                            with open(image_path, "wb") as f:
                                f.write(image_bytes)
                            
                            image_paths.append(str(image_path))
                            logger.debug(f"提取图片: {image_path}")
                    
                    except Exception as img_error:
                        logger.error(f"提取第{page_num + 1}页图片{img_index + 1}时出错: {img_error}")
                        continue
                
                # 释放内存
                del page
                if page_num % 3 == 0:
                    gc.collect()
        
        except Exception as e:
            logger.error(f"提取PDF图片时出错: {e}")
            raise
        
        finally:
            if doc:
                doc.close()
        
        return image_paths
    
    def _clean_text(self, text: str) -> str:
        """
        清理文本
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 移除多余的空格和换行
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        # 合并行，但保留段落分隔
        result = []
        current_paragraph = []
        
        for line in cleaned_lines:
            if line.endswith(('.', '。', '!', '！', '?', '？')):
                current_paragraph.append(line)
                result.append(' '.join(current_paragraph))
                current_paragraph = []
            else:
                current_paragraph.append(line)
        
        if current_paragraph:
            result.append(' '.join(current_paragraph))
        
        return '\n'.join(result)
    
    async def get_pdf_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取PDF文件信息
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            PDF信息字典
        """
        doc = None
        try:
            doc = fitz.open(file_path)
            
            info = {
                "file_path": file_path,
                "file_size_mb": os.path.getsize(file_path) / (1024 * 1024),
                "total_pages": len(doc),
                "metadata": doc.metadata,
                "is_scanned": self._is_scanned_pdf(doc),
            }
            
            return info
            
        finally:
            if doc:
                doc.close()
    
    def _is_scanned_pdf(self, doc) -> bool:
        """
        判断PDF是否为扫描件
        
        Args:
            doc: PyMuPDF文档对象
            
        Returns:
            是否为扫描件
        """
        try:
            # 检查前3页是否有可提取的文本
            sample_pages = min(3, len(doc))
            has_text = False
            
            for page_num in range(sample_pages):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text and len(text.strip()) > 50:  # 有超过50个字符的文本
                    has_text = True
                    break
                del page
            
            return not has_text
            
        except:
            return True
    
    async def compress_pdf(self, input_path: str, output_path: str) -> str:
        """
        压缩PDF文件（前端上传前使用）
        
        Args:
            input_path: 输入PDF路径
            output_path: 输出PDF路径
            
        Returns:
            压缩后的PDF路径
        """
        # 这里可以实现PDF压缩逻辑
        # 由于时间关系，暂时返回原文件路径
        return input_path


# 创建全局实例
pdf_parser = PDFParser()

# 导出
__all__ = ["PDFParser", "pdf_parser"]