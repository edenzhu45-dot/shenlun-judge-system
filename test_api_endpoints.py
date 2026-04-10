#!/usr/bin/env python3
"""
测试API端点
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_api_endpoints():
    """测试API端点"""
    print("测试API端点...")
    
    try:
        from backend.app.api.endpoints import router
        
        print(f"✓ API路由器加载成功")
        print(f"  - 路由器前缀: {router.prefix}")
        print(f"  - 路由器标签: {router.tags}")
        
        # 检查路由
        routes = router.routes
        print(f"  - 路由数量: {len(routes)}")
        
        for i, route in enumerate(routes[:5]):  # 只显示前5个路由
            print(f"    {i+1}. {route.path} - {route.methods}")
        
        return True
    except Exception as e:
        print(f"✗ API端点测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_endpoints()
    sys.exit(0 if success else 1)