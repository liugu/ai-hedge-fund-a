from pydantic import BaseModel


class Price(BaseModel):
    """价格数据模型"""
    open: float  # 开盘价
    close: float  # 收盘价
    high: float  # 最高价
    low: float  # 最低价
    volume: int  # 成交量
    time: str  # 时间


class PriceResponse(BaseModel):
    """价格响应模型"""
    ticker: str  # 股票代码
    prices: list[Price]


class FinancialMetrics(BaseModel):
    """财务指标数据模型"""
    ticker: str  # 股票代码
    report_period: str  # 报告期
    period: str  # 周期
    currency: str  # 货币
    market_cap: float | None  # 市值
    enterprise_value: float | None  # 企业价值
    price_to_earnings_ratio: float | None  # 市盈率
    price_to_book_ratio: float | None  # 市净率
    price_to_sales_ratio: float | None  # 市销率
    enterprise_value_to_ebitda_ratio: float | None  # EV/EBITDA
    enterprise_value_to_revenue_ratio: float | None  # EV/营收
    free_cash_flow_yield: float | None  # 自由现金流收益率
    peg_ratio: float | None  # PEG比率
    gross_margin: float | None  # 毛利率
    operating_margin: float | None  # 营业利润率
    net_margin: float | None  # 净利润率
    return_on_equity: float | None  # 净资产收益率
    return_on_assets: float | None  # 资产收益率
    return_on_invested_capital: float | None  # 投资资本回报率
    asset_turnover: float | None  # 资产周转率
    inventory_turnover: float | None  # 存货周转率
    receivables_turnover: float | None  # 应收账款周转率
    days_sales_outstanding: float | None  # 应收账款周转天数
    operating_cycle: float | None  # 营业周期
    working_capital_turnover: float | None  # 营运资本周转率
    current_ratio: float | None  # 流动比率
    quick_ratio: float | None  # 速动比率
    cash_ratio: float | None  # 现金比率
    operating_cash_flow_ratio: float | None  # 经营现金流比率
    debt_to_equity: float | None  # 资产负债率
    debt_to_assets: float | None  # 债务资产比
    interest_coverage: float | None  # 利息保障倍数
    revenue_growth: float | None  # 营收增长率
    earnings_growth: float | None  # 盈利增长率
    book_value_growth: float | None  # 账面价值增长率
    earnings_per_share_growth: float | None  # 每股收益增长率
    free_cash_flow_growth: float | None  # 自由现金流增长率
    operating_income_growth: float | None  # 营业收入增长率
    ebitda_growth: float | None  # EBITDA增长率
    payout_ratio: float | None  # 分红比率
    earnings_per_share: float | None  # 每股收益
    book_value_per_share: float | None  # 每股账面价值
    free_cash_flow_per_share: float | None  # 每股自由现金流


class FinancialMetricsResponse(BaseModel):
    """财务指标响应模型"""
    financial_metrics: list[FinancialMetrics]


class LineItem(BaseModel):
    """财务行项目模型"""
    ticker: str  # 股票代码
    report_period: str  # 报告期
    period: str  # 周期
    currency: str  # 货币

    # 允许动态添加额外字段
    model_config = {"extra": "allow"}


class LineItemResponse(BaseModel):
    """行项目响应模型"""
    search_results: list[LineItem]


class InsiderTrade(BaseModel):
    """内部交易数据模型"""
    ticker: str  # 股票代码
    issuer: str | None  # 发行人
    name: str | None  # 交易者姓名
    title: str | None  # 职位
    is_board_director: bool | None  # 是否董事
    transaction_date: str | None  # 交易日期
    transaction_shares: float | None  # 交易股数
    transaction_price_per_share: float | None  # 每股价格
    transaction_value: float | None  # 交易金额
    shares_owned_before_transaction: float | None  # 交易前持股数
    shares_owned_after_transaction: float | None  # 交易后持股数
    security_title: str | None  # 证券名称
    filing_date: str  # 备案日期


class InsiderTradeResponse(BaseModel):
    """内部交易响应模型"""
    insider_trades: list[InsiderTrade]


class CompanyNews(BaseModel):
    """公司新闻数据模型"""
    ticker: str  # 股票代码
    title: str  # 标题
    author: str | None = None  # 作者
    source: str  # 来源
    date: str  # 日期
    url: str  # 链接
    sentiment: str | None = None  # 情绪


class CompanyNewsResponse(BaseModel):
    """公司新闻响应模型"""
    news: list[CompanyNews]


class CompanyFacts(BaseModel):
    """公司基本信息模型"""
    ticker: str  # 股票代码
    name: str  # 公司名称
    cik: str | None = None  # CIK编号
    industry: str | None = None  # 行业
    sector: str | None = None  # 板块
    category: str | None = None  # 类别
    exchange: str | None = None  # 交易所
    is_active: bool | None = None  # 是否活跃
    listing_date: str | None = None  # 上市日期
    location: str | None = None  # 地点
    market_cap: float | None = None  # 市值
    number_of_employees: int | None = None  # 员工数
    sec_filings_url: str | None = None  # SEC文件链接
    sic_code: str | None = None  # SIC代码
    sic_industry: str | None = None  # SIC行业
    sic_sector: str | None = None  # SIC板块
    website_url: str | None = None  # 网站链接
    weighted_average_shares: int | None = None  # 加权平均股数


class CompanyFactsResponse(BaseModel):
    """公司信息响应模型"""
    company_facts: CompanyFacts


class Position(BaseModel):
    """持仓数据模型"""
    cash: float = 0.0  # 现金
    shares: int = 0  # 持股数
    ticker: str  # 股票代码


class Portfolio(BaseModel):
    """投资组合模型"""
    positions: dict[str, Position]  # 股票代码 -> 持仓映射
    total_cash: float = 0.0  # 总现金


class AnalystSignal(BaseModel):
    """分析师信号模型"""
    signal: str | None = None  # 信号（bullish/bearish/neutral）
    confidence: float | None = None  # 置信度
    reasoning: dict | str | None = None  # 推理依据
    max_position_size: float | None = None  # 最大仓位（用于风险管理信号）


class TickerAnalysis(BaseModel):
    """股票分析模型"""
    ticker: str  # 股票代码
    analyst_signals: dict[str, AnalystSignal]  # 代理名称 -> 信号映射


class AgentStateData(BaseModel):
    """代理状态数据模型"""
    tickers: list[str]  # 股票代码列表
    portfolio: Portfolio  # 投资组合
    start_date: str  # 开始日期
    end_date: str  # 结束日期
    ticker_analyses: dict[str, TickerAnalysis]  # 股票代码 -> 分析映射


class AgentStateMetadata(BaseModel):
    """代理状态元数据模型"""
    show_reasoning: bool = False  # 是否显示推理过程
    model_config = {"extra": "allow"}
