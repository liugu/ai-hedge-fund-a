#!/usr/bin/env python3
"""
A股综合分析系统
整合实时行情、技术指标、板块轮动、资金流向分析
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from src.tools.a_stock_api import AStockAPI
from src.utils.tencent_api import get_stock_quotes, StockQuote
from src.utils.eastmoney_api import EastMoneyAPI, KLineData, FundFlow
from src.utils.technical_indicators import TechnicalAnalyzer, analyze_technical
from src.utils.sector_rotation import SectorRotationAnalyzer, analyze_sector_rotation, print_rotation_analysis
from src.utils.cache_enhanced import get_cache

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ComprehensiveAnalysis:
    """综合分析结果"""
    ticker: str
    name: str
    sector: str
    market: str

    # 价格数据
    price: float
    change_pct: float
    volume: int

    # 技术指标
    technical_trend: str
    technical_strength: int
    macd_signal: str
    kdj_signal: str
    rsi_signal: str
    ma_signal: str

    # 资金流向
    main_net_inflow: float
    fund_flow_signal: str

    # 基本面
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    roe: Optional[float]

    # 综合评分
    total_score: int
    confidence: int
    signal: str
    recommendation: str


class ComprehensiveAnalyzer:
    """综合分析器"""

    # 股票池
    STOCK_POOL = {
        # 主板蓝筹
        "600519": {"name": "贵州茅台", "sector": "白酒", "market": "主板"},
        "601318": {"name": "中国平安", "sector": "保险", "market": "主板"},
        "600036": {"name": "招商银行", "sector": "银行", "market": "主板"},
        "600887": {"name": "伊利股份", "sector": "食品饮料", "market": "主板"},
        "600900": {"name": "长江电力", "sector": "电力", "market": "主板"},
        "000333": {"name": "美的集团", "sector": "家电", "market": "主板"},
        "000858": {"name": "五粮液", "sector": "白酒", "market": "主板"},
        "002594": {"name": "比亚迪", "sector": "新能源汽车", "market": "主板"},
        # 创业板龙头
        "300750": {"name": "宁德时代", "sector": "新能源电池", "market": "创业板"},
        "300059": {"name": "东方财富", "sector": "互联网金融", "market": "创业板"},
        "300760": {"name": "迈瑞医疗", "sector": "医疗器械", "market": "创业板"},
        "300124": {"name": "汇川技术", "sector": "工业自动化", "market": "创业板"},
    }

    def __init__(self, use_cache: bool = True):
        """初始化分析器"""
        self.a_stock_api = AStockAPI()
        self.eastmoney_api = EastMoneyAPI()
        self.cache = get_cache() if use_cache else None

    def analyze_stock(self, ticker: str, info: Dict) -> Optional[ComprehensiveAnalysis]:
        """分析单只股票"""
        try:
            # 获取实时行情
            quotes = get_stock_quotes([ticker])
            if ticker not in quotes:
                logger.warning(f"无法获取 {ticker} 的实时行情")
                return None

            quote = quotes[ticker]

            # 获取K线数据（用于技术分析）
            cache_key = f"kline:{ticker}"
            klines = self.cache.get(cache_key) if self.cache else None
            if not klines:
                klines = self.eastmoney_api.get_kline_data(ticker, count=60)
                if self.cache and klines:
                    self.cache.set(cache_key, klines, ttl=300)  # 缓存5分钟

            # 技术分析
            technical_result = self._analyze_technical(klines, quote)

            # 资金流向
            fund_flow = self._get_fund_flow(ticker)

            # 基本面数据
            fundamentals = self._get_fundamentals(ticker)

            # 综合评分
            total_score, confidence, signal, recommendation = self._calculate_comprehensive_score(
                quote, technical_result, fund_flow, fundamentals, info
            )

            return ComprehensiveAnalysis(
                ticker=ticker,
                name=quote.name,
                sector=info["sector"],
                market=info["market"],
                price=quote.price,
                change_pct=quote.change_pct,
                volume=quote.volume,
                technical_trend=technical_result.get('trend', 'neutral'),
                technical_strength=technical_result.get('strength', 50),
                macd_signal=technical_result.get('macd_signal', 'neutral'),
                kdj_signal=technical_result.get('kdj_signal', 'neutral'),
                rsi_signal=technical_result.get('rsi_signal', 'neutral'),
                ma_signal=technical_result.get('ma_signal', 'neutral'),
                main_net_inflow=fund_flow.main_net_inflow if fund_flow else 0,
                fund_flow_signal=self._get_fund_flow_signal(fund_flow),
                pe_ratio=fundamentals.get('pe'),
                pb_ratio=fundamentals.get('pb'),
                roe=fundamentals.get('roe'),
                total_score=total_score,
                confidence=confidence,
                signal=signal,
                recommendation=recommendation
            )

        except Exception as e:
            logger.error(f"分析 {ticker} 失败: {e}")
            return None

    def _analyze_technical(self, klines: List[KLineData], quote: StockQuote) -> Dict:
        """技术分析"""
        result = {
            'trend': 'neutral',
            'strength': 50,
            'macd_signal': 'neutral',
            'kdj_signal': 'neutral',
            'rsi_signal': 'neutral',
            'ma_signal': 'neutral'
        }

        if not klines or len(klines) < 30:
            return result

        # 提取价格数据
        closes = [k.close for k in klines]
        highs = [k.high for k in klines]
        lows = [k.low for k in klines]

        # 计算技术指标
        analyzer = TechnicalAnalyzer(closes, highs, lows)
        indicators = analyzer.calculate_all()

        result['trend'] = indicators.trend
        result['strength'] = indicators.signal_strength

        # MACD信号
        if indicators.macd and indicators.macd_signal:
            if indicators.macd > indicators.macd_signal:
                result['macd_signal'] = 'bullish'
            else:
                result['macd_signal'] = 'bearish'

        # KDJ信号
        if indicators.kdj_j:
            if indicators.kdj_j < 20:
                result['kdj_signal'] = 'bullish'  # 超卖
            elif indicators.kdj_j > 80:
                result['kdj_signal'] = 'bearish'  # 超买

        # RSI信号
        if indicators.rsi_12:
            if indicators.rsi_12 < 30:
                result['rsi_signal'] = 'bullish'  # 超卖
            elif indicators.rsi_12 > 70:
                result['rsi_signal'] = 'bearish'  # 超买

        # MA信号
        if indicators.ma5 and indicators.ma10 and indicators.ma20:
            if indicators.ma5 > indicators.ma10 > indicators.ma20:
                result['ma_signal'] = 'bullish'  # 多头排列
            elif indicators.ma5 < indicators.ma10 < indicators.ma20:
                result['ma_signal'] = 'bearish'  # 空头排列

        return result

    def _get_fund_flow(self, ticker: str) -> Optional[FundFlow]:
        """获取资金流向"""
        cache_key = f"fund_flow:{ticker}"
        flow = self.cache.get(cache_key) if self.cache else None
        if flow:
            return flow

        flow = self.eastmoney_api.get_fund_flow(ticker)
        if self.cache and flow:
            self.cache.set(cache_key, flow, ttl=300)

        return flow

    def _get_fund_flow_signal(self, flow: Optional[FundFlow]) -> str:
        """获取资金流向信号"""
        if not flow:
            return "无数据"

        if flow.main_net_inflow > 10000:  # 万
            return "资金大幅流入"
        elif flow.main_net_inflow > 0:
            return "资金流入"
        elif flow.main_net_inflow < -10000:
            return "资金大幅流出"
        elif flow.main_net_inflow < 0:
            return "资金流出"
        else:
            return "资金平衡"

    def _get_fundamentals(self, ticker: str) -> Dict:
        """获取基本面数据"""
        cache_key = f"fundamentals:{ticker}"
        fundamentals = self.cache.get(cache_key) if self.cache else None
        if fundamentals:
            return fundamentals

        fundamentals = {}
        try:
            metrics = self.a_stock_api.get_financial_metrics(ticker, datetime.now().strftime('%Y-%m-%d'), limit=1)
            if metrics:
                latest = metrics[0]
                fundamentals['pe'] = latest.price_to_earnings_ratio
                fundamentals['pb'] = latest.price_to_book_ratio
                fundamentals['roe'] = latest.return_on_equity
        except Exception as e:
            logger.warning(f"获取基本面数据失败: {e}")

        if self.cache:
            self.cache.set(cache_key, fundamentals, ttl=3600)  # 缓存1小时

        return fundamentals

    def _calculate_comprehensive_score(self, quote: StockQuote, technical: Dict,
                                        fund_flow: Optional[FundFlow], fundamentals: Dict,
                                        info: Dict) -> tuple:
        """计算综合评分"""
        score = 50  # 基础分
        signals = []

        # 技术面评分
        if technical['trend'] == 'bullish':
            score += 10
            signals.append("技术面看涨")
        elif technical['trend'] == 'bearish':
            score -= 10
            signals.append("技术面看跌")

        # 技术指标信号
        for key in ['macd_signal', 'kdj_signal', 'rsi_signal', 'ma_signal']:
            if technical.get(key) == 'bullish':
                score += 3
            elif technical.get(key) == 'bearish':
                score -= 3

        # 资金流向评分
        if fund_flow:
            if fund_flow.main_net_inflow > 5000:
                score += 8
                signals.append("主力资金流入")
            elif fund_flow.main_net_inflow > 0:
                score += 3
            elif fund_flow.main_net_inflow < -5000:
                score -= 8
                signals.append("主力资金流出")
            elif fund_flow.main_net_inflow < 0:
                score -= 3

        # 基本面评分
        if fundamentals.get('pe'):
            if fundamentals['pe'] < 15:
                score += 5
                signals.append("估值偏低")
            elif fundamentals['pe'] > 50:
                score -= 5
                signals.append("估值偏高")

        if fundamentals.get('roe') and fundamentals['roe'] > 0.15:
            score += 5
            signals.append("ROE优秀")

        # 涨跌幅调整
        if quote.change_pct > 3:
            score += 3
        elif quote.change_pct < -3:
            score -= 3

        # 限制分数范围
        score = max(0, min(100, score))

        # 计算置信度
        confidence = min(100, score + technical['strength'] // 2)

        # 判断信号
        if score >= 65:
            signal = "bullish"
        elif score >= 40:
            signal = "neutral"
        else:
            signal = "bearish"

        # 生成推荐
        if signal == "bullish":
            recommendation = f"建议关注，{', '.join(signals[:3])}"
        elif signal == "bearish":
            recommendation = f"建议谨慎，{', '.join(signals[:3])}"
        else:
            recommendation = "建议观望"

        return score, confidence, signal, recommendation

    def analyze_all(self) -> List[ComprehensiveAnalysis]:
        """分析所有股票"""
        results = []

        for ticker, info in self.STOCK_POOL.items():
            logger.info(f"正在分析 {ticker} {info['name']}...")
            analysis = self.analyze_stock(ticker, info)
            if analysis:
                results.append(analysis)

        # 按综合评分排序
        results.sort(key=lambda x: x.total_score, reverse=True)
        return results

    def analyze_sector(self) -> Dict:
        """分析板块"""
        try:
            # 获取板块数据
            sectors = self.eastmoney_api.get_sector_fund_flow()
            if sectors:
                analysis = analyze_sector_rotation(sectors)
                return {
                    'hot_sectors': [{'name': s.sector_name, 'change': s.change_pct, 'inflow': s.net_inflow}
                                   for s in analysis.hot_sectors],
                    'cold_sectors': [{'name': s.sector_name, 'change': s.change_pct, 'inflow': s.net_inflow}
                                    for s in analysis.cold_sectors],
                    'market_sentiment': analysis.market_sentiment,
                    'rotation_direction': analysis.rotation_direction,
                    'recommended': analysis.recommended_sectors
                }
        except Exception as e:
            logger.error(f"板块分析失败: {e}")

        return {}


def main():
    print("=" * 70)
    print("A股综合分析系统")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 初始化分析器
    analyzer = ComprehensiveAnalyzer()

    # 分析板块
    print("\n正在分析板块轮动...")
    sector_result = analyzer.analyze_sector()
    if sector_result:
        print(f"\n市场情绪: {sector_result.get('market_sentiment', 'N/A')}")
        print(f"轮动方向: {sector_result.get('rotation_direction', 'N/A')}")
        print(f"推荐板块: {', '.join(sector_result.get('recommended', []))}")

    # 分析个股
    print("\n正在分析个股...")
    results = analyzer.analyze_all()

    # 分类结果
    bullish = [r for r in results if r.signal == 'bullish']
    neutral = [r for r in results if r.signal == 'neutral']
    bearish = [r for r in results if r.signal == 'bearish']

    # 打印看涨标的
    print("\n" + "=" * 70)
    print(f"看涨标的 (共 {len(bullish)} 只)")
    print("=" * 70)

    for i, stock in enumerate(bullish, 1):
        print(f"\n{i}. {stock.ticker} {stock.name} ({stock.sector})")
        print(f"   价格: {stock.price:.2f}  涨跌: {stock.change_pct:+.2f}%")
        print(f"   综合评分: {stock.total_score}  置信度: {stock.confidence}%")
        print(f"   技术面: {stock.technical_trend} (强度: {stock.technical_strength}%)")
        print(f"   资金流向: {stock.fund_flow_signal} ({stock.main_net_inflow:.0f}万)")
        if stock.pe_ratio:
            print(f"   PE: {stock.pe_ratio:.2f}  PB: {stock.pb_ratio:.2f}" if stock.pb_ratio else f"   PE: {stock.pe_ratio:.2f}")
        print(f"   推荐: {stock.recommendation}")

    # 打印中性标的
    print("\n" + "-" * 70)
    print(f"中性标的 (共 {len(neutral)} 只)")
    print("-" * 70)
    for stock in neutral:
        print(f"  {stock.ticker} {stock.name} - 评分: {stock.total_score}")

    # 打印看跌标的
    print("\n" + "-" * 70)
    print(f"谨慎标的 (共 {len(bearish)} 只)")
    print("-" * 70)
    for stock in bearish:
        print(f"  {stock.ticker} {stock.name} - 评分: {stock.total_score}")
        print(f"    {stock.recommendation}")

    # 保存结果
    output = {
        "analysis_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "sector_analysis": sector_result,
        "stock_analysis": {
            "bullish": [asdict(s) for s in bullish],
            "neutral": [asdict(s) for s in neutral],
            "bearish": [asdict(s) for s in bearish]
        }
    }

    output_file = "comprehensive_analysis_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n分析结果已保存到: {output_file}")

    print("\n" + "=" * 70)
    print("免责声明: 以上分析仅供参考，不构成投资建议。")
    print("=" * 70)


if __name__ == "__main__":
    main()
