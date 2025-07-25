from typing import Optional
from .headers import headers
import requests
import json
from datetime import datetime, timedelta
from .price_data_point import SinaPriceDataPoint


class WenCaiClient:
    

    def parse_quote_data(self, raw_string: str) -> list[SinaPriceDataPoint]:
        """
        解析 quotebridge 格式的字符串，提取时间和价格数据。

        Args:
            raw_string: 包含股票/指数数据的原始字符串。

        Returns:
            一个包含 SinaPriceDataPoint 对象的列表，按时间顺序排列。
        """
        try:
            start_index = raw_string.find('(')
            end_index = raw_string.rfind(')')
            if start_index == -1 or end_index == -1:
                raise ValueError("输入字符串格式无效，找不到'('或')'")
            json_str = raw_string[start_index + 1: end_index]
            data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            raise SyntaxError("JSON解析失败: {}".format(e))

        data_key = list(data.keys())[0]
        market_data = data[data_key]

        # 获取基础日期
        current_date = datetime.strptime(
            market_data.get("date"),
            "%Y%m%d"
        ).date()

        # 时间序列数据
        time_series_data = market_data.get("data", "")
        if not time_series_data:
            return []

        results = []
        records = time_series_data.strip().split(';')

        last_time_str = "0000"

        for record in records:
            if not record:
                continue

            parts = record.split(',')
            time_str = parts[0]
            price_str = parts[1]

            # 如果当前时间小于上一个时间（例如从 2359 -> 0000），说明日期加一天
            if time_str < last_time_str:
                current_date += timedelta(days=1)

            # 组合日期和时间
            full_datetime_str = f"{current_date.strftime('%Y%m%d')}{time_str}"
            timestamp = datetime.strptime(full_datetime_str, "%Y%m%d%H%M")

            price = float(price_str)

            results.append(SinaPriceDataPoint(
                name=data_key,
                time=timestamp,
                price=price)
            )

            last_time_str = time_str

        return results

    def get_data(self, type: str) -> Optional[list[SinaPriceDataPoint]]:
        """
        发送请求并解析数据
        """
        url = 'https://d.10jqka.com.cn/v6/time/{}/last.js'.format(type)
        request_headers = headers()

        params = {
            'hexin-v': request_headers.get('hexin-v')
        }

        response = requests.get(url, params=params, headers=request_headers)
        return self.parse_quote_data(response.text)

    def get_hsi_kline(self) -> list[SinaPriceDataPoint]:
        """获取恒生指数分钟级K线"""
        return self.get_data('176_HSI')

    def get_nasdaq_kline(self) -> list[SinaPriceDataPoint]:
        """获取纳斯达克指数分钟级K线"""
        return self.get_data('88_IXIC')


if __name__ == "__main__":
    client = WenCaiClient()  # 创建实例

    print("恒生指数分钟级K线:")
    print(client.get_hsi_kline())
    print("纳斯达克指数分钟级K线:")
    print(client.get_nasdaq_kline())
