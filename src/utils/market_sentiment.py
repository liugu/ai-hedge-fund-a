"""
市场情绪分析模块

支持：
1. 恐慌贪婪指数
2. 市场宽度指标
3. 涨跌停统计
4. 新高新低统计
"""

import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class MarketSentiment:
    """市场情绪"""
    date: str
    fear_greed_index: float  # 恐慌贪婪指数 0-100
    market_breadth: float  # 市场宽度（上涨股票占比）
    advance_count: int  # 上涨股票数
    decline_count: int  # 下跌股票数
    limit_up_count: int  # 涨停数
    limit_down_count: int  # 跌停数
    new_high_count: int  # 创新高数
    new_low_count: int  # 创新低数
    sentiment_level: str  # 情绪等级


@dataclass
class SentimentSignal:
    """情绪信号"""
    signal: str  # bullish/bearish/neutral
    confidence: float
    reasoning: str


class MarketSentimentAnalyzer:
    """市场情绪分析器"""

    def __init__(self):
        # 情绪等级阈值
        self.extreme_fear_threshold = 20
        self.fear_threshold = 40
        self.greed_threshold = 60
        self.extreme_greed_threshold = 80

    def calculate_fear_greed_index(self, components: Dict[str, float]) -> float:
        """
        计算恐慌贪婪指数

        参数:
            components: 各项指标得分字典
                - market_breadth: 市场宽度
                - momentum: 动量
                - volatility: 波动率（反向）
                - northbound_flow: 北向资金
                - limit_ratio: 涨跌停比例
        """
        weights = {
            "market_breadth": 0.25,
            "momentum": 0.20,
            "volatility": 0.20,
            "northbound_flow": 0.20,
            "limit_ratio": 0.15,
        }

        total_score = 0
        total_weight = 0

        for key, weight in weights.items():
            if key in components:
                total_score += components[key] * weight
                total_weight += weight

        if total_weight == 0:
            return 50

        return total_score / total_weight

    def get_sentiment_level(self, fear_greed_index: float) -> str:
        """获取情绪等级"""
        if fear_greed_index < self.extreme_fear_threshold:
            return "极度恐慌"
        elif fear_greed_index < self.fear_threshold:
            return "恐慌"
        elif fear_greed_index < self.greed_threshold:
            return "中性"
        elif fear_greed_index < self.extreme_greed_threshold:
            return "贪婪"
        else:
            return "极度贪婪"

    def analyze_market_breadth(self, advance: int, decline: int) -> Dict:
        """
        分析市场宽度

        参数:
            advance: 上涨股票数
            decline: 下跌股票数
        """
        total = advance + decline
        if total == 0:
            return {"breadth": 0.5, "score": 50, "signal": "neutral"}

        breadth = advance / total

        # 转换为0-100分数
        score = breadth * 100

        # 判断信号
        if breadth > 0.7:
            signal = "bullish"
            reasoning = f"市场宽度强势：{advance}只上涨 vs {decline}只下跌，上涨占比{breadth*100:.1f}%"
        elif breadth > 0.55:
            signal = "bullish"
            reasoning = f"市场宽度偏强：上涨占比{breadth*100:.1f}%"
        elif breadth < 0.3:
            signal = "bearish"
            reasoning = f"市场宽度弱势：{advance}只上涨 vs {decline}只下跌，上涨占比{breadth*100:.1f}%"
        elif breadth < 0.45:
            signal = "bearish"
            reasoning = f"市场宽度偏弱：上涨占比{breadth*100:.1f}%"
        else:
            signal = "neutral"
            reasoning = f"市场宽度中性：上涨占比{breadth*100:.1f}%"

        return {
            "breadth": breadth,
            "score": score,
            "signal": signal,
            "reasoning": reasoning
        }

    def analyze_limit_moves(self, limit_up: int, limit_down: int) -> Dict:
        """
        分析涨跌停

        参数:
            limit_up: 涨停数
            limit_down: 跌停数
        """
        total = limit_up + limit_down
        if total == 0:
            return {"ratio": 0, "score": 50, "signal": "neutral"}

        # 涨停占比
        up_ratio = limit_up / total

        # 转换为分数
        score = up_ratio * 100

        # 判断信号
        if limit_up > limit_down * 3:
            signal = "bullish"
            reasoning = f"涨停潮：{limit_up}只涨停 vs {limit_down}只跌停"
        elif limit_up > limit_down * 1.5:
            signal = "bullish"
            reasoning = f"涨停偏多：{limit_up}只涨停 vs {limit_down}只跌停"
        elif limit_down > limit_up * 3:
            signal = "bearish"
            reasoning = f"跌停潮：{limit_down}只跌停 vs {limit_up}只涨停"
        elif limit_down > limit_up * 1.5:
            signal = "bearish"
            reasoning = f"跌停偏多：{limit_down}只跌停 vs {limit_up}只涨停"
        else:
            signal = "neutral"
            reasoning = f"涨跌停均衡：{limit_up}只涨停 vs {limit_down}只跌停"

        return {
            "ratio": up_ratio,
            "score": score,
            "signal": signal,
            "reasoning": reasoning
        }

    def analyze_new_high_low(self, new_high: int, new_low: int) -> Dict:
        """
        分析新高新低

        参数:
            new_high: 创新高数
            new_low: 创新低数
        """
        total = new_high + new_low
        if total == 0:
            return {"ratio": 0.5, "score": 50, "signal": "neutral"}

        high_ratio = new_high / total
        score = high_ratio * 100

        if new_high > new_low * 2:
            signal = "bullish"
            reasoning = f"创新高占优：{new_high}只新高 vs {new_low}只新低"
        elif new_low > new_high * 2:
            signal = "bearish"
            reasoning = f"创新低占优：{new_low}只新低 vs {new_high}只新高"
        else:
            signal = "neutral"
            reasoning = f"新高新低均衡：{new_high}只新高 vs {new_low}只新低"

        return {
            "ratio": high_ratio,
            "score": score,
            "signal": signal,
            "reasoning": reasoning
        }

    def analyze_northbound_sentiment(self, net_buy: float) -> Dict:
        """
        分析北向资金情绪

        参数:
            net_buy: 净买入（亿元）
        """
        # 转换为分数
        if net_buy > 100:
            score = 90
        elif net_buy > 50:
            score = 70
        elif net_buy > 20:
            score = 60
        elif net_buy > 0:
            score = 55
        elif net_buy > -20:
            score = 45
        elif net_buy > -50:
            score = 40
        elif net_buy > -100:
            score = 30
        else:
            score = 10

        if net_buy > 50:
            signal = "bullish"
            reasoning = f"北向资金大幅流入{net_buy:.1f}亿"
        elif net_buy > 0:
            signal = "bullish"
            reasoning = f"北向资金流入{net_buy:.1f}亿"
        elif net_buy < -50:
            signal = "bearish"
            reasoning = f"北向资金大幅流出{abs(net_buy):.1f}亿"
        elif net_buy < 0:
            signal = "bearish"
            reasoning = f"北向资金流出{abs(net_buy):.1f}亿"
        else:
            signal = "neutral"
            reasoning = "北向资金平衡"

        return {"score": score, "signal": signal, "reasoning": reasoning}

    def generate_comprehensive_sentiment(self, market_data: Dict) -> MarketSentiment:
        """
        生成综合市场情绪

        参数:
            market_data: 市场数据字典
        """
        # 分析各项指标
        breadth_analysis = self.analyze_market_breadth(
            market_data.get("advance", 0),
            market_data.get("decline", 0)
        )

        limit_analysis = self.analyze_limit_moves(
            market_data.get("limit_up", 0),
            market_data.get("limit_down", 0)
        )

        high_low_analysis = self.analyze_new_high_low(
            market_data.get("new_high", 0),
            market_data.get("new_low", 0)
        )

        northbound_analysis = self.analyze_northbound_sentiment(
            market_data.get("northbound_net_buy", 0)
        )

        # 计算恐慌贪婪指数
        components = {
            "market_breadth": breadth_analysis["score"],
            "limit_ratio": limit_analysis["score"],
            "northbound_flow": northbound_analysis["score"],
        }

        if "momentum_score" in market_data:
            components["momentum"] = market_data["momentum_score"]

        if "volatility_score" in market_data:
            components["volatility"] = market_data["volatility_score"]

        fear_greed_index = self.calculate_fear_greed_index(components)
        sentiment_level = self.get_sentiment_level(fear_greed_index)

        return MarketSentiment(
            date=market_data.get("date", datetime.now().strftime('%Y-%m-%d')),
            fear_greed_index=fear_greed_index,
            market_breadth=breadth_analysis["breadth"],
            advance_count=market_data.get("advance", 0),
            decline_count=market_data.get("decline", 0),
            limit_up_count=market_data.get("limit_up", 0),
            limit_down_count=market_data.get("limit_down", 0),
            new_high_count=market_data.get("new_high", 0),
            new_low_count=market_data.get("new_low", 0),
            sentiment_level=sentiment_level
        )

    def generate_sentiment_signal(self, sentiment: MarketSentiment) -> SentimentSignal:
        """生成情绪信号"""
        # 逆向指标：极度恐慌时看涨，极度贪婪时看跌
        if sentiment.fear_greed_index < 20:
            return SentimentSignal(
                signal="bullish",
                confidence=0.7,
                reasoning=f"市场极度恐慌（指数{sentiment.fear_greed_index:.0f}），逆向看涨信号"
            )
        elif sentiment.fear_greed_index < 40:
            return SentimentSignal(
                signal="bullish",
                confidence=0.6,
                reasoning=f"市场恐慌（指数{sentiment.fear_greed_index:.0f}），偏多信号"
            )
        elif sentiment.fear_greed_index > 80:
            return SentimentSignal(
                signal="bearish",
                confidence=0.7,
                reasoning=f"市场极度贪婪（指数{sentiment.fear_greed_index:.0f}），逆向看跌信号"
            )
        elif sentiment.fear_greed_index > 60:
            return SentimentSignal(
                signal="bearish",
                confidence=0.6,
                reasoning=f"市场贪婪（指数{sentiment.fear_greed_index:.0f}），偏空信号"
            )
        else:
            return SentimentSignal(
                signal="neutral",
                confidence=0.5,
                reasoning=f"市场情绪中性（指数{sentiment.fear_greed_index:.0f}）"
            )


if __name__ == "__main__":
    # 测试市场情绪分析
    analyzer = MarketSentimentAnalyzer()

    # 模拟市场数据
    market_data = {
        "date": "2024-01-15",
        "advance": 2800,
        "decline": 1800,
        "limit_up": 45,
        "limit_down": 12,
        "new_high": 80,
        "new_low": 30,
        "northbound_net_buy": 65.5,
        "momentum_score": 65,
        "volatility_score": 45,
    }

    sentiment = analyzer.generate_comprehensive_sentiment(market_data)

    print("市场情绪分析:")
    print(f"  恐慌贪婪指数: {sentiment.fear_greed_index:.1f}")
    print(f"  情绪等级: {sentiment.sentiment_level}")
    print(f"  市场宽度: {sentiment.market_breadth*100:.1f}%")
    print(f"  涨跌停: {sentiment.limit_up_count} vs {sentiment.limit_down_count}")

    signal = analyzer.generate_sentiment_signal(sentiment)
    print(f"\n情绪信号: {signal.signal}")
    print(f"置信度: {signal.confidence}")
    print(f"理由: {signal.reasoning}")