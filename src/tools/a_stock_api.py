"""
A股数据源适配器（增强版）

支持多种A股数据源：
1. AKShare - 免费开源，无需API密钥
2. Tushare Pro - 专业数据，需要API密钥
3. 东方财富 - 免费开源

功能增强：
- 数据缓存
- 重试机制
- 异常处理
- 北向资金数据
- 龙虎榜数据
- 板块数据
"""

import datetime
import logging
import os
import time
import pandas as pd
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
import threading

logger = logging.getLogger(__name__)

from src.data.models import (
    Price,
    FinancialMetrics,
    LineItem,
    InsiderTrade,
    CompanyNews,
    CompanyFacts,
)


@dataclass
class NorthboundFlow:
    """北向资金流向数据"""
    date: str
    buy_amount: float  # 买入金额（亿元）
    sell_amount: float  # 卖出金额（亿元）
    net_buy: float  # 净买入（亿元）
    total_balance: Optional[float] = None  # 累计净买入


@dataclass
class DragonTigerItem:
    """龙虎榜数据"""
    ticker: str
    date: str
    close_price: float
    change_pct: float
    turnover_rate: float
    reason: str  # 上榜原因
    net_buy: float  # 净买入金额


@dataclass
class SectorData:
    """板块数据"""
    name: str
    code: str
    change_pct: float
    turnover: float
    leading_stock: str  # 领涨股
    leading_change: float


class DataCache:
    """数据缓存管理器"""

    def __init__(self, ttl_seconds: int = 3600):
        """
        初始化缓存

        参数：
            ttl_seconds: 缓存过期时间（秒），默认1小时
        """
        self._cache: Dict[str, tuple] = {}  # key -> (data, timestamp)
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        with self._lock:
            if key not in self._cache:
                return None
            data, timestamp = self._cache[key]
            if time.time() - timestamp > self._ttl:
                del self._cache[key]
                return None
            return data

    def set(self, key: str, data: Any) -> None:
        """设置缓存数据"""
        with self._lock:
            self._cache[key] = (data, time.time())

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()


# 全局缓存实例
_cache = DataCache()


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        logger.warning(f"{func.__name__} 第{attempt + 1}次尝试失败: {e}，{delay}秒后重试...")
                        time.sleep(delay)
            logger.error(f"{func.__name__} 重试{max_retries}次后仍失败: {last_error}")
            raise last_error
        return wrapper
    return decorator


class AStockDataSource(ABC):
    """A股数据源抽象基类"""

    def __init__(self):
        self._cache = _cache

    @abstractmethod
    def get_prices(self, ticker: str, start_date: str, end_date: str) -> List[Price]:
        """获取价格数据"""
        pass

    @abstractmethod
    def get_financial_metrics(self, ticker: str, end_date: str, period: str = "ttm", limit: int = 10) -> List[FinancialMetrics]:
        """获取财务指标"""
        pass

    @abstractmethod
    def get_company_facts(self, ticker: str) -> Optional[CompanyFacts]:
        """获取公司基本信息"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查数据源是否可用"""
        pass

    def get_northbound_flow(self, days: int = 30) -> List[NorthboundFlow]:
        """获取北向资金流向"""
        return []

    def get_dragon_tiger(self, date: str = None) -> List[DragonTigerItem]:
        """获取龙虎榜数据"""
        return []

    def get_sectors(self) -> List[SectorData]:
        """获取板块数据"""
        return []

    def normalize_ticker(self, ticker: str) -> str:
        """
        规范化股票代码
        支持格式：600519, 600519.SH, sh600519
        """
        ticker = ticker.upper().strip()
        # 移除前缀
        for prefix in ["SH", "SZ", "BJ", "."]:
            if ticker.startswith(prefix):
                ticker = ticker[len(prefix):]
            if ticker.endswith(prefix):
                ticker = ticker[:-len(prefix)]
        return ticker

    def get_exchange(self, ticker: str) -> str:
        """根据股票代码判断交易所"""
        code = self.normalize_ticker(ticker)
        if code.startswith("6"):
            return "SH"  # 上海证券交易所
        elif code.startswith(("0", "3")):
            return "SZ"  # 深圳证券交易所
        elif code.startswith(("4", "8")):
            return "BJ"  # 北京证券交易所
        return "SH"

    def _get_cache_key(self, prefix: str, *args) -> str:
        """生成缓存键"""
        return f"{prefix}:{':'.join(str(a) for a in args)}"


