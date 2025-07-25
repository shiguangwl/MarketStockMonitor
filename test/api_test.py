"""API 测试文件"""

import requests
import json
from datetime import datetime, timedelta


def test_api_endpoints():
    """测试所有API端点"""
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("开始测试 MarketStockMonitor API")
    print("=" * 60)
    
    # 1. 测试获取数据源列表
    print("\n1. 测试获取数据源列表:")
    try:
        response = requests.get(f"{base_url}/api/sources")
        if response.status_code == 200:
            sources = response.json()
            print(f"✅ 成功获取 {len(sources)} 个数据源:")
            for source in sources:
                print(f"  - {source['source_name']} (ID: {source['source_id']})")
                print(f"    支持市场: {source['supported_markets']}")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 2. 测试获取最新价格 - HSI 实时数据
    print("\n2. 测试获取 HSI 实时价格:")
    try:
        response = requests.get(f"{base_url}/api/sources/wen_cai/latest/HSI/realtime")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ HSI 实时数据:")
            print(f"  名称: {data['data']['name']}")
            print(f"  时间: {data['data']['time']}")
            print(f"  价格: {data['data']['price']}")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 3. 测试获取最新价格 - NASDAQ 实时数据
    print("\n3. 测试获取 NASDAQ 实时价格:")
    try:
        response = requests.get(f"{base_url}/api/sources/wen_cai/latest/NASDAQ/realtime")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ NASDAQ 实时数据:")
            print(f"  名称: {data['data']['name']}")
            print(f"  时间: {data['data']['time']}")
            print(f"  价格: {data['data']['price']}")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 4. 测试获取最新价格 - HSI K线数据
    print("\n4. 测试获取 HSI K线数据:")
    try:
        response = requests.get(f"{base_url}/api/sources/wen_cai/latest/HSI/kline1m")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ HSI K线数据:")
            print(f"  名称: {data['data']['name']}")
            print(f"  时间: {data['data']['time']}")
            print(f"  价格: {data['data']['price']}")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 5. 测试获取交易时间表 - HSI
    print("\n5. 测试获取 HSI 交易时间表:")
    try:
        response = requests.get(f"{base_url}/api/sources/wen_cai/trading-hours/HSI")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ HSI 交易时间表 (显示前5条):")
            for i, th in enumerate(data['trading_hours'][:5]):
                print(f"  {i+1}. {th['start']} 到 {th['end']}")
                print(f"     描述: {th['text']}")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 6. 测试获取交易时间表 - NASDAQ
    print("\n6. 测试获取 NASDAQ 交易时间表:")
    try:
        response = requests.get(f"{base_url}/api/sources/wen_cai/trading-hours/NASDAQ")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ NASDAQ 交易时间表 (显示前5条):")
            for i, th in enumerate(data['trading_hours'][:5]):
                print(f"  {i+1}. {th['start']} 到 {th['end']}")
                print(f"     描述: {th['text']}")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 7. 测试获取市场状态 - HSI 当前时间
    print("\n7. 测试获取 HSI 当前市场状态:")
    try:
        response = requests.get(f"{base_url}/api/sources/wen_cai/market-status/HSI")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ HSI 当前市场状态:")
            print(f"  检查时间: {data['check_time']}")
            print(f"  是否开盘: {data['status']['is_open']}")
            print(f"  状态描述: {data['status']['status_text']}")
            if data['status']['matched_rule']:
                print(f"  匹配规则: {data['status']['matched_rule']['description']}")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 8. 测试获取市场状态 - NASDAQ 指定时间
    print("\n8. 测试获取 NASDAQ 指定时间市场状态:")
    try:
        # 使用昨天的时间作为测试
        test_time = (datetime.now() - timedelta(days=1)).isoformat()
        response = requests.get(f"{base_url}/api/sources/wen_cai/market-status/NASDAQ?check_time={test_time}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ NASDAQ 指定时间市场状态:")
            print(f"  检查时间: {data['check_time']}")
            print(f"  是否开盘: {data['status']['is_open']}")
            print(f"  状态描述: {data['status']['status_text']}")
            if data['status']['matched_rule']:
                print(f"  匹配规则: {data['status']['matched_rule']['description']}")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 9. 测试错误情况 - 无效数据源
    print("\n9. 测试错误情况 - 无效数据源:")
    try:
        response = requests.get(f"{base_url}/api/sources/invalid_source/latest/HSI/realtime")
        if response.status_code == 404:
            print("✅ 正确返回404错误")
        else:
            print(f"❌ 期望404错误，但得到: {response.status_code}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 10. 测试错误情况 - 无效市场
    print("\n10. 测试错误情况 - 无效市场:")
    try:
        response = requests.get(f"{base_url}/api/sources/wen_cai/latest/INVALID_MARKET/realtime")
        if response.status_code == 400:
            print("✅ 正确返回400错误")
        else:
            print(f"❌ 期望400错误，但得到: {response.status_code}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    print("\n" + "=" * 60)
    print("API 测试完成")
    print("=" * 60)


def print_api_documentation():
    """打印API文档"""
    print("\n" + "=" * 60)
    print("API 文档")
    print("=" * 60)
    
    apis = [
        {
            "endpoint": "GET /api/sources",
            "description": "获取数据源列表",
            "example": "curl http://localhost:8000/api/sources"
        },
        {
            "endpoint": "GET /api/sources/{source_id}/latest/{market}/{data_type}",
            "description": "获取指定数据源的指定市场的最新价格",
            "parameters": {
                "source_id": "数据源ID (如: wen_cai)",
                "market": "市场代码 (HSI, NASDAQ)",
                "data_type": "数据类型 (realtime, kline1m)"
            },
            "example": "curl http://localhost:8000/api/sources/wen_cai/latest/HSI/realtime"
        },
        {
            "endpoint": "GET /api/sources/{source_id}/trading-hours/{market}",
            "description": "获取特殊收盘时间表",
            "parameters": {
                "source_id": "数据源ID (如: wen_cai)",
                "market": "市场代码 (HSI, NASDAQ)"
            },
            "example": "curl http://localhost:8000/api/sources/wen_cai/trading-hours/HSI"
        },
        {
            "endpoint": "GET /api/sources/{source_id}/market-status/{market}",
            "description": "获取指定源的指定市场的状态",
            "parameters": {
                "source_id": "数据源ID (如: wen_cai)",
                "market": "市场代码 (HSI, NASDAQ)",
                "check_time": "检查时间 (可选，ISO格式)"
            },
            "example": "curl http://localhost:8000/api/sources/wen_cai/market-status/HSI"
        }
    ]
    
    for i, api in enumerate(apis, 1):
        print(f"\n{i}. {api['endpoint']}")
        print(f"   描述: {api['description']}")
        if 'parameters' in api:
            print(f"   参数:")
            for param, desc in api['parameters'].items():
                print(f"     - {param}: {desc}")
        print(f"   示例: {api['example']}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print_api_documentation()
    
    # 检查服务是否运行
    try:
        response = requests.get("http://localhost:8000/")
        if response.status_code == 200:
            test_api_endpoints()
        else:
            print("❌ 服务似乎没有运行在 http://localhost:8000")
            print("请先运行: python web.py")
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器 http://localhost:8000")
        print("请确保服务正在运行: python web.py") 