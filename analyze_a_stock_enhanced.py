#!/usr/bin/env python3
"""
A股智能分析脚本 - 增强版
整合实时行情、技术分析、基本面数据
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

from src.tools.a_stock_api import AStockAPI, NorthboundFlow, SectorData
from src.utils.tencent_api import get_stock_quotes, StockQuote

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class StockAnalysisResult:
    """股票分析结果"""
    ticker: str
    name: str
    sector: str
    market: str
    price: float
    change_pct: float
    volume: int
    turnover_rate: Optional[float]
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    roe: Optional[float]
    confidence: int
    signal: str  # bullish/neutral/bearish
    reasoning: str
    signals: List[str]
    technical_score: int  # 技术面评分 0-100
    fundamental_score: int  # 基本面评分 0-100
    sentiment_score: int  # 情绪面评分 0-100


# 行业配置
SECTOR_CONFIG = {
    "白酒": {"trend": "stable", "base_confidence": 70, "reasoning": "消费升级，品牌集中度提升，现金流充沛"},
    "新能源电池": {"trend": "growth", "base_confidence": 72, "reasoning": "全球电动化趋势，储能需求增长，龙头优势明显"},
    "新能源汽车": {"trend": "growth", "base_confidence": 70, "reasoning": "销量持续增长，出海加速，产业链完善"},
    "电力": {"trend": "stable", "base_confidence": 68, "reasoning": "现金流稳定，高分红，防御性资产"},
    "医疗器械": {"trend": "growth", "base_confidence": 66, "reasoning": "国产替代，海外拓展，人口老龄化需求"},
    "光伏逆变器": {"trend": "growth", "base_confidence": 65, "reasoning": "光伏装机增长，储能业务放量"},
    "家电": {"trend": "stable", "base_confidence": 64, "reasoning": "龙头优势，海外业务占比高，估值合理"},
    "光伏": {"trend": "recovery", "base_confidence": 63, "reasoning": "行业周期底部，技术迭代，产能出清"},
    "工业自动化": {"trend": "growth", "base_confidence": 62, "reasoning": "国产替代空间大，新能源业务增长"},
    "银行": {"trend": "stable", "base_confidence": 50, "reasoning": "估值低，息差收窄压力，分红稳定"},
    "保险": {"trend": "stable", "base_confidence": 48, "reasoning": "投资收益承压，转型中，长期价值"},
    "医药": {"trend": "stable", "base_confidence": 52, "reasoning": "集采影响，创新药布局，老龄化需求"},
    "互联网金融": {"trend": "growth", "base_confidence": 55, "reasoning": "市场活跃度提升，财富管理转型"},
    "医疗": {"trend": "growth", "base_confidence": 53, "reasoning": "医疗服务需求增长，连锁化趋势"},
    "房地产": {"trend": "decline", "base_confidence": 35, "reasoning": "行业调整期，销售承压，政策托底"},
    "零售": {"trend": "decline", "base_confidence": 40, "reasoning": "消费复苏缓慢，竞争激烈"},
    "安防": {"trend": "stable", "base_confidence": 42, "reasoning": "海外市场受限，增长放缓，AI赋能"},
    "芯片": {"trend": "growth", "base_confidence": 60, "reasoning": "国产替代加速，政策支持"},
    "半导体设备": {"trend": "growth", "base_confidence": 61, "reasoning": "国产替代空间大，技术突破"},
    "电池": {"trend": "growth", "base_confidence": 65, "reasoning": "新能源需求旺盛，技术迭代"},
    "生物制药": {"trend": "growth", "base_confidence": 58, "reasoning": "创新药发展，疫苗需求"},
    "金融软件": {"trend": "growth", "base_confidence": 56, "reasoning": "金融科技发展，AI赋能"},
    "养殖": {"trend": "cyclical", "base_confidence": 45, "reasoning": "猪周期影响，成本控制"},
    "保健品": {"trend": "stable", "base_confidence": 50, "reasoning": "健康意识提升，竞争加剧"},
    "化工": {"trend": "cyclical", "base_confidence": 55, "reasoning": "周期性行业，龙头优势"},
    "食品饮料": {"trend": "stable", "base_confidence": 62, "reasoning": "消费刚需，品牌价值"},
    "物流": {"trend": "stable", "base_confidence": 52, "reasoning": "电商发展，成本压力"},
}

# 股票池
STOCK_POOL = {
    # 主板蓝筹
    "600519": {"name": "贵州茅台", "sector": "白酒", "market": "主板"},
    "601318": {"name": "中国平安", "sector": "保险", "market": "主板"},
    "600036": {"name": "招商银行", "sector": "银行", "market": "主板"},
    "601166": {"name": "兴业银行", "sector": "银行", "market": "主板"},
    "600276": {"name": "恒瑞医药", "sector": "医药", "market": "主板"},
    "600887": {"name": "伊利股份", "sector": "食品饮料", "market": "主板"},
    "601888": {"name": "中国中免", "sector": "零售", "market": "主板"},
    "600309": {"name": "万华化学", "sector": "化工", "market": "主板"},
    "601012": {"name": "隆基绿能", "sector": "光伏", "market": "主板"},
    "600900": {"name": "长江电力", "sector": "电力", "market": "主板"},
    "000001": {"name": "平安银行", "sector": "银行", "market": "主板"},
    "000002": {"name": "万科A", "sector": "房地产", "market": "主板"},
    "000333": {"name": "美的集团", "sector": "家电", "market": "主板"},
    "000651": {"name": "格力电器", "sector": "家电", "market": "主板"},
    "000858": {"name": "五粮液", "sector": "白酒", "market": "主板"},
    "000568": {"name": "泸州老窖", "sector": "白酒", "market": "主板"},
    "002415": {"name": "海康威视", "sector": "安防", "market": "主板"},
    "002304": {"name": "洋河股份", "sector": "白酒", "market": "主板"},
    "002594": {"name": "比亚迪", "sector": "新能源汽车", "market": "主板"},
    "002352": {"name": "顺丰控股", "sector": "物流", "market": "主板"},
    # 创业板龙头
    "300750": {"name": "宁德时代", "sector": "新能源电池", "market": "创业板"},
    "300059": {"name": "东方财富", "sector": "互联网金融", "market": "创业板"},
    "300015": {"name": "爱尔眼科", "sector": "医疗", "market": "创业板"},
    "300014": {"name": "亿纬锂能", "sector": "电池", "market": "创业板"},
    "300124": {"name": "汇川技术", "sector": "工业自动化", "market": "创业板"},
    "300274": {"name": "阳光电源", "sector": "光伏逆变器", "market": "创业板"},
    "300122": {"name": "智飞生物", "sector": "生物制药", "market": "创业板"},
    "300347": {"name": "泰格医药", "sector": "医药", "market": "创业板"},
    "300760": {"name": "迈瑞医疗", "sector": "医疗器械", "market": "创业板"},
    "300033": {"name": "同花顺", "sector": "金融软件", "market": "创业板"},
    "300498": {"name": "温氏股份", "sector": "养殖", "market": "创业板"},
    "300146": {"name": "汤臣倍健", "sector": "保健品", "market": "创业板"},
    "300408": {"name": "晶盛机电", "sector": "半导体设备", "market": "创业板"},
    "300661": {"name": "圣邦股份", "sector": "芯片", "market": "创业板"},
    "300782": {"name": "卓胜微", "sector": "芯片", "market": "创业板"},
}


def calculate_technical_score(quote: StockQuote, prices: List) -> int:
    """计算技术面评分"""
    score = 50  # 基础分

    # 涨跌幅调整
    if quote.change_pct > 5:
        score += 15
    elif quote.change_pct > 3:
        score += 10
    elif quote.change_pct > 0:
        score += 5
    elif quote.change_pct < -5:
        score -= 15
    elif quote.change_pct < -3:
        score -= 10
    elif quote.change_pct < 0:
        score -= 5

    # 成交量调整
    if quote.volume > 1000000:
        score += 5
    elif quote.volume > 500000:
        score += 3

    # 价格位置（相对前收盘价）
    if quote.high > quote.prev_close and quote.low < quote.prev_close:
        # 日内波动
        if quote.price > (quote.high + quote.low) / 2:
            score += 5  # 收在日内中位以上

    return max(0, min(100, score))


def calculate_fundamental_score(metrics: List, sector: str) -> int:
    """计算基本面评分"""
    score = 50

    if not metrics:
        return score

    latest = metrics[0] if metrics else None
    if not latest:
        return score

    # PE估值
    if latest.price_to_earnings_ratio:
        if latest.price_to_earnings_ratio < 15:
            score += 10
        elif latest.price_to_earnings_ratio < 25:
            score += 5
        elif latest.price_to_earnings_ratio > 50:
            score -= 10

    # PB估值
    if latest.price_to_book_ratio:
        if latest.price_to_book_ratio < 2:
            score += 5
        elif latest.price_to_book_ratio > 5:
            score -= 5

    # ROE
    if latest.return_on_equity:
        if latest.return_on_equity > 0.15:
            score += 10
        elif latest.return_on_equity > 0.10:
            score += 5
        elif latest.return_on_equity < 0.05:
            score -= 10

    # 毛利率
    if latest.gross_margin:
        if latest.gross_margin > 0.40:
            score += 5
        elif latest.gross_margin < 0.20:
            score -= 5

    return max(0, min(100, score))


def calculate_sentiment_score(northbound_net: float, sector_trend: str) -> int:
    """计算情绪面评分"""
    score = 50

    # 北向资金
    if northbound_net > 50:
        score += 15
    elif northbound_net > 20:
        score += 10
    elif northbound_net > 0:
        score += 5
    elif northbound_net < -50:
        score -= 15
    elif northbound_net < -20:
        score -= 10
    elif northbound_net < 0:
        score -= 5

    # 行业趋势
    if sector_trend == "growth":
        score += 10
    elif sector_trend == "decline":
        score -= 10

    return max(0, min(100, score))


def analyze_stock(
    quote: StockQuote,
    info: Dict,
    api: AStockAPI,
    northbound_data: List[NorthboundFlow],
    end_date: str
) -> StockAnalysisResult:
    """分析单只股票"""
    sector = info["sector"]
    sector_config = SECTOR_CONFIG.get(sector, {"trend": "neutral", "base_confidence": 50, "reasoning": ""})

    # 获取历史价格数据
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    prices = api.get_prices(quote.code, start_date, end_date)

    # 获取财务指标
    metrics = api.get_financial_metrics(quote.code, end_date, limit=5)

    # 计算各项评分
    technical_score = calculate_technical_score(quote, prices)
    fundamental_score = calculate_fundamental_score(metrics, sector)

    # 获取北向资金净买入
    northbound_net = 0
    if northbound_data:
        northbound_net = northbound_data[0].net_buy if northbound_data else 0

    sentiment_score = calculate_sentiment_score(northbound_net, sector_config["trend"])

    # 综合置信度
    confidence = int(
        sector_config["base_confidence"] * 0.3 +
        technical_score * 0.3 +
        fundamental_score * 0.25 +
        sentiment_score * 0.15
    )

    # 根据涨跌幅微调
    if quote.change_pct > 2:
        confidence += 3
    elif quote.change_pct < -2:
        confidence -= 3

    # 限制置信度范围
    confidence = max(0, min(100, confidence))

    # 判断信号
    if confidence >= 65:
        signal = "bullish"
    elif confidence >= 40:
        signal = "neutral"
    else:
        signal = "bearish"

    # 生成信号列表
    signals = []
    if sector_config["trend"] == "growth":
        signals.append("行业景气")
    elif sector_config["trend"] == "decline":
        signals.append("行业承压")
    elif sector_config["trend"] == "recovery":
        signals.append("行业复苏")

    if quote.change_pct > 0:
        signals.append("当日上涨")
    else:
        signals.append("当日下跌")

    if technical_score >= 60:
        signals.append("技术面强")
    elif technical_score <= 40:
        signals.append("技术面弱")

    if fundamental_score >= 60:
        signals.append("基本面优")
    elif fundamental_score <= 40:
        signals.append("基本面差")

    # 计算换手率（简化）
    turnover_rate = None
    if prices and len(prices) > 0:
        avg_volume = sum(p.volume for p in prices[-5:]) / min(5, len(prices)) if prices else 0
        if avg_volume > 0:
            turnover_rate = quote.volume / avg_volume if avg_volume > 0 else None

    # 获取财务数据
    pe_ratio = None
    pb_ratio = None
    roe = None
    if metrics:
        latest = metrics[0]
        pe_ratio = latest.price_to_earnings_ratio
        pb_ratio = latest.price_to_book_ratio
        roe = latest.return_on_equity

    return StockAnalysisResult(
        ticker=quote.code,
        name=quote.name,
        sector=sector,
        market=info["market"],
        price=quote.price,
        change_pct=quote.change_pct,
        volume=quote.volume,
        turnover_rate=turnover_rate,
        pe_ratio=pe_ratio,
        pb_ratio=pb_ratio,
        roe=roe,
        confidence=confidence,
        signal=signal,
        reasoning=sector_config["reasoning"],
        signals=signals,
        technical_score=technical_score,
        fundamental_score=fundamental_score,
        sentiment_score=sentiment_score
    )


def main():
    print("=" * 70)
    print("A股智能分析系统 - 增强版")
    print(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 初始化API
    api = AStockAPI()
    if not api.is_available():
        print("错误: A股数据源不可用，请检查AKShare安装")
        return

    # 获取股票代码列表
    codes = list(STOCK_POOL.keys())
    print(f"\n总计分析股票: {len(codes)} 只")
    print(f"  - 主板股票: {len([c for c in codes if STOCK_POOL[c]['market'] == '主板'])} 只")
    print(f"  - 创业板股票: {len([c for c in codes if STOCK_POOL[c]['market'] == '创业板'])} 只")

    # 获取北向资金数据
    print("\n正在获取北向资金数据...")
    northbound_data = api.get_northbound_flow(days=5)
    if northbound_data:
        latest_flow = northbound_data[0]
        print(f"最新北向资金: 净买入 {latest_flow.net_buy:.2f} 亿元")
    else:
        print("北向资金数据获取失败，使用默认值")

    # 批量获取实时行情
    print("\n正在获取实时行情数据...")
    quotes = get_stock_quotes(codes)
    print(f"成功获取 {len(quotes)} 只股票实时数据")

    # 分析每只股票
    end_date = datetime.now().strftime("%Y-%m-%d")
    results = []

    for code, info in STOCK_POOL.items():
        if code in quotes:
            try:
                analysis = analyze_stock(quotes[code], info, api, northbound_data, end_date)
                results.append(analysis)
            except Exception as e:
                logger.error(f"分析 {code} 失败: {e}")
                results.append(StockAnalysisResult(
                    ticker=code,
                    name=info["name"],
                    sector=info["sector"],
                    market=info["market"],
                    price=0,
                    change_pct=0,
                    volume=0,
                    turnover_rate=None,
                    pe_ratio=None,
                    pb_ratio=None,
                    roe=None,
                    confidence=50,
                    signal="neutral",
                    reasoning="分析失败",
                    signals=["数据异常"],
                    technical_score=50,
                    fundamental_score=50,
                    sentiment_score=50
                ))
        else:
            results.append(StockAnalysisResult(
                ticker=code,
                name=info["name"],
                sector=info["sector"],
                market=info["market"],
                price=0,
                change_pct=0,
                volume=0,
                turnover_rate=None,
                pe_ratio=None,
                pb_ratio=None,
                roe=None,
                confidence=50,
                signal="neutral",
                reasoning="数据获取失败",
                signals=["数据缺失"],
                technical_score=50,
                fundamental_score=50,
                sentiment_score=50
            ))

    # 按置信度排序
    results.sort(key=lambda x: x.confidence, reverse=True)

    # 分类结果
    bullish = [r for r in results if r.signal == "bullish"]
    neutral = [r for r in results if r.signal == "neutral"]
    bearish = [r for r in results if r.signal == "bearish"]

    # 显示看涨标的
    print("\n" + "=" * 70)
    print(f"看涨标的汇总 (共 {len(bullish)} 只)")
    print("=" * 70)

    for i, stock in enumerate(bullish, 1):
        print(f"\n{i}. {stock.ticker} {stock.name} ({stock.sector})")
        print(f"   价格: {stock.price:.2f}  涨跌: {stock.change_pct:+.2f}%")
        print(f"   置信度: {stock.confidence}%")
        print(f"   技术面: {stock.technical_score}  基本面: {stock.fundamental_score}  情绪面: {stock.sentiment_score}")
        if stock.pe_ratio:
            print(f"   PE: {stock.pe_ratio:.2f}  PB: {stock.pb_ratio:.2f}  ROE: {stock.roe*100:.2f}%" if stock.roe else f"   PE: {stock.pe_ratio:.2f}")
        print(f"   理由: {stock.reasoning}")
        print(f"   信号: {', '.join(stock.signals)}")

    # 显示中性标的
    print("\n" + "-" * 70)
    print(f"中性标的 (共 {len(neutral)} 只)")
    print("-" * 70)
    for stock in neutral[:10]:
        print(f"  {stock.ticker} {stock.name} - 置信度: {stock.confidence}%")

    # 显示看跌标的
    print("\n" + "-" * 70)
    print(f"谨慎标的 (共 {len(bearish)} 只)")
    print("-" * 70)
    for stock in bearish:
        print(f"  {stock.ticker} {stock.name} - 置信度: {stock.confidence}%")
        print(f"    原因: {stock.reasoning}")

    # 行业分布
    print("\n" + "=" * 70)
    print("看涨标的行业分布")
    print("=" * 70)
    sector_count = {}
    for stock in bullish:
        sector = stock.sector
        sector_count[sector] = sector_count.get(sector, 0) + 1

    for sector, count in sorted(sector_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  {sector}: {count} 只")

    # 保存结果
    output = {
        "analysis_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "total_analyzed": len(results),
        "bullish_count": len(bullish),
        "neutral_count": len(neutral),
        "bearish_count": len(bearish),
        "northbound_flow": {
            "net_buy": northbound_data[0].net_buy if northbound_data else 0,
            "date": northbound_data[0].date if northbound_data else ""
        },
        "bullish_stocks": [asdict(s) for s in bullish],
        "neutral_stocks": [asdict(s) for s in neutral],
        "bearish_stocks": [asdict(s) for s in bearish],
        "sector_distribution": sector_count
    }

    output_file = "a_stock_analysis_enhanced.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n详细结果已保存到: {output_file}")

    print("\n" + "=" * 70)
    print("免责声明: 以上分析仅供参考，不构成投资建议。")
    print("投资有风险，入市需谨慎。")
    print("=" * 70)


if __name__ == "__main__":
    main()
