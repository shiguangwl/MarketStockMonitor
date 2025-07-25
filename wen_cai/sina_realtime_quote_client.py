import re
import time
from dataclasses import dataclass
from datetime import datetime
from pprint import pprint
from typing import Dict, List, Optional
import pytz
import requests

from .price_data_point import SinaPriceDataPoint


class SinaRealtimeQuoteClient:
    """新浪财经实时行情客户端"""
    
    def __init__(self):
        self.HEADERS = {
            'Referer': 'https://stock.finance.sina.com.cn/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.SINA_API_URL = "https://hq.sinajs.cn/"
        self.BEIJING_TZ = pytz.timezone('Asia/Shanghai')
        self.US_TZ_MAP = {
            'EDT': pytz.timezone('Etc/GMT+4'),
            'EST': pytz.timezone('Etc/GMT+5'),
        }
        
        # 港股 (rt_hk) 数据索引
        self.HK_NAME_IDX = 1
        self.HK_PRICE_IDX = 6
        self.HK_DATE_IDX = 17
        self.HK_TIME_IDX = 18
        
        # 美股 (gb) 数据索引
        self.US_NAME_IDX = 0
        self.US_PRICE_IDX = 1
        self.US_DATETIME_TZ_IDX = 25  # 例如: "Jul 21 05:15PM EDT"
        self.US_YEAR_IDX = 29         # 例如: "2025"

    def _to_float(self, value: str, default: float = 0.0) -> float:
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _parse_hk_stock(self, data_parts: List[str]) -> Optional[SinaPriceDataPoint]:
        """解析港股 (rt_hk) 数据。"""
        if len(data_parts) <= max(self.HK_DATE_IDX, self.HK_TIME_IDX):
            return None

        try:
            name = data_parts[self.HK_NAME_IDX]
            price = self._to_float(data_parts[self.HK_PRICE_IDX])
            date_str = data_parts[self.HK_DATE_IDX].replace("/", "-")
            time_str = data_parts[self.HK_TIME_IDX]
            
            datetime_str = f"{date_str} {time_str}"
            # 港股直接赋予时区信息
            naive_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            timestamp = self.BEIJING_TZ.localize(naive_dt)

            return SinaPriceDataPoint(name=name, time=timestamp, price=price)
        except (ValueError, IndexError) as e:
            print(f"解析港股数据时出错: {e}")
            return None

    def _parse_us_stock(self, data_parts: List[str]) -> Optional[SinaPriceDataPoint]:
        """
        解析美股 (gb) 数据。
        """
        if len(data_parts) <= max(self.US_DATETIME_TZ_IDX, self.US_YEAR_IDX):
            return None

        try:
            name = data_parts[self.US_NAME_IDX]
            price = self._to_float(data_parts[self.US_PRICE_IDX])
            
            year_str = data_parts[self.US_YEAR_IDX]
            datetime_with_tz_str = data_parts[self.US_DATETIME_TZ_IDX]
            
            parts = datetime_with_tz_str.split()

            if len(parts) != 4:
                raise ValueError(f"未知的美股时间格式: {datetime_with_tz_str}")
            
            datetime_str_no_tz = " ".join(parts[:-1])
            tz_abbr = parts[-1]  # "EDT"

            source_tz = self.US_TZ_MAP.get(tz_abbr)
            if not source_tz:
                raise ValueError(f"无法识别的美股时区缩写: {tz_abbr}")

            full_datetime_str = f"{year_str} {datetime_str_no_tz}"
            naive_dt = datetime.strptime(full_datetime_str, "%Y %b %d %I:%M%p")

            source_aware_dt = source_tz.localize(naive_dt)
            beijing_dt = source_aware_dt.astimezone(self.BEIJING_TZ)

            return SinaPriceDataPoint(name=name, time=beijing_dt, price=price)
        except (ValueError, IndexError, KeyError) as e:
            print(f"解析美股数据时出错: {e}")
            return None

    def fetch_sina_quotes(self, codes: List[str]) -> Dict[str, SinaPriceDataPoint]:
        """
        从新浪财经获取指定代码列表的实时行情。

        参数:
            codes (List[str]): 股票/指数代码列表, 例如 ['rt_hkHSI', 'gb_ixic']。

        返回:
            Dict[str, SinaPriceDataPoint]: 一个字典，键为完整的股票代码，值为 SinaPriceDataPoint 对象。
                                        如果请求失败或无数据解析，则返回空字典。
        """
        if not codes:
            return {}

        timestamp = int(time.time() * 1000)
        list_str = ",".join(codes)
        url = f"{self.SINA_API_URL}?rn={timestamp}&list={list_str}"

        try:
            response = requests.get(url, headers=self.HEADERS, timeout=5)
            response.raise_for_status()
            response.encoding = 'gbk'

            results = {}
            matches = re.findall(r'var hq_str_([^=]+)="([^"]*)"', response.text)

            requested_codes_set = set(codes)

            for code_from_api, data_str in matches:
                if code_from_api not in requested_codes_set:
                    print(f"警告: 收到未在请求列表中的代码 '{code_from_api}' 的数据，已跳过。")
                    continue

                if not data_str:
                    print(f"警告: 代码 {code_from_api} 未返回有效数据。")
                    continue

                data_parts = data_str.split(',')
                
                point = None
                # 根据代码前缀分发到对应的解析器
                if code_from_api.startswith('rt_hk'):
                    point = self._parse_hk_stock(data_parts)
                elif code_from_api.startswith('gb_'):
                    point = self._parse_us_stock(data_parts)
                else:
                    print(f"警告: 代码 '{code_from_api}' 没有对应的解析器。")
                    continue
                
                if point:
                    results[code_from_api] = point

            return results

        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {e}")
            return {}
        except Exception as e:
            print(f"获取或解析数据时发生意外错误: {e}")
            return {}

    def get_hsi_quote(self) -> Optional[SinaPriceDataPoint]:
        """获取恒生指数的实时报价。"""
        result = self.fetch_sina_quotes(['rt_hkHSI'])
        return result.get('rt_hkHSI')

    def get_nasdaq_quote(self) -> Optional[SinaPriceDataPoint]:
        """获取纳斯达克综合指数的实时报价。"""
        result = self.fetch_sina_quotes(['gb_ixic'])
        return result.get('gb_ixic')


if __name__ == "__main__":
    client = SinaRealtimeQuoteClient()
    
    stock_codes_to_fetch = [
        'rt_hkHSI',  # 港股：恒生指数
        'gb_ixic',   # 美股：纳斯达克综合指数
    ]
    
    print(f"正在获取行情: {stock_codes_to_fetch}\n")
    quotes = client.fetch_sina_quotes(stock_codes_to_fetch)

    if quotes:
        print("--- 实时行情数据 ---")
        pprint(quotes)
        print("---------------------\n")
    else:
        print("获取行情数据失败。")
