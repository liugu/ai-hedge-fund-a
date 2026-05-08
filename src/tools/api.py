"""
统一数据API接口

自动识别股票代码类型（A股/美股）并使用对应数据源：
- A股：使用AKShare或Tushare
- 美股：使用Financial Datasets API
"""

import datetime
import logging
import os
import pandas as pd
import requests
import time
from typing import List, Optional

logger = logging.getLogger(__name__)

from src.data.cache import get_cache
from src.data.models import (
    CompanyNews,
    CompanyNewsResponse,
    FinancialMetrics,
    FinancialMetricsResponse,
    Price,
    PriceResponse,
    LineItem,
    LineItemResponse,
    InsiderTrade,
    InsiderTradeResponse,
    CompanyFactsResponse,
)

# 全局缓存实例
_cache = get_cache()

# A股数据源实例（延迟初始化）
_a_stock_api = None


def _get_a_stock_api():
    """获取A股数据API实例（延迟初始化）"""
    global _a_stock_api
    if _a_stock_api is None:
        try:
            from src.tools.a_stock_api import AStockAPI
            _a_stock_api = AStockAPI()
        except ImportError:
            logger.warning("无法导入A股数据源")
            _a_stock_api = False  # 标记为不可用
    return _a_stock_api if _a_stock_api else None


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

    支持格式：600519, 600519.SH, sh600519
    """
    ticker = ticker.upper().strip()

    # 移除交易所后缀
    for suffix in [".SH", ".SZ", ".BJ"]:
        if ticker.endswith(suffix):
            ticker = ticker[:-3]
            break

    # 移除前缀
    for prefix in ["SH", "SZ", "BJ"]:
        if ticker.startswith(prefix):
            ticker = ticker[len(prefix):]
            break

    # 检查是否为纯数字且长度为6
    if len(ticker) == 6 and ticker.isdigit():
        return True

    return False


def _make_api_request(url: str, headers: dict, method: str = "GET", json_data: dict = None, max_retries: int = 3) -> requests.Response:
    """
    发送API请求，处理速率限制和适度退避。

    参数：
        url: 请求URL
        headers: 请求头
        method: HTTP方法（GET或POST）
        json_data: POST请求的JSON数据
        max_retries: 最大重试次数（默认：3）

    返回：
        requests.Response: 响应对象
    """
    for attempt in range(max_retries + 1):  # +1 用于初始尝试
        if method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data)
        else:
            response = requests.get(url, headers=headers)

        if response.status_code == 429 and attempt < max_retries:
            # 线性退避：60秒、90秒、120秒、150秒...
            delay = 60 + (30 * attempt)
            print(f"触发速率限制（429）。尝试 {attempt + 1}/{max_retries + 1}。等待 {delay} 秒后重试...")
            time.sleep(delay)
            continue

        # 返回响应（无论成功、其他错误或最终429）
        return response


def get_prices(ticker: str, start_date: str, end_date: str, api_key: str = None) -> List[Price]:
    """
    从缓存或API获取价格数据

    自动识别股票代码类型：
    - A股：使用AKShare/Tushare
    - 美股：使用Financial Datasets API
    """
    # 检查是否为A股
    if is_a_stock_ticker(ticker):
        a_stock_api = _get_a_stock_api()
        if a_stock_api and a_stock_api.is_available():
            logger.info(f"使用A股数据源获取 {ticker} 价格数据")
            return a_stock_api.get_prices(ticker, start_date, end_date)
        else:
            logger.warning(f"A股数据源不可用，无法获取 {ticker} 价格数据")
            return []

    # 美股数据获取逻辑
    # 创建包含所有参数的缓存键以确保精确匹配
    cache_key = f"{ticker}_{start_date}_{end_date}"

    # 首先检查缓存 - 简单精确匹配
    if cached_data := _cache.get_prices(cache_key):
        return [Price(**price) for price in cached_data]

    # 如果不在缓存中，从API获取
    headers = {}
    financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if financial_api_key:
        headers["X-API-KEY"] = financial_api_key

    url = f"https://api.financialdatasets.ai/prices/?ticker={ticker}&interval=day&interval_multiplier=1&start_date={start_date}&end_date={end_date}"
    response = _make_api_request(url, headers)
    if response.status_code != 200:
        return []

    # 使用Pydantic模型解析响应
    try:
        price_response = PriceResponse(**response.json())
        prices = price_response.prices
    except Exception as e:
        logger.warning("解析 %s 价格响应失败: %s", ticker, e)
        return []

    if not prices:
        return []

    # 使用综合缓存键缓存结果
    _cache.set_prices(cache_key, [p.model_dump() for p in prices])
    return prices


def get_financial_metrics(
    ticker: str,
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
    api_key: str = None,
) -> List[FinancialMetrics]:
    """
    从缓存或API获取财务指标

    自动识别股票代码类型：
    - A股：使用AKShare/Tushare
    - 美股：使用Financial Datasets API
    """
    # 检查是否为A股
    if is_a_stock_ticker(ticker):
        a_stock_api = _get_a_stock_api()
        if a_stock_api and a_stock_api.is_available():
            logger.info(f"使用A股数据源获取 {ticker} 财务指标")
            return a_stock_api.get_financial_metrics(ticker, end_date, period, limit)
        else:
            logger.warning(f"A股数据源不可用，无法获取 {ticker} 财务指标")
            return []

    # 美股数据获取逻辑
    # 创建包含所有参数的缓存键以确保精确匹配
    cache_key = f"{ticker}_{period}_{end_date}_{limit}"

    # 首先检查缓存 - 简单精确匹配
    if cached_data := _cache.get_financial_metrics(cache_key):
        return [FinancialMetrics(**metric) for metric in cached_data]

    # 如果不在缓存中，从API获取
    headers = {}
    financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if financial_api_key:
        headers["X-API-KEY"] = financial_api_key

    url = f"https://api.financialdatasets.ai/financial-metrics/?ticker={ticker}&report_period_lte={end_date}&limit={limit}&period={period}"
    response = _make_api_request(url, headers)
    if response.status_code != 200:
        return []

    # 使用Pydantic模型解析响应
    try:
        metrics_response = FinancialMetricsResponse(**response.json())
        financial_metrics = metrics_response.financial_metrics
    except Exception as e:
        logger.warning("解析 %s 财务指标响应失败: %s", ticker, e)
        return []

    if not financial_metrics:
        return []

    # 使用综合缓存键将结果缓存为字典
    _cache.set_financial_metrics(cache_key, [m.model_dump() for m in financial_metrics])
    return financial_metrics


def search_line_items(
    ticker: str,
    line_items: list[str],
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
    api_key: str = None,
) -> List[LineItem]:
    """
    从API获取财务行项目

    注意：A股数据源暂不支持行项目搜索，仅支持美股
    """
    # 检查是否为A股
    if is_a_stock_ticker(ticker):
        logger.warning(f"A股数据源暂不支持行项目搜索: {ticker}")
        return []

    # 美股数据获取逻辑
    headers = {}
    financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if financial_api_key:
        headers["X-API-KEY"] = financial_api_key

    url = "https://api.financialdatasets.ai/financials/search/line-items"

    body = {
        "tickers": [ticker],
        "line_items": line_items,
        "end_date": end_date,
        "period": period,
        "limit": limit,
    }
    response = _make_api_request(url, headers, method="POST", json_data=body)
    if response.status_code != 200:
        return []

    try:
        data = response.json()
        response_model = LineItemResponse(**data)
        search_results = response_model.search_results
    except Exception as e:
        logger.warning("解析 %s 行项目响应失败: %s", ticker, e)
        return []
    if not search_results:
        return []

    return search_results[:limit]


def get_insider_trades(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
    api_key: str = None,
) -> List[InsiderTrade]:
    """
    从缓存或API获取内部交易数据

    注意：A股内部交易数据格式与美股不同
    """
    # 检查是否为A股
    if is_a_stock_ticker(ticker):
        logger.info(f"A股内部交易数据获取: {ticker}")
        # A股内部交易数据可以通过龙虎榜等方式获取
        # 这里返回空列表，实际使用时可扩展
        return []

    # 美股数据获取逻辑
    cache_key = f"{ticker}_{start_date or 'none'}_{end_date}_{limit}"

    if cached_data := _cache.get_insider_trades(cache_key):
        return [InsiderTrade(**trade) for trade in cached_data]

    headers = {}
    financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if financial_api_key:
        headers["X-API-KEY"] = financial_api_key

    all_trades = []
    current_end_date = end_date

    while True:
        url = f"https://api.financialdatasets.ai/insider-trades/?ticker={ticker}&filing_date_lte={current_end_date}"
        if start_date:
            url += f"&filing_date_gte={start_date}"
        url += f"&limit={limit}"

        response = _make_api_request(url, headers)
        if response.status_code != 200:
            break

        try:
            data = response.json()
            response_model = InsiderTradeResponse(**data)
            insider_trades = response_model.insider_trades
        except Exception as e:
            logger.warning("解析 %s 内部交易响应失败: %s", ticker, e)
            break

        if not insider_trades:
            break

        all_trades.extend(insider_trades)

        if not start_date or len(insider_trades) < limit:
            break

        current_end_date = min(trade.filing_date for trade in insider_trades).split("T")[0]

        if current_end_date <= start_date:
            break

    if not all_trades:
        return []

    _cache.set_insider_trades(cache_key, [trade.model_dump() for trade in all_trades])
    return all_trades


def get_company_news(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
    api_key: str = None,
) -> List[CompanyNews]:
    """从缓存或API获取公司新闻"""
    # 检查是否为A股
    if is_a_stock_ticker(ticker):
        a_stock_api = _get_a_stock_api()
        if a_stock_api and a_stock_api.is_available():
            logger.info(f"使用A股数据源获取 {ticker} 新闻数据")
            return a_stock_api.get_news(ticker, limit=min(limit, 50))
        else:
            logger.warning(f"A股数据源不可用，无法获取 {ticker} 新闻数据")
            return []

    # 美股数据获取逻辑
    cache_key = f"{ticker}_{start_date or 'none'}_{end_date}_{limit}"

    if cached_data := _cache.get_company_news(cache_key):
        return [CompanyNews(**news) for news in cached_data]

    headers = {}
    financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if financial_api_key:
        headers["X-API-KEY"] = financial_api_key

    all_news = []
    current_end_date = end_date

    while True:
        url = f"https://api.financialdatasets.ai/news/?ticker={ticker}&end_date={current_end_date}"
        if start_date:
            url += f"&start_date={start_date}"
        url += f"&limit={limit}"

        response = _make_api_request(url, headers)
        if response.status_code != 200:
            break

        try:
            data = response.json()
            response_model = CompanyNewsResponse(**data)
            company_news = response_model.news
        except Exception as e:
            logger.warning("解析 %s 公司新闻响应失败: %s", ticker, e)
            break

        if not company_news:
            break

        all_news.extend(company_news)

        if not start_date or len(company_news) < limit:
            break

        current_end_date = min(news.date for news in company_news).split("T")[0]

        if current_end_date <= start_date:
            break

    if not all_news:
        return []

    _cache.set_company_news(cache_key, [news.model_dump() for news in all_news])
    return all_news


def get_market_cap(
    ticker: str,
    end_date: str,
    api_key: str = None,
) -> float | None:
    """
    从API获取市值

    自动识别股票代码类型并使用对应数据源
    """
    # 检查是否为A股
    if is_a_stock_ticker(ticker):
        a_stock_api = _get_a_stock_api()
        if a_stock_api and a_stock_api.is_available():
            logger.info(f"使用A股数据源获取 {ticker} 市值")
            return a_stock_api.get_market_cap(ticker, end_date)
        else:
            logger.warning(f"A股数据源不可用，无法获取 {ticker} 市值")
            return None

    # 美股数据获取逻辑
    if end_date == datetime.datetime.now().strftime("%Y-%m-%d"):
        headers = {}
        financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
        if financial_api_key:
            headers["X-API-KEY"] = financial_api_key

        url = f"https://api.financialdatasets.ai/company/facts/?ticker={ticker}"
        response = _make_api_request(url, headers)
        if response.status_code != 200:
            print(f"获取公司信息失败: {ticker} - {response.status_code}")
            return None

        data = response.json()
        response_model = CompanyFactsResponse(**data)
        return response_model.company_facts.market_cap

    financial_metrics = get_financial_metrics(ticker, end_date, api_key=api_key)
    if not financial_metrics:
        return None

    market_cap = financial_metrics[0].market_cap

    if not market_cap:
        return None

    return market_cap


def get_company_facts(ticker: str, api_key: str = None) -> Optional[dict]:
    """
    获取公司基本信息

    自动识别股票代码类型并使用对应数据源
    """
    # 检查是否为A股
    if is_a_stock_ticker(ticker):
        a_stock_api = _get_a_stock_api()
        if a_stock_api and a_stock_api.is_available():
            logger.info(f"使用A股数据源获取 {ticker} 公司信息")
            facts = a_stock_api.get_company_facts(ticker)
            if facts:
                return facts.model_dump()
        return None

    # 美股数据获取逻辑
    headers = {}
    financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if financial_api_key:
        headers["X-API-KEY"] = financial_api_key

    url = f"https://api.financialdatasets.ai/company/facts/?ticker={ticker}"
    response = _make_api_request(url, headers)
    if response.status_code != 200:
        return None

    try:
        data = response.json()
        response_model = CompanyFactsResponse(**data)
        return response_model.company_facts.model_dump()
    except Exception as e:
        logger.warning("解析 %s 公司信息响应失败: %s", ticker, e)
        return None


def prices_to_df(prices: List[Price]) -> pd.DataFrame:
    """将价格数据转换为DataFrame"""
    df = pd.DataFrame([p.model_dump() for p in prices])
    df["Date"] = pd.to_datetime(df["time"])
    df.set_index("Date", inplace=True)
    numeric_cols = ["open", "close", "high", "low", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.sort_index(inplace=True)
    return df


def get_price_data(ticker: str, start_date: str, end_date: str, api_key: str = None) -> pd.DataFrame:
    """获取价格数据并转换为DataFrame"""
    prices = get_prices(ticker, start_date, end_date, api_key=api_key)
    return prices_to_df(prices)


# A股特有数据获取函数
def get_northbound_flow(days: int = 30) -> List[dict]:
    """
    获取北向资金流向数据

    返回最近N天的北向资金净买入数据
    """
    a_stock_api = _get_a_stock_api()
    if a_stock_api and a_stock_api.is_available():
        flows = a_stock_api.get_northbound_flow(days)
        return [f.__dict__ for f in flows]
    return []


def get_dragon_tiger(date: str = None) -> List[dict]:
    """
    获取龙虎榜数据

    参数：
        date: 日期（YYYYMMDD格式），默认今天
    """
    a_stock_api = _get_a_stock_api()
    if a_stock_api and a_stock_api.is_available():
        items = a_stock_api.get_dragon_tiger(date)
        return [i.__dict__ for i in items]
    return []


def get_sectors() -> List[dict]:
    """
    获取板块数据

    返回所有板块的涨跌幅和领涨股信息
    """
    a_stock_api = _get_a_stock_api()
    if a_stock_api and a_stock_api.is_available():
        sectors = a_stock_api.get_sectors()
        return [s.__dict__ for s in sectors]
    return []


# 导出
__all__ = [
    "get_prices",
    "get_financial_metrics",
    "search_line_items",
    "get_insider_trades",
    "get_company_news",
    "get_market_cap",
    "get_company_facts",
    "prices_to_df",
    "get_price_data",
    "is_a_stock_ticker",
    "get_northbound_flow",
    "get_dragon_tiger",
    "get_sectors",
]