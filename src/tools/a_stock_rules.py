"""
A股交易规则模块

包含A股特有的交易规则：
1. 涨跌停限制
2. T+1交易规则
3. 交易时间
4. 停牌检测
5. ST股票处理
"""

import datetime
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AStockTradingRules:
    """A股交易规则配置"""

    # 涨跌停限制（百分比）
    normal_price_limit: float = 10.0  # 普通股票
    st_price_limit: float = 5.0  # ST股票
    gem_price_limit: float = 20.0  # 创业板/科创板

    # 交易时间
    morning_start: str = "09:30"
    morning_end: str = "11:30"
    afternoon_start: str = "13:00"
    afternoon_end: str = "15:00"

    # T+1规则
    t_plus_one: bool = True  # A股实行T+1，当天买入的股票不能当天卖出

    # 最小交易单位
    min_trade_unit: int = 100  # 最小交易单位为100股（1手）

    # 价格精度
    price_precision: int = 2  # 价格精确到小数点后2位


def get_stock_type(ticker: str) -> str:
    """
    判断股票类型

    返回：
        "normal": 普通主板股票
        "gem": 创业板/科创板股票
        "st": ST股票
        "bj": 北交所股票
    """
    ticker = ticker.upper().strip()

    # 移除交易所后缀
    for suffix in [".SH", ".SZ", ".BJ"]:
        if ticker.endswith(suffix):
            ticker = ticker[:-3]
            break

    # 判断股票类型
    if ticker.startswith("688"):  # 科创板
        return "gem"
    elif ticker.startswith("300"):  # 创业板
        return "gem"
    elif ticker.startswith("ST") or ticker.startswith("*ST"):  # ST股票
        return "st"
    elif ticker.startswith(("4", "8")):  # 北交所
        return "bj"
    else:
        return "normal"


def get_price_limit(ticker: str, rules: AStockTradingRules = None) -> float:
    """
    获取股票的涨跌停限制

    参数：
        ticker: 股票代码
        rules: 交易规则配置

    返回：
        涨跌停限制百分比
    """
    if rules is None:
        rules = AStockTradingRules()

    stock_type = get_stock_type(ticker)

    if stock_type == "st":
        return rules.st_price_limit
    elif stock_type == "gem":
        return rules.gem_price_limit
    elif stock_type == "bj":
        return rules.gem_price_limit  # 北交所也是20%
    else:
        return rules.normal_price_limit


def calculate_price_limits(
    ticker: str,
    reference_price: float,
    rules: AStockTradingRules = None
) -> Tuple[float, float]:
    """
    计算涨跌停价格

    参数：
        ticker: 股票代码
        reference_price: 参考价格（昨日收盘价或发行价）
        rules: 交易规则配置

    返回：
        (涨停价, 跌停价)
    """
    if rules is None:
        rules = AStockTradingRules()

    limit_pct = get_price_limit(ticker, rules)
    limit_factor = limit_pct / 100.0

    # 计算涨跌停价格，精确到小数点后2位
    upper_limit = round(reference_price * (1 + limit_factor), rules.price_precision)
    lower_limit = round(reference_price * (1 - limit_factor), rules.price_precision)

    return upper_limit, lower_limit


def is_trading_time(dt: datetime.datetime = None, rules: AStockTradingRules = None) -> bool:
    """
    判断是否在交易时间内

    参数：
        dt: 时间（默认当前时间）
        rules: 交易规则配置

    返回：
        是否在交易时间内
    """
    if dt is None:
        dt = datetime.datetime.now()

    if rules is None:
        rules = AStockTradingRules()

    # 检查是否为工作日（周一至周五）
    if dt.weekday() >= 5:  # 周六、周日
        return False

    # 检查是否在交易时间段内
    current_time = dt.strftime("%H:%M")

    # 上午交易时间
    if rules.morning_start <= current_time <= rules.morning_end:
        return True

    # 下午交易时间
    if rules.afternoon_start <= current_time <= rules.afternoon_end:
        return True

    return False


def can_sell_today(buy_date: datetime.date, sell_date: datetime.date, rules: AStockTradingRules = None) -> bool:
    """
    判断是否可以卖出（T+1规则）

    参数：
        buy_date: 买入日期
        sell_date: 欲卖出日期
        rules: 交易规则配置

    返回：
        是否可以卖出
    """
    if rules is None:
        rules = AStockTradingRules()

    if not rules.t_plus_one:
        return True  # 如果不实行T+1，可以当天卖出

    # A股实行T+1，买入后至少要等到下一个交易日才能卖出
    return sell_date > buy_date


