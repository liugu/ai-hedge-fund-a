#!/usr/bin/env python3
"""
A股批量分析脚本 - 使用腾讯财经API
分析主板和创业板股票，找出看涨标的
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

from src.utils.tencent_api import get_stock_quotes, StockQuote


@dataclass
class StockAnalysis:
    """股票分析结果"""
    ticker: str
    name: str
    sector: str
    market: str
    price: float
    change_pct: float
    volume: int
    confidence: int
    signal: str  # bullish/neutral/bearish
    reasoning: str
    signals: List[str]


# 股票列表及其行业分类
STOCK_INFO = {
    # 主板股票
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
    # 创业板股票
    "300750": {"name": "宁德时代", "sector": "新能源电池", "market": "创业板"},
    "300059": {"name": "东方财富", "sector": "互联网金融", "market": "创业板"},
    "300015": {"name": "爱尔眼科", "sector": "医疗", "market": "创业板"},
    "300014": {"name": "亿纬锂能", "sector": "电池", "market": "创业板"},
    "300124": {"name": "汇川技术", "sector": "工业自动化", "market": "创业板"},
    "300274": {"name": "阳光电源", "sector": "光伏逆变器", "market": "创业板"},
    "300122": {"name": "智飞生物", "sector": "生物制药", "market": "创业板"},
    "300347": {"name": "泰格医药", "sector": "医药研发", "market": "创业板"},
    "300760": {"name": "迈瑞医疗", "sector": "医疗器械", "market": "创业板"},
    "300033": {"name": "同花顺", "sector": "金融软件", "market": "创业板"},
    "300498": {"name": "温氏股份", "sector": "养殖", "market": "创业板"},
    "300146": {"name": "汤臣倍健", "sector": "保健品", "market": "创业板"},
    "300408": {"name": "晶盛机电", "sector": "半导体设备", "market": "创业板"},
    "300661": {"name": "圣邦股份", "sector": "芯片", "market": "创业板"},
    "300782": {"name": "卓胜微", "sector": "射频芯片", "market": "创业板"},
}

# 行业景气度和投资逻辑
SECTOR_ANALYSIS = {
    "白酒": {"trend": "stable", "confidence_base": 70, "reasoning": "消费升级，品牌集中度提升"},
    "新能源电池": {"trend": "growth", "confidence_base": 72, "reasoning": "全球电动化趋势，储能需求增长"},
    "新能源汽车": {"trend": "growth", "confidence_base": 70, "reasoning": "销量持续增长，出海加速"},
    "电力": {"trend": "stable", "confidence_base": 68, "reasoning": "现金流稳定，高分红，防御性资产"},
    "医疗器械": {"trend": "growth", "confidence_base": 66, "reasoning": "国产替代，海外拓展"},
    "光伏逆变器": {"trend": "growth", "confidence_base": 65, "reasoning": "光伏装机增长，储能业务放量"},
    "家电": {"trend": "stable", "confidence_base": 64, "reasoning": "龙头优势，海外业务占比高"},
    "光伏": {"trend": "recovery", "confidence_base": 63, "reasoning": "行业周期底部，技术迭代"},
    "工业自动化": {"trend": "growth", "confidence_base": 62, "reasoning": "国产替代空间大，新能源业务增长"},
    "银行": {"trend": "stable", "confidence_base": 50, "reasoning": "估值低，息差收窄压力"},
    "保险": {"trend": "stable", "confidence_base": 48, "reasoning": "投资收益承压，转型中"},
    "医药": {"trend": "stable", "confidence_base": 52, "reasoning": "集采影响，创新药布局"},
    "互联网金融": {"trend": "growth", "confidence_base": 55, "reasoning": "市场活跃度提升"},
    "医疗": {"trend": "growth", "confidence_base": 53, "reasoning": "医疗服务需求增长"},
    "房地产": {"trend": "decline", "confidence_base": 35, "reasoning": "行业调整期，销售承压"},
    "零售": {"trend": "decline", "confidence_base": 40, "reasoning": "消费复苏缓慢"},
    "安防": {"trend": "stable", "confidence_base": 42, "reasoning": "海外市场受限，增长放缓"},
}


def analyze_stock(quote: StockQuote, info: Dict) -> StockAnalysis:
    """分析单只股票"""
    sector = info["sector"]
    sector_data = SECTOR_ANALYSIS.get(sector, {"trend": "neutral", "confidence_base": 50, "reasoning": ""})

    # 基础置信度
    confidence = sector_data["confidence_base"]

    # 根据涨跌幅调整
    if quote.change_pct > 2:
        confidence += 5
    elif quote.change_pct < -2:
        confidence -= 5

    # 根据成交量调整（相对于价格）
    if quote.volume > 100000:
        confidence += 3

    # 限制置信度范围
    confidence = max(0, min(100, confidence))

    # 判断信号
    if confidence >= 60:
        signal = "bullish"
    elif confidence >= 40:
        signal = "neutral"
    else:
        signal = "bearish"

    # 生成信号列表
    signals = []
    if sector_data["trend"] == "growth":
        signals.append("行业景气")
    elif sector_data["trend"] == "decline":
        signals.append("行业承压")

    if quote.change_pct > 0:
        signals.append("当日上涨")
    else:
        signals.append("当日下跌")

    if confidence >= 65:
        signals.append("看好")
    elif confidence <= 40:
        signals.append("谨慎")

    return StockAnalysis(
        ticker=quote.code,
        name=quote.name,
        sector=sector,
        market=info["market"],
        price=quote.price,
        change_pct=quote.change_pct,
        volume=quote.volume,
        confidence=confidence,
        signal=signal,
        reasoning=sector_data["reasoning"],
        signals=signals
    )


def main():
    print("=" * 60)
    print("A股主板和创业板股票分析")
    print(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 获取所有股票代码
    codes = list(STOCK_INFO.keys())
    print(f"\n总计分析股票: {len(codes)} 只")
    print(f"  - 主板股票: {len([c for c in codes if STOCK_INFO[c]['market'] == '主板'])} 只")
    print(f"  - 创业板股票: {len([c for c in codes if STOCK_INFO[c]['market'] == '创业板'])} 只")

    # 批量获取行情数据
    print("\n正在获取实时行情数据...")
    quotes = get_stock_quotes(codes)
    print(f"成功获取 {len(quotes)} 只股票数据")

    # 分析每只股票
    results = []
    for code, info in STOCK_INFO.items():
        if code in quotes:
            analysis = analyze_stock(quotes[code], info)
            results.append(analysis)
        else:
            # 如果获取失败，使用默认数据
            results.append(StockAnalysis(
                ticker=code,
                name=info["name"],
                sector=info["sector"],
                market=info["market"],
                price=0,
                change_pct=0,
                volume=0,
                confidence=50,
                signal="neutral",
                reasoning="数据获取失败",
                signals=["数据缺失"]
            ))

    # 按置信度排序
    results.sort(key=lambda x: x.confidence, reverse=True)

    # 显示看涨标的
    bullish = [r for r in results if r.signal == "bullish"]
    neutral = [r for r in results if r.signal == "neutral"]
    bearish = [r for r in results if r.signal == "bearish"]

    print("\n" + "=" * 60)
    print(f"看涨标的汇总 (共 {len(bullish)} 只)")
    print("=" * 60)

    for i, stock in enumerate(bullish, 1):
        print(f"\n{i}. {stock.ticker} {stock.name} ({stock.sector})")
        print(f"   价格: {stock.price:.2f}  涨跌: {stock.change_pct:+.2f}%")
        print(f"   置信度: {stock.confidence}%")
        print(f"   理由: {stock.reasoning}")
        print(f"   信号: {', '.join(stock.signals)}")

    # 显示中性标的
    print("\n" + "-" * 60)
    print(f"中性标的 (共 {len(neutral)} 只)")
    print("-" * 60)
    for stock in neutral[:10]:
        print(f"  {stock.ticker} {stock.name} - 置信度: {stock.confidence}%")

    # 显示看跌标的
    print("\n" + "-" * 60)
    print(f"谨慎标的 (共 {len(bearish)} 只)")
    print("-" * 60)
    for stock in bearish:
        print(f"  {stock.ticker} {stock.name} - 置信度: {stock.confidence}%")
        print(f"    原因: {stock.reasoning}")

    # 行业分布
    print("\n" + "=" * 60)
    print("看涨标的行业分布")
    print("=" * 60)
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
        "bullish_stocks": [asdict(s) for s in bullish],
        "neutral_stocks": [asdict(s) for s in neutral],
        "bearish_stocks": [asdict(s) for s in bearish],
        "sector_distribution": sector_count
    }

    with open("bullish_analysis_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n详细结果已保存到: bullish_analysis_results.json")

    print("\n" + "=" * 60)
    print("免责声明: 以上分析仅供参考，不构成投资建议。")
    print("投资有风险，入市需谨慎。")
    print("=" * 60)


if __name__ == "__main__":
    main()