class AKShareDataSource(AStockDataSource):
    """AKShare数据源 - 免费开源"""

    def __init__(self):
        super().__init__()
        self._ak = None
        try:
            import akshare
            self._ak = akshare
            logger.info("AKShare数据源初始化成功")
        except ImportError:
            logger.warning("AKShare未安装，请运行：pip install akshare")
        except Exception as e:
            logger.error(f"AKShare初始化失败: {e}")

    def is_available(self) -> bool:
        return self._ak is not None

    @retry_on_failure(max_retries=3, delay=2.0)
    def get_prices(self, ticker: str, start_date: str, end_date: str) -> List[Price]:
        """获取A股历史价格数据"""
        if not self.is_available():
            return []

        # 检查缓存
        cache_key = self._get_cache_key("prices", ticker, start_date, end_date)
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            code = self.normalize_ticker(ticker)

            # 使用AKShare获取股票历史数据
            df = self._ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="qfq"  # 前复权
            )

            if df is None or df.empty:
                logger.warning(f"AKShare未找到价格数据: {ticker}")
                return []

            prices = []
            for _, row in df.iterrows():
                try:
                    price = Price(
                        open=float(row["开盘"]),
                        close=float(row["收盘"]),
                        high=float(row["最高"]),
                        low=float(row["最低"]),
                        volume=int(row["成交量"]),
                        time=str(row["日期"]),
                    )
                    prices.append(price)
                except (ValueError, KeyError) as e:
                    logger.warning(f"解析价格数据失败: {e}")
                    continue

            # 缓存结果
            self._cache.set(cache_key, prices)
            return prices

        except Exception as e:
            logger.error(f"AKShare获取价格数据失败: {ticker} - {e}")
            return []

    @retry_on_failure(max_retries=3, delay=2.0)
    def get_financial_metrics(self, ticker: str, end_date: str, period: str = "ttm", limit: int = 10) -> List[FinancialMetrics]:
        """获取A股财务指标"""
        if not self.is_available():
            return []

        # 检查缓存
        cache_key = self._get_cache_key("metrics", ticker, end_date, period, limit)
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            code = self.normalize_ticker(ticker)

            # 获取财务指标数据 - 使用 stock_financial_abstract
            df = self._ak.stock_financial_abstract(symbol=code)

            if df is None or df.empty:
                logger.warning(f"AKShare未找到财务指标: {ticker}")
                return []

            # 获取列名（日期列）- 过滤掉非日期列
            date_columns = []
            for col in df.columns:
                if col in ["选股", "指标"]:
                    continue
                # 检查是否为日期格式（YYYYMMDD）
                if isinstance(col, str) and len(col) == 8 and col.isdigit():
                    date_columns.append(col)

            # 创建指标到行的映射
            indicator_col = "指标"
            indicator_map = {}
            for _, row in df.iterrows():
                indicator_name = str(row[indicator_col])
                indicator_map[indicator_name] = row

            metrics_list = []
            for date_col in date_columns[:limit]:
                try:
                    # 辅助函数：获取指标值
                    def get_value(name_patterns: list) -> float:
                        for pattern in name_patterns:
                            for ind_name, row in indicator_map.items():
                                if pattern in ind_name:
                                    val = row.get(date_col)
                                    if val is not None and not pd.isna(val):
                                        return self._safe_float(val)
                        return None

                    metrics = FinancialMetrics(
                        ticker=ticker,
                        report_period=date_col,
                        period=period,
                        currency="CNY",
                        market_cap=None,
                        enterprise_value=None,
                        price_to_earnings_ratio=get_value(["市盈率"]),
                        price_to_book_ratio=get_value(["市净率"]),
                        price_to_sales_ratio=get_value(["市销率"]),
                        enterprise_value_to_ebitda_ratio=None,
                        enterprise_value_to_revenue_ratio=None,
                        free_cash_flow_yield=None,
                        peg_ratio=None,
                        gross_margin=get_value(["毛利率"]),
                        operating_margin=get_value(["营业利润率"]),
                        net_margin=get_value(["净利率", "销售净利率"]),
                        return_on_equity=get_value(["净资产收益率", "ROE"]),
                        return_on_assets=get_value(["总资产净利润率", "ROA"]),
                        return_on_invested_capital=None,
                        asset_turnover=None,
                        inventory_turnover=None,
                        receivables_turnover=None,
                        days_sales_outstanding=None,
                        operating_cycle=None,
                        working_capital_turnover=None,
                        current_ratio=get_value(["流动比率"]),
                        quick_ratio=get_value(["速动比率"]),
                        cash_ratio=None,
                        operating_cash_flow_ratio=None,
                        debt_to_equity=get_value(["资产负债率"]),
                        debt_to_assets=None,
                        interest_coverage=None,
                        revenue_growth=None,
                        earnings_growth=None,
                        book_value_growth=None,
                        earnings_per_share_growth=None,
                        free_cash_flow_growth=None,
                        operating_income_growth=None,
                        ebitda_growth=None,
                        payout_ratio=None,
                        earnings_per_share=get_value(["每股收益"]),
                        book_value_per_share=get_value(["每股净资产"]),
                        free_cash_flow_per_share=None,
                    )
                    metrics_list.append(metrics)
                except Exception as e:
                    logger.warning(f"解析财务指标失败: {e}")
                    continue

            # 缓存结果
            self._cache.set(cache_key, metrics_list)
            return metrics_list

        except Exception as e:
            logger.error(f"AKShare获取财务指标失败: {ticker} - {e}")
            return []

    @retry_on_failure(max_retries=3, delay=2.0)
    def get_company_facts(self, ticker: str) -> Optional[CompanyFacts]:
        """获取A股公司基本信息"""
        if not self.is_available():
            return None

        # 检查缓存
        cache_key = self._get_cache_key("facts", ticker)
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            code = self.normalize_ticker(ticker)

            # 获取公司基本信息
            df = self._ak.stock_individual_info_em(symbol=code)

            if df is None or df.empty:
                logger.warning(f"AKShare未找到公司信息: {ticker}")
                return None

            # 解析公司信息
            info_dict = dict(zip(df["item"], df["value"]))

            # 处理上市日期格式（AKShare可能返回整数如20010827）
            listing_date_raw = info_dict.get("上市时间")
            listing_date = None
            if listing_date_raw is not None:
                if isinstance(listing_date_raw, int):
                    listing_date = str(listing_date_raw)
                else:
                    listing_date = str(listing_date_raw)

            facts = CompanyFacts(
                ticker=ticker,
                name=info_dict.get("公司名称", ""),
                cik=None,
                industry=info_dict.get("行业"),
                sector=None,
                category=None,
                exchange=self.get_exchange(ticker),
                is_active=True,
                listing_date=listing_date,
                location=info_dict.get("地区"),
                market_cap=None,
                number_of_employees=None,
                sec_filings_url=None,
                sic_code=None,
                sic_industry=None,
                sic_sector=None,
                website_url=None,
                weighted_average_shares=None,
            )

            # 缓存结果
            self._cache.set(cache_key, facts)
            return facts

        except Exception as e:
            logger.error(f"AKShare获取公司信息失败: {ticker} - {e}")
            return None

    def get_northbound_flow(self, days: int = 30) -> List[NorthboundFlow]:
        """获取北向资金流向"""
        if not self.is_available():
            return []

        # 检查缓存
        cache_key = self._get_cache_key("northbound", days)
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            # 获取北向资金数据
            df = self._ak.stock_hsgt_north_net_flow_in_em()

            if df is None or df.empty:
                return []

            flows = []
            for _, row in df.head(days).iterrows():
                try:
                    flow = NorthboundFlow(
                        date=str(row["日期"]),
                        buy_amount=self._safe_float(row.get("买入金额", 0)) / 100000000,  # 转换为亿元
                        sell_amount=self._safe_float(row.get("卖出金额", 0)) / 100000000,
                        net_buy=self._safe_float(row.get("净买入金额", 0)) / 100000000,
                    )
                    flows.append(flow)
                except Exception as e:
                    logger.warning(f"解析北向资金数据失败: {e}")
                    continue

            # 缓存结果
            self._cache.set(cache_key, flows)
            return flows

        except Exception as e:
            logger.error(f"AKShare获取北向资金失败: {e}")
            return []

    def get_dragon_tiger(self, date: str = None) -> List[DragonTigerItem]:
        """获取龙虎榜数据"""
        if not self.is_available():
            return []

        if date is None:
            date = datetime.datetime.now().strftime("%Y%m%d")

        # 检查缓存
        cache_key = self._get_cache_key("dragon_tiger", date)
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            # 获取龙虎榜数据
            df = self._ak.stock_lhb_detail_em(start_date=date, end_date=date)

            if df is None or df.empty:
                return []

            items = []
            for _, row in df.iterrows():
                try:
                    item = DragonTigerItem(
                        ticker=str(row.get("代码", "")),
                        date=date,
                        close_price=self._safe_float(row.get("收盘价", 0)),
                        change_pct=self._safe_float(row.get("涨跌幅", 0)),
                        turnover_rate=self._safe_float(row.get("换手率", 0)),
                        reason=str(row.get("上榜原因", "")),
                        net_buy=self._safe_float(row.get("净买入", 0)),
                    )
                    items.append(item)
                except Exception as e:
                    logger.warning(f"解析龙虎榜数据失败: {e}")
                    continue

            # 缓存结果
            self._cache.set(cache_key, items)
            return items

        except Exception as e:
            logger.error(f"AKShare获取龙虎榜失败: {e}")
            return []

    def get_sectors(self) -> List[SectorData]:
        """获取板块数据"""
        if not self.is_available():
            return []

        # 检查缓存
        cache_key = self._get_cache_key("sectors")
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            # 获取板块数据
            df = self._ak.stock_board_concept_name_em()

            if df is None or df.empty:
                return []

            sectors = []
            for _, row in df.iterrows():
                try:
                    sector = SectorData(
                        name=str(row.get("板块名称", "")),
                        code=str(row.get("板块代码", "")),
                        change_pct=self._safe_float(row.get("涨跌幅", 0)),
                        turnover=self._safe_float(row.get("总市值", 0)),
                        leading_stock=str(row.get("领涨股票", "")),
                        leading_change=self._safe_float(row.get("领涨股票涨跌幅", 0)),
                    )
                    sectors.append(sector)
                except Exception as e:
                    logger.warning(f"解析板块数据失败: {e}")
                    continue

            # 缓存结果
            self._cache.set(cache_key, sectors)
            return sectors

        except Exception as e:
            logger.error(f"AKShare获取板块数据失败: {e}")
            return []

    def _safe_float(self, value) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None:
            return None
        # 处理 pandas Series
        if isinstance(value, pd.Series):
            if value.empty:
                return None
            value = value.iloc[0]
        if value == "" or value == "-":
            return None
        try:
            # 处理百分比格式
            if isinstance(value, str) and "%" in value:
                return float(value.replace("%", "")) / 100
            return float(value)
        except (ValueError, TypeError):
            return None


