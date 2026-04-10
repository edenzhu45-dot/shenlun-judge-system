#!/usr/bin/env python3
"""
测试配置文件加载
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_config_loading():
    """测试配置文件加载"""
    print("测试配置文件加载...")
    
    try:
        # 设置环境变量
        os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:8000"
        
        from backend.app.config import settings
        
        print(f"✓ 配置文件加载成功")
        print(f"  - APP_NAME: {settings.APP_NAME}")
        print(f"  - DEBUG: {settings.DEBUG}")
        print(f"  - CORS_ORIGINS: {settings.CORS_ORIGINS}")
        print(f"  - 类型: {type(settings.CORS_ORIGINS)}")
        
        return True
    except Exception as e:
        print(f"✗ 配置文件加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_config_loading()
    sys.exit(0 if success else 1)