def normalize_trade_quantity(quantity: int, rules: AStockTradingRules = None) -> int:
    """
    规范化交易数量（调整为100股的整数倍）

    参数：
        quantity: 原始数量
        rules: 交易规则配置

    返回：
        规范化后的数量
    """
    if rules is None:
        rules = AStockTradingRules()

    # 调整为最小交易单位的整数倍
    normalized = (quantity // rules.min_trade_unit) * rules.min_trade_unit

    return normalized


def validate_trade_price(
    ticker: str,
    price: float,
    reference_price: float,
    rules: AStockTradingRules = None
) -> Tuple[bool, Optional[float]]:
    """
    验证交易价格是否在涨跌停范围内

    参数：
        ticker: 股票代码
        price: 交易价格
        reference_price: 参考价格
        rules: 交易规则配置

    返回：
        (是否有效, 调整后的价格)
    """
    if rules is None:
        rules = AStockTradingRules()

    upper_limit, lower_limit = calculate_price_limits(ticker, reference_price, rules)

    if lower_limit <= price <= upper_limit:
        return True, price

    # 如果超出涨跌停，调整到边界
    if price > upper_limit:
        logger.warning(f"价格 {price} 超过涨停价 {upper_limit}，调整为涨停价")
        return False, upper_limit
    else:
        logger.warning(f"价格 {price} 低于跌停价 {lower_limit}，调整为跌停价")
        return False, lower_limit


def get_next_trading_day(date: datetime.date = None) -> datetime.date:
    """
    获取下一个交易日

    注意：此函数不考虑节假日，仅考虑周末
    实际应用中应结合交易日历

    参数：
        date: 当前日期（默认今天）

    返回：
        下一个交易日
    """
    if date is None:
        date = datetime.date.today()

    next_day = date + datetime.timedelta(days=1)

    # 如果是周末，跳到周一
    while next_day.weekday() >= 5:
        next_day += datetime.timedelta(days=1)

    return next_day


def format_a_stock_ticker(ticker: str) -> str:
    """
    格式化A股股票代码

    将各种格式的股票代码统一为标准格式（带交易所后缀）

    例如：
        600519 -> 600519.SH
        sh600519 -> 600519.SH
        000001 -> 000001.SZ
    """
    ticker = ticker.upper().strip()

    # 移除可能的前缀/后缀
    for prefix in ["SH", "SZ", "BJ"]:
        if ticker.startswith(prefix):
            ticker = ticker[len(prefix):]
        if ticker.endswith(f".{prefix}"):
            ticker = ticker[:-4]

    # 确保是6位数字
    if len(ticker) != 6:
        return ticker

    # 根据代码判断交易所
    if ticker.startswith("6"):
        return f"{ticker}.SH"
    elif ticker.startswith(("0", "3")):
        return f"{ticker}.SZ"
    elif ticker.startswith(("4", "8")):
        return f"{ticker}.BJ"
    else:
        return ticker


class AStockTradingConstraints:
    """
    A股交易约束检查器

    用于在交易执行前检查各种约束条件
    """

    def __init__(self, rules: AStockTradingRules = None):
        self.rules = rules or AStockTradingRules()
        self._suspended_stocks = set()  # 停牌股票集合
        self._st_stocks = set()  # ST股票集合

    def add_suspended_stock(self, ticker: str):
        """添加停牌股票"""
        self._suspended_stocks.add(format_a_stock_ticker(ticker))

    def remove_suspended_stock(self, ticker: str):
        """移除停牌股票"""
        self._suspended_stocks.discard(format_a_stock_ticker(ticker))

    def is_suspended(self, ticker: str) -> bool:
        """检查股票是否停牌"""
        return format_a_stock_ticker(ticker) in self._suspended_stocks

    def add_st_stock(self, ticker: str):
        """添加ST股票"""
        self._st_stocks.add(format_a_stock_ticker(ticker))

    def is_st_stock(self, ticker: str) -> bool:
        """检查是否为ST股票"""
        formatted = format_a_stock_ticker(ticker)
        if formatted in self._st_stocks:
            return True
        # 也检查股票代码本身是否以ST开头
        return get_stock_type(ticker) == "st"

    def validate_order(
        self,
        ticker: str,
        action: str,
        quantity: int,
        price: float,
        reference_price: float,
        buy_date: datetime.date = None,
        sell_date: datetime.date = None,
    ) -> Tuple[bool, str]:
        """
        验证订单是否符合A股交易规则

        参数：
            ticker: 股票代码
            action: 交易动作（BUY/SELL）
            quantity: 数量
            price: 价格
            reference_price: 参考价格
            buy_date: 买入日期（用于T+1检查）
            sell_date: 卖出日期

        返回：
            (是否有效, 错误信息)
        """
        # 检查停牌
        if self.is_suspended(ticker):
            return False, f"股票 {ticker} 已停牌，无法交易"

        # 检查交易数量
        if quantity < self.rules.min_trade_unit:
            return False, f"交易数量 {quantity} 小于最小交易单位 {self.rules.min_trade_unit}"

        if quantity % self.rules.min_trade_unit != 0:
            return False, f"交易数量 {quantity} 不是 {self.rules.min_trade_unit} 的整数倍"

        # 检查价格是否在涨跌停范围内
        is_valid_price, adjusted_price = validate_trade_price(
            ticker, price, reference_price, self.rules
        )
        if not is_valid_price:
            return False, f"价格 {price} 超出涨跌停范围，调整为 {adjusted_price}"

        # 检查T+1规则（卖出时）
        if action.upper() == "SELL":
            if buy_date and sell_date:
                if not can_sell_today(buy_date, sell_date, self.rules):
                    return False, f"T+1规则：买入日期 {buy_date} 的股票不能在 {sell_date} 卖出"

        return True, ""


# 导出便捷函数
__all__ = [
    "AStockTradingRules",
    "get_stock_type",
    "get_price_limit",
    "calculate_price_limits",
    "is_trading_time",
    "can_sell_today",
    "normalize_trade_quantity",
    "validate_trade_price",
    "get_next_trading_day",
    "format_a_stock_ticker",
    "AStockTradingConstraints",
]