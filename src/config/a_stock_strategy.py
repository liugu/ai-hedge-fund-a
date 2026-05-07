"""
A股投资策略优化配置

针对A股市场特点对投资大师策略进行调整：
1. 考虑涨跌停限制
2. T+1交易规则
3. 行业轮动特点
4. 政策敏感性
5. 散户占比高
6. 题材炒作
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class AStockMarketFeature(Enum):
    """A股市场特征"""
    PRICE_LIMIT = "price_limit"  # 涨跌停限制
    T_PLUS_ONE = "t_plus_one"  # T+1交易
    RETAIL_DOMINANT = "retail_dominant"  # 散户主导
    POLICY_SENSITIVE = "policy_sensitive"  # 政策敏感
    SECTOR_ROTATION = "sector_rotation"  # 行业轮动
    THEME_SPECULATION = "theme_speculation"  # 题材炒作


@dataclass
class AStockStrategyAdjustment:
    """A股策略调整配置"""

    # 原始策略名称
    original_strategy: str

    # A股调整后的权重调整
    weight_adjustment: Dict[str, float]

    # 需要额外关注的因素
    additional_factors: List[str]

    # 需要降低权重的因素
    reduced_factors: List[str]

    # A股特有的信号
    a_stock_signals: List[str]

    # 调整说明
    adjustment_notes: str


# A股策略调整配置
A_STOCK_STRATEGY_ADJUSTMENTS = {
    # 沃伦·巴菲特策略A股调整
    "warren_buffett": AStockStrategyAdjustment(
        original_strategy="Warren Buffett",
        weight_adjustment={
            "competitive_moat": 1.2,  # 护城河权重提高
            "management_quality": 1.1,  # 管理层质量权重提高
            "dividend_yield": 1.3,  # 分红收益率权重提高（A股分红文化增强）
            "price_to_earnings": 0.9,  # P/E权重降低（A股整体估值较高）
        },
        additional_factors=[
            "state_owned_enterprise",  # 国企背景
            "dividend_policy",  # 分红政策
            "industry_policy",  # 行业政策支持
            "market_cap_stability",  # 大盘股稳定性
        ],
        reduced_factors=[
            "us_market_comparison",  # 美股市场对比
            "circle_of_competence",  # 能力圈（A股行业更集中）
        ],
        a_stock_signals=[
            "northbound_capital_flow",  # 北向资金流向
            "institutional_holding",  # 机构持股比例
            "dividend_payout_ratio",  # 分红比例
        ],
        adjustment_notes="A股价值投资需更关注政策导向和分红稳定性，国企背景可提供额外安全边际",
    ),

    # 彼得·林奇策略A股调整
    "peter_lynch": AStockStrategyAdjustment(
        original_strategy="Peter Lynch",
        weight_adjustment={
            "growth_rate": 1.2,  # 增长率权重提高
            "peg_ratio": 1.1,  # PEG权重提高
            "small_cap": 1.3,  # 小盘股权重提高
            "insider_ownership": 0.8,  # 内部人持股权重降低（A股内部人持股比例较低）
        },
        additional_factors=[
            "concept_theme",  # 概念题材
            "retail_interest",  # 散户关注度
            "turnover_rate",  # 换手率
            "hot_sector",  # 热门板块
        ],
        reduced_factors=[
            "us_consumer_stocks",  # 美国消费股特点
        ],
        a_stock_signals=[
            "dragon_tiger_list",  # 龙虎榜
            "retail_sentiment",  # 散户情绪
            "concept_rotation",  # 概念轮动
        ],
        adjustment_notes="A股十倍股更多来自新兴行业和热门概念，需关注题材炒作和散户情绪",
    ),

    # 迈克尔·布瑞策略A股调整
    "michael_burry": AStockStrategyAdjustment(
        original_strategy="Michael Burry",
        weight_adjustment={
            "deep_value": 1.3,  # 深度价值权重提高
            "contrarian": 1.2,  # 逆向投资权重提高
            "short_interest": 0.5,  # 做空兴趣权重降低（A股做空机制有限）
        },
        additional_factors=[
            "st_turnaround",  # ST股扭亏
            "restructuring",  # 重组预期
            "policy_turnaround",  # 政策反转
            "industry_cycle_bottom",  # 行业周期底部
        ],
        reduced_factors=[
            "short_selling",  # 做空机制
            "put_options",  # 看跌期权
        ],
        a_stock_signals=[
            "st_status_change",  # ST状态变化
            "restructuring_plan",  # 重组计划
            "major_shareholder_change",  # 大股东变更
        ],
        adjustment_notes="A股做空机制有限，逆向投资更多关注ST股扭亏和重组机会",
    ),

    # 凯瑟琳·伍德策略A股调整
    "cathie_wood": AStockStrategyAdjustment(
        original_strategy="Cathie Wood",
        weight_adjustment={
            "innovation": 1.3,  # 创新权重提高
            "disruption": 1.2,  # 颠覆性权重提高
            "technology": 1.4,  # 科技权重提高
            "valuation": 0.7,  # 估值权重降低（A股科技股估值较高）
        },
        additional_factors=[
            "national_strategy",  # 国家战略支持
            "independent_innovation",  # 自主创新
            "import_substitution",  # 进口替代
            "new_infrastructure",  # 新基建
        ],
        reduced_factors=[
            "us_tech_leadership",  # 美国科技领先性
        ],
        a_stock_signals=[
            "government_funding",  # 政府资金支持
            "national_project",  # 国家项目
            "tech_independence",  # 科技自主可控
        ],
        adjustment_notes="A股科技创新需关注国家战略方向，如半导体、新能源、人工智能等",
    ),

    # 斯坦利·德鲁肯米勒策略A股调整
    "stanley_druckenmiller": AStockStrategyAdjustment(
        original_strategy="Stanley Druckenmiller",
        weight_adjustment={
            "macro_trend": 1.4,  # 宏观趋势权重提高
            "sector_rotation": 1.3,  # 板块轮动权重提高
            "liquidity": 1.2,  # 流动性权重提高
        },
        additional_factors=[
            "monetary_policy",  # 货币政策
            "fiscal_policy",  # 财政政策
            "credit_cycle",  # 信贷周期
            "property_market",  # 房地产市场
        ],
        reduced_factors=[
            "currency_trading",  # 汇率交易
            "commodity_trading",  # 大宗商品交易
        ],
        a_stock_signals=[
            "mlf_rate",  # MLF利率
            "lpr_rate",  # LPR利率
            "social_financing",  # 社会融资规模
            "pmi",  # PMI指数
        ],
        adjustment_notes="A股宏观驱动明显，需密切关注货币政策和经济周期",
    ),

    # 技术分析策略A股调整
    "technical_analyst": AStockStrategyAdjustment(
        original_strategy="Technical Analyst",
        weight_adjustment={
            "trend_following": 1.2,  # 趋势跟踪权重提高
            "momentum": 1.3,  # 动量权重提高
            "volume_analysis": 1.4,  # 成交量分析权重提高
            "mean_reversion": 0.8,  # 均值回归权重降低（A股趋势性更强）
        },
        additional_factors=[
            "limit_up_down",  # 涨跌停分析
            "dragon_tiger",  # 龙虎榜分析
            "northbound_flow",  # 北向资金
            "margin_trading",  # 融资融券
        ],
        reduced_factors=[
            "short_interest",  # 做空兴趣
        ],
        a_stock_signals=[
            "continuous_limit_up",  # 连续涨停
            "volume_spike",  # 成交量异动
            "capital_flow",  # 资金流向
            "turnover_rate",  # 换手率
        ],
        adjustment_notes="A股技术分析需特别关注涨跌停板、资金流向和换手率",
    ),

    # 基本面分析策略A股调整
    "fundamentals_analyst": AStockStrategyAdjustment(
        original_strategy="Fundamentals Analyst",
        weight_adjustment={
            "roe": 1.2,  # ROE权重提高
            "revenue_growth": 1.1,  # 营收增长权重提高
            "cash_flow": 1.3,  # 现金流权重提高
            "debt_ratio": 1.2,  # 负债率权重提高
        },
        additional_factors=[
            "state_ownership",  # 国有股比例
            "dividend_policy",  # 分红政策
            "industry_policy",  # 行业政策
            "esg_rating",  # ESG评级
        ],
        reduced_factors=[
            "gaap_comparison",  # GAAP对比
        ],
        a_stock_signals=[
            "performance_forecast",  # 业绩预告
            "performance_correction",  # 业绩修正
            "dividend_announcement",  # 分红公告
        ],
        adjustment_notes="A股基本面分析需关注业绩预告和分红政策",
    ),

    # 情绪分析策略A股调整
    "sentiment_analyst": AStockStrategyAdjustment(
        original_strategy="Sentiment Analyst",
        weight_adjustment={
            "retail_sentiment": 1.5,  # 散户情绪权重大幅提高
            "institutional_sentiment": 1.2,  # 机构情绪权重提高
            "media_sentiment": 1.3,  # 媒体情绪权重提高
        },
        additional_factors=[
            "social_media_heat",  # 社交媒体热度
            "forum_discussion",  # 论坛讨论热度
            "concept_popularity",  # 概念热度
            "retail_trading_ratio",  # 散户交易占比
        ],
        reduced_factors=[
            "options_sentiment",  # 期权情绪
            "short_ratio",  # 做空比例
        ],
        a_stock_signals=[
            "guba_sentiment",  # 股吧情绪
            "weibo_heat",  # 微博热度
            "wechat_articles",  # 微信文章
            "broker_recommendations",  # 券商推荐
        ],
        adjustment_notes="A股散户占比高，情绪分析需重点关注社交媒体和论坛讨论",
    ),
}


# A股行业权重调整
A_STOCK_INDUSTRY_WEIGHTS = {
    # 战略性新兴产业（高权重）
    "semiconductor": 1.5,  # 半导体
    "new_energy": 1.4,  # 新能源
    "artificial_intelligence": 1.4,  # 人工智能
    "biomedicine": 1.3,  # 生物医药
    "high_end_manufacturing": 1.3,  # 高端制造

    # 传统优势行业（中等权重）
    "consumer": 1.0,  # 消费
    "finance": 1.0,  # 金融
    "infrastructure": 0.9,  # 基建
    "real_estate": 0.7,  # 房地产

    # 周期性行业（低权重）
    "steel": 0.8,  # 钢铁
    "coal": 0.8,  # 煤炭
    "chemical": 0.9,  # 化工
}


# A股风险因子
A_STOCK_RISK_FACTORS = {
    # 政策风险
    "policy_risk": {
        "weight": 1.3,
        "factors": [
            "industry_regulation",  # 行业监管
            "anti_monopoly",  # 反垄断
            "environmental_protection",  # 环保
            "education_policy",  # 教育政策
        ],
    },

    # 流动性风险
    "liquidity_risk": {
        "weight": 1.2,
        "factors": [
            "trading_volume",  # 成交量
            "market_depth",  # 市场深度
            "margin_call_risk",  # 平仓风险
        ],
    },

    # 公司治理风险
    "governance_risk": {
        "weight": 1.2,
        "factors": [
            "controlling_shareholder",  # 控股股东
            "pledged_shares",  # 股权质押
            "related_party_transactions",  # 关联交易
        ],
    },

    # 市场风险
    "market_risk": {
        "weight": 1.0,
        "factors": [
            "systematic_risk",  # 系统性风险
            "sector_correlation",  # 板块相关性
            "style_rotation",  # 风格轮动
        ],
    },
}


def get_a_stock_adjusted_signal(
    strategy_name: str,
    original_signal: str,
    confidence: float,
    a_stock_factors: Dict[str, float] = None
) -> tuple[str, float]:
    """
    根据A股特点调整投资信号

    参数：
        strategy_name: 策略名称
        original_signal: 原始信号（bullish/bearish/neutral）
        confidence: 原始置信度
        a_stock_factors: A股特有因素

    返回：
        (调整后信号, 调整后置信度)
    """
    adjustment = A_STOCK_STRATEGY_ADJUSTMENTS.get(strategy_name)

    if not adjustment:
        return original_signal, confidence

    adjusted_confidence = confidence

    # 根据A股因素调整置信度
    if a_stock_factors:
        for factor, value in a_stock_factors.items():
            if factor in adjustment.a_stock_signals:
                # A股特有信号对置信度的影响
                if value > 0:
                    adjusted_confidence *= 1.1
                elif value < 0:
                    adjusted_confidence *= 0.9

    # 确保置信度在0-100范围内
    adjusted_confidence = max(0, min(100, adjusted_confidence))

    return original_signal, adjusted_confidence


def get_a_stock_industry_adjustment(industry: str) -> float:
    """
    获取A股行业权重调整

    参数：
        industry: 行业名称

    返回：
        权重调整系数
    """
    return A_STOCK_INDUSTRY_WEIGHTS.get(industry, 1.0)


def get_a_stock_risk_score(risk_factors: Dict[str, float]) -> float:
    """
    计算A股风险得分

    参数：
        risk_factors: 各类风险因素得分

    返回：
        综合风险得分（0-100）
    """
    total_score = 0.0
    total_weight = 0.0

    for risk_type, factors in A_STOCK_RISK_FACTORS.items():
        weight = factors["weight"]
        factor_scores = risk_factors.get(risk_type, {})

        if factor_scores:
            avg_score = sum(factor_scores.values()) / len(factor_scores)
            total_score += avg_score * weight
            total_weight += weight

    if total_weight > 0:
        return total_score / total_weight
    return 50.0  # 默认中等风险


# 导出
__all__ = [
    "AStockMarketFeature",
    "AStockStrategyAdjustment",
    "A_STOCK_STRATEGY_ADJUSTMENTS",
    "A_STOCK_INDUSTRY_WEIGHTS",
    "A_STOCK_RISK_FACTORS",
    "get_a_stock_adjusted_signal",
    "get_a_stock_industry_adjustment",
    "get_a_stock_risk_score",
]