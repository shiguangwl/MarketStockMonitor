from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from datetime import datetime, time as time_obj, timedelta
import requests
import re
import time
import random
import pytz
import logging
from wen_cai.price_data_point import ParsedTradingRule, TradingDay, CurrentStatus

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DataSource:
    """数据源信息"""
    id: str
    name: str
    description: str
    api_url: str
    api_key: str
    timezone: str



class TradingHoursClient:
    """
    股市交易时间工具类
    提供清晰的API，用于获取节假日安排和指定时间的市场交易状态。
    """
    
    # 关闭状态关键词
    CLOSED_KEYWORDS = {
        "休市", "收盘", "停市", "未开盘", "假期", "休假", 
        "竞价", "节", "日", "提前", "延迟" , "盘前"
    }
    
    def __init__(self, cache_ttl: int = 3600):
        self.data_sources = self._init_data_sources()
        self.cache: Dict[str, Tuple[List[ParsedTradingRule], float]] = {}
        self.cache_ttl = cache_ttl
        
    def _generate_random_param(self) -> str:
        """必要的请求参数"""
        return f"{int(time.time() * 1000)}{random.random()}"
    
    def _init_data_sources(self) -> Dict[str, DataSource]:
        """初始化数据源"""
        return {
            "HK": DataSource(
                "HK", 
                "香港股市", 
                "香港联合交易所", 
                "https://hq.sinajs.cn/random={}&list=market_stock_hk", 
                "hk", 
                "Asia/Hong_Kong"
            ),
            "NASDAQ": DataSource(
                "NASDAQ", 
                "纳斯达克", 
                "纳斯达克交易所", 
                "https://hq.sinajs.cn/random={}&list=market_stock_nsq", 
                "nsq", 
                "America/New_York"
            ),
        }
    
    def _is_cache_valid(self, market: str) -> bool:
        """检查缓存是否有效"""
        return (market in self.cache and 
                time.time() - self.cache[market][1] < self.cache_ttl)
    
    def _update_cache(self, market: str, rules: List[ParsedTradingRule]) -> None:
        """更新缓存"""
        self.cache[market] = (rules, time.time())
    
    def _fetch_trading_rules(self, market: str) -> List[ParsedTradingRule]:
        """获取交易日历"""
        # 处理市场别名
        if market == "HSI":
            market = "HK"
            
        if market not in self.data_sources:
            raise ValueError(f"不支持的市场: {market}")
            
        # 检查缓存
        if self._is_cache_valid(market):
            return self.cache[market][0]
        
        data_source = self.data_sources[market]
        url = data_source.api_url.format(self._generate_random_param())
        
        try:
            response = requests.get(
                url, 
                headers={
                    "User-Agent": "Mozilla/5.0", 
                    "Referer": "https://stock.finance.sina.com.cn"
                }, 
                timeout=10
            )
            response.raise_for_status()
            parsed_rules = self._parse_trading_data(response.text, data_source)
            
            # 只有获取到规则时才更新缓存
            if parsed_rules: 
                self._update_cache(market, parsed_rules)
                
            return parsed_rules
        except requests.RequestException as e:
            logger.error(f"获取 {market} 交易时间数据失败: {e}")
            return []
    
    def _parse_trading_data(self, data: str, source: DataSource) -> List[ParsedTradingRule]:
        """解析交易数据"""
        pattern = rf'var hq_str_market_stock_{source.api_key}="([^"]+)";'
        match = re.search(pattern, data)
        
        if not match:
            logger.warning(f"未能在返回数据中找到 {source.name} 的规则。")
            return []
            
        content = match.group(1).split('|', 1)
        rule_string = content[1] if len(content) > 1 else content[0]
        
        parsed_rules = []
        for rule_str in rule_string.strip().split(';'):
            if not rule_str.strip():
                continue
                
            parts = rule_str.split(',')
            if len(parts) >= 3:
                parsed_rules.append(ParsedTradingRule(
                    date_pattern=parts[0].strip(),
                    start_time=parts[1].strip(),
                    end_time=parts[2].strip(),
                    description=parts[3].strip() if len(parts) > 3 else "交易中"
                ))
        return parsed_rules

    def _time_in_range(self, current: str, start: str, end: str) -> bool:
        """检查当前时间是否在指定的时间范围内"""
        # 处理 24:00:00 特殊情况
        if end == "24:00:00":
            end = "23:59:59"
            
        try:
            current_t, start_t, end_t = map(time_obj.fromisoformat, [current, start, end])
        except ValueError as e:
            logger.error(f"时间格式错误: {e}")
            return False
            
        # 处理跨日情况（如 23:00:00 - 01:00:00）
        if start_t <= end_t:
            return start_t <= current_t < end_t
        else:
            return current_t >= start_t or current_t < end_t

    def _get_status_for_datetime(self, market: str, target_market_time: datetime) -> CurrentStatus:
        """
        [内部核心方法] 获取指定市场在特定时区时间点的状态。
        """
        all_rules = self._fetch_trading_rules(market)
        if not all_rules:
            return CurrentStatus(False, "无法获取交易规则", target_market_time, None)

        current_time_str = target_market_time.strftime("%H:%M:%S")
        today_date_str = target_market_time.strftime("%Y-%m-%d")
        today_weekday_str = f"w{(target_market_time.weekday() + 1) % 7}"

        # 按优先级筛选规则
        rule_groups = [
            [r for r in all_rules if r.date_pattern == today_date_str],     # 特定日期
            [r for r in all_rules if r.date_pattern == today_weekday_str],  # 星期几
            [r for r in all_rules if r.date_pattern == '*']                 # 默认规则
        ]
        
        # 找到第一个非空的规则组
        applicable_rules = next((rules for rules in rule_groups if rules), [])

        # 查找匹配的规则
        matched_rule = next(
            (rule for rule in applicable_rules 
             if self._time_in_range(current_time_str, rule.start_time, rule.end_time)), 
            None
        )
        
        if matched_rule:
            description = matched_rule.description
            # 判断是否为开盘状态
            is_open = not any(keyword in description for keyword in self.CLOSED_KEYWORDS)
            
            return CurrentStatus(is_open, description, target_market_time, matched_rule)
        
        return CurrentStatus(False, "状态未知", target_market_time, None)

    def _offset_time(self, date_str: str, offset_str: str, time_timezone: str, to_timezone: str) -> datetime:
        """
        将指定地区(time_timezone)的日期(date_str)添加偏移(offset_str)后转换为指定时区(to_timezone)的datetime对象
        """
        # 处理 "24:00:00" 的特殊情况
        if offset_str == "24:00:00":
            current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            next_day = current_date + timedelta(days=1)
            date_str = next_day.strftime("%Y-%m-%d")
            offset_str = "00:00:00"

        # 日期和时间字符串合并
        full_datetime_str = f"{date_str} {offset_str}"
        try:
            naive_dt = datetime.strptime(full_datetime_str, "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            raise ValueError(f"无效的日期或时间格式: {date_str} {offset_str}") from e

        source_tz = pytz.timezone(time_timezone)
        aware_source_dt = source_tz.localize(naive_dt)

        target_tz = pytz.timezone(to_timezone)
        
        return aware_source_dt.astimezone(target_tz)

    def get_special_holidays(self, market: str, to_timezone: str = "Asia/Shanghai") -> List[TradingDay]:
        """
        获取指定市场的特殊节假日安排列表。
        """
        # 处理市场别名
        original_market = market
        if market == "HSI":
            market = "HK"
            
        all_rules = self._fetch_trading_rules(market)
        date_pattern_regex = r'^\d{4}-\d{2}-\d{2}$'
        special_day_rules = [r for r in all_rules if re.match(date_pattern_regex, r.date_pattern)]
        
        if market not in self.data_sources:
            raise ValueError(f"不支持的市场: {original_market}")
            
        time_timezone = self.data_sources[market].timezone
        
        result = []
        for r in special_day_rules:
            try:
                special_day = TradingDay(
                    self._offset_time(r.date_pattern, r.start_time, time_timezone, to_timezone),
                    self._offset_time(r.date_pattern, r.end_time, time_timezone, to_timezone),
                    r.description
                )
                result.append(special_day)
            except ValueError as e:
                logger.error(f"处理特殊交易日时出错: {e}")
                continue
                
        return result
    
    def get_all_trading_days(self, market: str) -> List[TradingDay]:
        """
        获取指定市场的所有交易日。
        """
        # 处理市场别名
        if market == "HSI":
            market = "HK"
            
        if market not in self.data_sources:
            raise ValueError(f"不支持的市场: {market}")
            
        all_rules = self._fetch_trading_rules(market)
        time_timezone = self.data_sources[market].timezone
        
        result = []
        for rule in all_rules:
            # 只处理特定日期的规则
            if re.match(r'^\d{4}-\d{2}-\d{2}$', rule.date_pattern):
                try:
                    special_day = TradingDay(
                        self._offset_time(rule.date_pattern, rule.start_time, time_timezone, "Asia/Shanghai"),
                        self._offset_time(rule.date_pattern, rule.end_time, time_timezone, "Asia/Shanghai"),
                        rule.description
                    )
                    result.append(special_day)
                except ValueError as e:
                    logger.error(f"处理特殊交易日时出错: {e}")
                    continue
                    
        return result
    
    def get_next_opening_time(self, market: str) -> Optional[ParsedTradingRule]:
        """
        获取指定市场的下一次开盘时间。
        此方法会首先查找常规交易日（周一至周五），然后排除掉特殊的节假日，
        并处理提前收盘等特殊情况。

        Args:
            market (str): 市场标识 (例如 "HK", "NASDAQ", "HSI").

        Returns:
            Optional[ParsedTradingRule]: 返回下一个开盘时间的交易规则对象，
                                        其中 date_pattern 会被替换为具体的日期 (YYYY-MM-DD)。
                                        如果在未来一年内未找到开盘时间，则返回 None。
        """
        # 1. 预处理规则
        original_market = market
        if market == "HSI":
            market = "HK"
            
        if market not in self.data_sources:
            raise ValueError(f"不支持的市场: {original_market}")
            
        all_rules = self._fetch_trading_rules(market)
        if not all_rules:
            return None

        # 将规则分为特殊日期规则和常规规则
        date_pattern_regex = r'^\d{4}-\d{2}-\d{2}$'
        special_day_rules = [r for r in all_rules if re.match(date_pattern_regex, r.date_pattern)]
        regular_rules = [r for r in all_rules if not re.match(date_pattern_regex, r.date_pattern)]
        
        # 提取全天休市的特殊日期
        full_day_holidays = set()
        for rule in special_day_rules:
            is_holiday_desc = any(keyword in rule.description for keyword in self.CLOSED_KEYWORDS)
            is_full_day = rule.start_time == "00:00:00" and rule.end_time == "24:00:00"
            if is_holiday_desc and is_full_day:
                full_day_holidays.add(rule.date_pattern)

        # 2. 循环查找下一个开盘日
        data_source = self.data_sources[market]
        market_tz = pytz.timezone(data_source.timezone)
        now_market_time = datetime.now(market_tz)
        
        for i in range(365): # 搜索未来一年
            target_date = now_market_time.date() + timedelta(days=i)
            target_date_str = target_date.strftime("%Y-%m-%d")

            # 3. 检查是否为全天假日
            if target_date_str in full_day_holidays:
                continue

            # 4. 查找当天的常规开盘规则
            # (weekday + 1) % 7 => Mon(0)->w1, ..., Sun(6)->w0
            target_weekday_str = f"w{(target_date.weekday() + 1) % 7}"
            
            # 按优先级查找适用规则 (星期 > 通用)
            applicable_regular_rules = [r for r in regular_rules if r.date_pattern == target_weekday_str]
            if not applicable_regular_rules:
                applicable_regular_rules = [r for r in regular_rules if r.date_pattern == '*']
            
            applicable_regular_rules.sort(key=lambda r: r.start_time)
            
            # 5. 遍历常规规则，并用特殊规则修正
            for regular_rule in applicable_regular_rules:
                is_opening_rule = not any(keyword in regular_rule.description for keyword in self.CLOSED_KEYWORDS)
                if not is_opening_rule:
                    continue

                try:
                    start_time = time_obj.fromisoformat(regular_rule.start_time)
                except ValueError:
                    continue

                is_today = (i == 0)
                if is_today and now_market_time.time() >= start_time:
                    continue # 开盘时间已过

                # 找到一个潜在的开盘时间，现在检查特殊规则
                final_rule = regular_rule
                
                # 查找当天是否有特殊规则（非全天休市，例如半日市）
                day_specific_rules = [r for r in special_day_rules if r.date_pattern == target_date_str and r.date_pattern not in full_day_holidays]
                if day_specific_rules:
                    # 假设当天的第一个特殊规则就是修正规则
                    final_rule = day_specific_rules[0]

                return ParsedTradingRule(
                    date_pattern=target_date_str,
                    start_time=final_rule.start_time,
                    end_time=final_rule.end_time,
                    description=final_rule.description
                )

        return None

    def clear_trading_rules_cache(self) -> None:
        """
        清除交易规则缓存。
        """
        self.cache.clear()
    
    def get_current_trading_status(self, market: str) -> CurrentStatus:
        """
        获取指定市场当前的详细交易状态。
        """
        
        if market == "HSI":
            return self.get_current_trading_status("HK")
    
        if market not in self.data_sources:
            raise ValueError(f"不支持的市场: {market}")
        
        data_source = self.data_sources[market]
        market_tz = pytz.timezone(data_source.timezone)
        now_market_time = datetime.now(market_tz)
        
        return self._get_status_for_datetime(market, now_market_time)

    def get_status_at_time(self, market: str, time_str: str, timezone: str = "Asia/Shanghai") -> CurrentStatus:
        """
        获取指定市场在特定时间点的详细交易状态。
        """
        # 处理市场别名
        original_market = market
        if market == "HSI":
            market = "HK"
            
        if market not in self.data_sources:
            raise ValueError(f"不支持的市场: {original_market}")

        try:
            naive_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            local_tz = pytz.timezone(timezone)
            local_dt = local_tz.localize(naive_dt)

            data_source = self.data_sources[market]
            market_tz = pytz.timezone(data_source.timezone)
            target_market_time = local_dt.astimezone(market_tz)

            return self._get_status_for_datetime(market, target_market_time)

        except ValueError as e:
            raise ValueError("时间字符串格式不正确，请使用 'YYYY-MM-DD HH:MM:SS'") from e
        except Exception as e:
            logger.error(f"处理时间时出错: {e}")
            return CurrentStatus(False, f"处理时间时出错: {e}", datetime.now(), None)


def main():
    """主函数示例"""
    util = TradingHoursClient()

    try:
        # 获取纳斯达克市场安排
        print("=== 纳斯达克特殊交易日 ===")
        special_days = util.get_special_holidays("NASDAQ")
        for day in special_days[:5]:  # 只显示前5个
            print(day)
        print()
        
        # 获取香港市场安排
        print("=== 香港特殊交易日 ===")
        special_days = util.get_special_holidays("HK")
        for day in special_days[:5]:  # 只显示前5个
            print(day)
        print()

        print("--- 1. 获取当前状态 (示例) ---")
        hk_status_now = util.get_current_trading_status("HK")
        open_str_now = "✅ 开盘" if hk_status_now.is_open else "❌ 关闭"
        print(f"香港当前状态: {open_str_now} - {hk_status_now.status_text} (当地时间: {hk_status_now.market_time.strftime('%H:%M')})")
        print("-" * 30)
        
        nasdaq_status_now = util.get_current_trading_status("NASDAQ")
        nasdaq_status_now_str = "✅ 开盘" if nasdaq_status_now.is_open else "❌ 关闭"
        print(f"纳斯达克当前状态: {nasdaq_status_now_str} - {nasdaq_status_now.status_text} (当地时间: {nasdaq_status_now.market_time.strftime('%H:%M')})")
        print("-" * 30)
        
        print("\n--- 2. 获取指定时间点的状态 ---")
        # 示例 A: 检查香港国庆节
        time_to_check_a = "2024-10-01 10:00:00"
        print(f"查询时间 (服务器本地): {time_to_check_a}")
        hk_status_holiday = util.get_status_at_time("HK", time_to_check_a)
        open_str_a = "✅ 开盘" if hk_status_holiday.is_open else "❌ 关闭"
        print(f"查询结果: 在香港当地时间 {hk_status_holiday.market_time.strftime('%Y-%m-%d %H:%M')}, 市场状态为: {open_str_a} - {hk_status_holiday.status_text}\n")

        # 示例 B: 检查纳斯达克正常交易时间
        time_to_check_b = "2025-07-23 23:00:00"
        print(f"查询时间 (服务器本地): {time_to_check_b}")
        nasdaq_status_open = util.get_status_at_time("NASDAQ", time_to_check_b)
        open_str_b = "✅ 开盘" if nasdaq_status_open.is_open else "❌ 关闭"
        print(f"查询结果: 在纽约当地时间 {nasdaq_status_open.market_time.strftime('%Y-%m-%d %H:%M')}, 市场状态为: {open_str_b} - {nasdaq_status_open.status_text}\n")

        # 示例 C: 检查纳斯达克感恩节
        time_to_check_c = "2024-11-28 23:00:00"
        print(f"查询时间 (服务器本地): {time_to_check_c}")
        nasdaq_status_thanksgiving = util.get_status_at_time("NASDAQ", time_to_check_c)
        open_str_c = "✅ 开盘" if nasdaq_status_thanksgiving.is_open else "❌ 关闭"
        print(f"查询结果: 在纽约当地时间 {nasdaq_status_thanksgiving.market_time.strftime('%Y-%m-%d %H:%M')}, 市场状态为: {open_str_c} - {nasdaq_status_thanksgiving.status_text}")
        print("-" * 30)
        
        # 香港周末
        print("香港周末:")
        time_to_check_d = "2025-07-26 10:00:00"
        print(f"查询时间 (服务器本地): {time_to_check_d}")
        hk_status_weekend = util.get_status_at_time("HK", time_to_check_d)
        open_str_d = "✅ 开盘" if hk_status_weekend.is_open else "❌ 关闭"
        print(f"查询结果: 在香港当地时间 {hk_status_weekend.market_time.strftime('%Y-%m-%d %H:%M')}, 市场状态为: {open_str_d} - {hk_status_weekend.status_text}")
        print("-" * 30)
        
        # 纳斯达克周末
        print("纳斯达克周末:")
        time_to_check_e = "2025-07-27 23:00:00"
        print(f"查询时间 (服务器本地): {time_to_check_e}")
        nasdaq_status_weekend = util.get_status_at_time("NASDAQ", time_to_check_e)
        open_str_e = "✅ 开盘" if nasdaq_status_weekend.is_open else "❌ 关闭"
        print(f"查询结果: 在纽约当地时间 {nasdaq_status_weekend.market_time.strftime('%Y-%m-%d %H:%M')}, 市场状态为: {open_str_e} - {nasdaq_status_weekend.status_text}")
        print("-" * 30)
        
        # 边界测试
        print("=== 边界测试 ===")
        time_to_check_f = "2025-07-24 11:59:59"
        print(f"查询时间 (服务器本地): {time_to_check_f}")
        hk_status_boundary = util.get_status_at_time("HK", time_to_check_f)
        open_str_f = "✅ 开盘" if hk_status_boundary.is_open else "❌ 关闭"
        print(f"查询结果: 在香港当地时间 {hk_status_boundary.market_time.strftime('%Y-%m-%d %H:%M')}, 市场状态为: {open_str_f} - {hk_status_boundary.status_text}")
        print("-" * 30)

        time_to_check_g = "2025-07-24 21:29:00"
        print(f"查询时间 (服务器本地): {time_to_check_g}")
        nasdaq_status_boundary = util.get_status_at_time("NASDAQ", time_to_check_g)
        open_str_g = "✅ 开盘" if nasdaq_status_boundary.is_open else "❌ 关闭"
        print(f"查询结果: 在纳斯达克当地时间 {nasdaq_status_boundary.market_time.strftime('%Y-%m-%d %H:%M')}, 市场状态为: {open_str_g} - {nasdaq_status_boundary.status_text}")
        print("-" * 30)
        
        # 跨日时间测试
        print("=== 跨日时间测试 ===")
        time_to_check_h = "2025-07-24 23:59:59"
        print(f"查询时间 (服务器本地): {time_to_check_h}")
        nasdaq_status_late = util.get_status_at_time("NASDAQ", time_to_check_h, "Asia/Shanghai")
        open_str_h = "✅ 开盘" if nasdaq_status_late.is_open else "❌ 关闭"
        print(f"查询结果: 在纳斯达克当地时间 {nasdaq_status_late.market_time.strftime('%Y-%m-%d %H:%M')}, 市场状态为: {open_str_h} - {nasdaq_status_late.status_text}")
        print("-" * 30)
        
        # 错误输入测试
        print("=== 错误输入测试 ===")
        try:
            util.get_status_at_time("INVALID", "2025-07-24 10:00:00")
        except ValueError as e:
            print(f"捕获到预期错误: {e}")
            
        try:
            util.get_status_at_time("HK", "invalid-time-format")
        except ValueError as e:
            print(f"捕获到预期错误: {e}")
        print("-" * 30)
        
    except Exception as e:
        print(f"程序执行出错: {e}")


if __name__ == "__main__":
    main()