class TushareDataSource(AStockDataSource):
    """Tushare Pro数据源 - 专业数据"""

    def __init__(self, api_key: str = None):
        super().__init__()
        self._pro = None
        self._api_key = api_key or os.environ.get("TUSHARE_API_KEY")

        if self._api_key:
            try:
                import tushare as ts
                ts.set_token(self._api_key)
                self._pro = ts.pro_api()
                logger.info("Tushare数据源初始化成功")
            except ImportError:
                logger.warning("Tushare未安装，请运行：pip install tushare")
            except Exception as e:
                logger.warning(f"Tushare初始化失败: {e}")

    def is_available(self) -> bool:
        return self._pro is not None

    @retry_on_failure(max_retries=3, delay=2.0)
    def get_prices(self, ticker: str, start_date: str, end_date: str) -> List[Price]:
        """获取A股历史价格数据"""
        if not self.is_available():
            return []

        # 检查缓存
        cache_key = self._get_cache_key("prices", ticker, start_date, end_date)
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            code = self.normalize_ticker(ticker)

            # 使用Tushare获取日线数据
            df = self._pro.daily(
                ts_code=f"{code}.{self.get_exchange(ticker)}",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", "")
            )

            if df is None or df.empty:
                logger.warning(f"Tushare未找到价格数据: {ticker}")
                return []

            prices = []
            for _, row in df.iterrows():
                try:
                    price = Price(
                        open=float(row["open"]),
                        close=float(row["close"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        volume=int(row["vol"] * 100),  # Tushare单位是手，转换为股
                        time=str(row["trade_date"]),
                    )
                    prices.append(price)
                except Exception as e:
                    logger.warning(f"解析价格数据失败: {e}")
                    continue

            # 按日期排序
            prices.sort(key=lambda x: x.time)

            # 缓存结果
            self._cache.set(cache_key, prices)
            return prices

        except Exception as e:
            logger.error(f"Tushare获取价格数据失败: {ticker} - {e}")
            return []

    @retry_on_failure(max_retries=3, delay=2.0)
    def get_financial_metrics(self, ticker: str, end_date: str, period: str = "ttm", limit: int = 10) -> List[FinancialMetrics]:
        """获取A股财务指标"""
        if not self.is_available():
            return []

        # 检查缓存
        cache_key = self._get_cache_key("metrics", ticker, end_date, period, limit)
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            code = self.normalize_ticker(ticker)
            ts_code = f"{code}.{self.get_exchange(ticker)}"

            # 获取财务指标
            df = self._pro.fina_indicator(ts_code=ts_code, limit=limit)

            if df is None or df.empty:
                logger.warning(f"Tushare未找到财务指标: {ticker}")
                return []

            metrics_list = []
            for _, row in df.iterrows():
                try:
                    metrics = FinancialMetrics(
                        ticker=ticker,
                        report_period=str(row["ann_date"]),
                        period=period,
                        currency="CNY",
                        market_cap=None,
                        enterprise_value=None,
                        price_to_earnings_ratio=self._safe_float(row.get("pe")),
                        price_to_book_ratio=self._safe_float(row.get("pb")),
                        price_to_sales_ratio=self._safe_float(row.get("ps")),
                        enterprise_value_to_ebitda_ratio=None,
                        enterprise_value_to_revenue_ratio=None,
                        free_cash_flow_yield=None,
                        peg_ratio=None,
                        gross_margin=self._safe_float(row.get("grossprofit_margin")),
                        operating_margin=self._safe_float(row.get("op_yoy")),
                        net_margin=self._safe_float(row.get("netprofit_margin")),
                        return_on_equity=self._safe_float(row.get("roe")),
                        return_on_assets=self._safe_float(row.get("roa")),
                        return_on_invested_capital=None,
                        asset_turnover=None,
                        inventory_turnover=None,
                        receivables_turnover=None,
                        days_sales_outstanding=None,
                        operating_cycle=None,
                        working_capital_turnover=None,
                        current_ratio=self._safe_float(row.get("current_ratio")),
                        quick_ratio=self._safe_float(row.get("quick_ratio")),
                        cash_ratio=None,
                        operating_cash_flow_ratio=None,
                        debt_to_equity=self._safe_float(row.get("debt_to_assets")),
                        debt_to_assets=None,
                        interest_coverage=None,
                        revenue_growth=None,
                        earnings_growth=None,
                        book_value_growth=None,
                        earnings_per_share_growth=None,
                        free_cash_flow_growth=None,
                        operating_income_growth=None,
                        ebitda_growth=None,
                        payout_ratio=None,
                        earnings_per_share=self._safe_float(row.get("eps")),
                        book_value_per_share=self._safe_float(row.get("bps")),
                        free_cash_flow_per_share=None,
                    )
                    metrics_list.append(metrics)
                except Exception as e:
                    logger.warning(f"解析财务指标失败: {e}")
                    continue

            # 缓存结果
            self._cache.set(cache_key, metrics_list)
            return metrics_list

        except Exception as e:
            logger.error(f"Tushare获取财务指标失败: {ticker} - {e}")
            return []

    @retry_on_failure(max_retries=3, delay=2.0)
    def get_company_facts(self, ticker: str) -> Optional[CompanyFacts]:
        """获取A股公司基本信息"""
        if not self.is_available():
            return None

        # 检查缓存
        cache_key = self._get_cache_key("facts", ticker)
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            code = self.normalize_ticker(ticker)
            ts_code = f"{code}.{self.get_exchange(ticker)}"

            # 获取公司基本信息
            df = self._pro.stock_basic(ts_code=ts_code)

            if df is None or df.empty:
                logger.warning(f"Tushare未找到公司信息: {ticker}")
                return None

            row = df.iloc[0]

            facts = CompanyFacts(
                ticker=ticker,
                name=row.get("name", ""),
                cik=None,
                industry=row.get("industry"),
                sector=None,
                category=None,
                exchange=row.get("exchange"),
                is_active=row.get("list_status") == "L",
                listing_date=str(row.get("list_date")) if row.get("list_date") else None,
                location=row.get("area"),
                market_cap=None,
                number_of_employees=None,
                sec_filings_url=None,
                sic_code=None,
                sic_industry=None,
                sic_sector=None,
                website_url=None,
                weighted_average_shares=None,
            )

            # 缓存结果
            self._cache.set(cache_key, facts)
            return facts

        except Exception as e:
            logger.error(f"Tushare获取公司信息失败: {ticker} - {e}")
            return None

    def get_northbound_flow(self, days: int = 30) -> List[NorthboundFlow]:
        """获取北向资金流向"""
        if not self.is_available():
            return []

        try:
            # 获取北向资金数据
            end_date = datetime.datetime.now().strftime("%Y%m%d")
            start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y%m%d")

            df = self._pro.moneyflow_hsgt(start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                return []

            flows = []
            for _, row in df.iterrows():
                try:
                    flow = NorthboundFlow(
                        date=str(row["trade_date"]),
                        buy_amount=self._safe_float(row.get("buy_amount", 0)) / 100000000,
                        sell_amount=self._safe_float(row.get("sell_amount", 0)) / 100000000,
                        net_buy=self._safe_float(row.get("buy_amount", 0) - row.get("sell_amount", 0)) / 100000000,
                    )
                    flows.append(flow)
                except Exception as e:
                    logger.warning(f"解析北向资金数据失败: {e}")
                    continue

            return flows

        except Exception as e:
            logger.error(f"Tushare获取北向资金失败: {e}")
            return []

    def _safe_float(self, value) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None or pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


class AStockAPI:
    """
    A股数据API统一接口

    自动选择可用的数据源，优先级：
    1. Tushare Pro（如果配置了API密钥）
    2. AKShare（免费开源）
    """

    def __init__(self, data_source: str = None):
        """
        初始化A股数据API

        参数：
            data_source: 指定数据源（"tushare", "akshare"），默认自动选择
        """
        self._sources = []
        self._primary_source = None

        # 根据配置或自动选择数据源
        config_source = data_source or os.environ.get("A_STOCK_DATA_SOURCE", "auto")

        if config_source in ["tushare", "auto"]:
            tushare = TushareDataSource()
            if tushare.is_available():
                self._sources.append(tushare)
                if config_source == "tushare":
                    self._primary_source = tushare

        if config_source in ["akshare", "auto"]:
            akshare = AKShareDataSource()
            if akshare.is_available():
                self._sources.append(akshare)
                if config_source == "akshare":
                    self._primary_source = akshare

        # 设置默认数据源
        if self._primary_source is None and self._sources:
            self._primary_source = self._sources[0]

        if self._primary_source:
            logger.info(f"A股数据源已初始化: {self._primary_source.__class__.__name__}")
        else:
            logger.warning("没有可用的A股数据源，请安装AKShare或配置Tushare API密钥")

    def is_available(self) -> bool:
        """检查是否有可用的数据源"""
        return self._primary_source is not None

    def get_prices(self, ticker: str, start_date: str, end_date: str) -> List[Price]:
        """获取股票历史价格数据"""
        if not self.is_available():
            logger.warning("A股数据源不可用")
            return []
        return self._primary_source.get_prices(ticker, start_date, end_date)

    def get_financial_metrics(self, ticker: str, end_date: str, period: str = "ttm", limit: int = 10) -> List[FinancialMetrics]:
        """获取财务指标"""
        if not self.is_available():
            return []
        return self._primary_source.get_financial_metrics(ticker, end_date, period, limit)

    def get_company_facts(self, ticker: str) -> Optional[CompanyFacts]:
        """获取公司基本信息"""
        if not self.is_available():
            return None
        return self._primary_source.get_company_facts(ticker)

    def get_market_cap(self, ticker: str, end_date: str) -> Optional[float]:
        """获取市值"""
        try:
            prices = self.get_prices(ticker, end_date, end_date)
            if prices:
                # 获取总股本并计算市值
                facts = self.get_company_facts(ticker)
                if facts and facts.weighted_average_shares:
                    return prices[-1].close * facts.weighted_average_shares
        except Exception as e:
            logger.error(f"获取市值失败: {ticker} - {e}")
        return None

    def get_northbound_flow(self, days: int = 30) -> List[NorthboundFlow]:
        """获取北向资金流向"""
        if not self.is_available():
            return []
        return self._primary_source.get_northbound_flow(days)

    def get_dragon_tiger(self, date: str = None) -> List[DragonTigerItem]:
        """获取龙虎榜数据"""
        if not self.is_available():
            return []
        return self._primary_source.get_dragon_tiger(date)

    def get_sectors(self) -> List[SectorData]:
        """获取板块数据"""
        if not self.is_available():
            return []
        return self._primary_source.get_sectors()

    @staticmethod
    def is_a_stock_ticker(ticker: str) -> bool:
        """
        判断是否为A股股票代码

        A股代码规则：
        - 6开头：上海证券交易所主板
        - 0开头：深圳证券交易所主板
        - 3开头：深圳证券交易所创业板
        - 688开头：上海证券交易所科创板
        - 8开头：北京证券交易所
        - 4开头：北京证券交易所
        """
        ticker = ticker.upper().strip()
        # 移除交易所后缀
        for suffix in [".SH", ".SZ", ".BJ"]:
            if ticker.endswith(suffix):
                ticker = ticker[:-3]
                break

        # 检查是否为纯数字且长度为6
        if len(ticker) == 6 and ticker.isdigit():
            return True

        return False


# 便捷函数
def get_a_stock_prices(ticker: str, start_date: str, end_date: str) -> List[Price]:
    """获取A股价格数据的便捷函数"""
    api = AStockAPI()
    return api.get_prices(ticker, start_date, end_date)


def get_a_stock_financial_metrics(ticker: str, end_date: str, period: str = "ttm", limit: int = 10) -> List[FinancialMetrics]:
    """获取A股财务指标的便捷函数"""
    api = AStockAPI()
    return api.get_financial_metrics(ticker, end_date, period, limit)


def get_northbound_flow(days: int = 30) -> List[NorthboundFlow]:
    """获取北向资金流向的便捷函数"""
    api = AStockAPI()
    return api.get_northbound_flow(days)


def get_dragon_tiger(date: str = None) -> List[DragonTigerItem]:
    """获取龙虎榜数据的便捷函数"""
    api = AStockAPI()
    return api.get_dragon_tiger(date)


def get_sectors() -> List[SectorData]:
    """获取板块数据的便捷函数"""
    api = AStockAPI()
    return api.get_sectors()


# 导出
__all__ = [
    "AStockAPI",
    "AStockDataSource",
    "AKShareDataSource",
    "TushareDataSource",
    "NorthboundFlow",
    "DragonTigerItem",
    "SectorData",
    "DataCache",
    "get_a_stock_prices",
    "get_a_stock_financial_metrics",
    "get_northbound_flow",
    "get_dragon_tiger",
    "get_sectors",
]