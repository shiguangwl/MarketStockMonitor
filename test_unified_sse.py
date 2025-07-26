#!/usr/bin/env python3
"""统一SSE端点测试脚本."""

import requests
import time
import json
from urllib.parse import urlencode

def test_sse_endpoint(base_url="http://localhost:8000", **params):
    """测试SSE端点."""
    url = f"{base_url}/api/sources/stream"
    if params:
        # 过滤掉空值参数
        filtered_params = {k: v for k, v in params.items() if v}
        if filtered_params:
            url += "?" + urlencode(filtered_params)
    
    print(f"🔗 测试SSE端点: {url}")
    
    try:
        response = requests.get(url, stream=True, timeout=5)
        print(f"✅ 连接状态: {response.status_code}")
        
        if response.status_code == 200:
            print("📨 接收到的数据:")
            count = 0
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    print(f"  {line}")
                    count += 1
                    if count >= 10:  # 限制输出行数
                        break
        else:
            print(f"❌ 连接失败: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ 连接超时（正常，用于测试）")
    except Exception as e:
        print(f"❌ 连接异常: {str(e)}")

def test_stats_endpoint(base_url="http://localhost:8000"):
    """测试统计端点."""
    url = f"{base_url}/api/sources/stream/stats"
    print(f"📊 测试统计端点: {url}")
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 统计信息: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 获取统计失败: {response.text}")
    except Exception as e:
        print(f"❌ 统计端点异常: {str(e)}")

def main():
    """主测试函数."""
    print("🚀 统一SSE端点测试")
    print("=" * 50)
    
    # 测试统计端点
    test_stats_endpoint()
    print()
    
    # 测试1: 无参数（接收所有数据）
    print("📋 测试1: 接收所有数据")
    test_sse_endpoint()
    print()
    
    # 测试2: 指定数据源
    print("📋 测试2: 指定数据源")
    test_sse_endpoint(sources="wen_cai")
    print()
    
    # 测试3: 指定市场
    print("📋 测试3: 指定市场")
    test_sse_endpoint(sources="wen_cai", markets="HSI")
    print()
    
    # 测试4: 指定数据类型
    print("📋 测试4: 指定数据类型")
    test_sse_endpoint(sources="wen_cai", markets="HSI", data_types="realtime")
    print()
    
    # 测试5: 多市场
    print("📋 测试5: 多市场")
    test_sse_endpoint(sources="wen_cai", markets="HSI,NASDAQ", data_types="realtime")
    print()
    
    print("🎯 测试完成！")

if __name__ == "__main__":
    main()