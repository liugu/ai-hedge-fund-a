"""
量化策略模块

支持多种量化策略：
1. 均线策略
2. 动量策略
3. 均值回归策略
4. 因子策略
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class StrategySignal:
    """策略信号"""
    strategy_name: str
    ticker: str
    date: str
    signal: str  # buy/sell/hold
    confidence: float  # 0-1
    reasoning: str
    price: float


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    total_return: float
    annual_return: float
    max_drawdown: float
    win_rate: float
    sharpe_ratio: float
    trades: int


class MovingAverageStrategy:
    """均线策略"""

    def __init__(self, fast_period: int = 5, slow_period: int = 20):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.name = f"MA_{fast_period}_{slow_period}"

    def generate_signal(self, prices: List[float], dates: List[str] = None) -> StrategySignal:
        """生成交易信号"""
        if len(prices) < self.slow_period:
            return None

        # 计算均线
        fast_ma = np.mean(prices[-self.fast_period:])
        slow_ma = np.mean(prices[-self.slow_period:])
        prev_fast_ma = np.mean(prices[-self.fast_period-1:-1])
        prev_slow_ma = np.mean(prices[-self.slow_period-1:-1])

        # 判断信号
        current_price = prices[-1]
        date = dates[-1] if dates else datetime.now().strftime('%Y-%m-%d')

        # 金叉/死叉
        if fast_ma > slow_ma and prev_fast_ma <= prev_slow_ma:
            signal = "buy"
            confidence = 0.7
            reasoning = f"金叉信号：MA{self.fast_period}({fast_ma:.2f})上穿MA{self.slow_period}({slow_ma:.2f})"
        elif fast_ma < slow_ma and prev_fast_ma >= prev_slow_ma:
            signal = "sell"
            confidence = 0.7
            reasoning = f"死叉信号：MA{self.fast_period}({fast_ma:.2f})下穿MA{self.slow_period}({slow_ma:.2f})"
        elif fast_ma > slow_ma:
            signal = "hold"
            confidence = 0.5
            reasoning = f"多头排列：MA{self.fast_period}({fast_ma:.2f}) > MA{self.slow_period}({slow_ma:.2f})"
        else:
            signal = "hold"
            confidence = 0.5
            reasoning = f"空头排列：MA{self.fast_period}({fast_ma:.2f}) < MA{self.slow_period}({slow_ma:.2f})"

        return StrategySignal(
            strategy_name=self.name,
            ticker="",
            date=date,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            price=current_price
        )


class MomentumStrategy:
    """动量策略"""

    def __init__(self, lookback: int = 20, threshold: float = 0.05):
        self.lookback = lookback
        self.threshold = threshold
        self.name = f"Momentum_{lookback}"

    def generate_signal(self, prices: List[float], dates: List[str] = None) -> StrategySignal:
        """生成交易信号"""
        if len(prices) < self.lookback:
            return None

        # 计算动量
        current_price = prices[-1]
        past_price = prices[-self.lookback]
        momentum = (current_price - past_price) / past_price

        date = dates[-1] if dates else datetime.now().strftime('%Y-%m-%d')

        # 判断信号
        if momentum > self.threshold:
            signal = "buy"
            confidence = min(0.9, 0.5 + abs(momentum))
            reasoning = f"上涨动量：{self.lookback}日涨幅{momentum*100:.2f}%，超过阈值{self.threshold*100}%"
        elif momentum < -self.threshold:
            signal = "sell"
            confidence = min(0.9, 0.5 + abs(momentum))
            reasoning = f"下跌动量：{self.lookback}日跌幅{abs(momentum)*100:.2f}%，超过阈值{self.threshold*100}%"
        else:
            signal = "hold"
            confidence = 0.5
            reasoning = f"动量不足：{self.lookback}日涨跌幅{momentum*100:.2f}%"

        return StrategySignal(
            strategy_name=self.name,
            ticker="",
            date=date,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            price=current_price
        )


class MeanReversionStrategy:
    """均值回归策略"""

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev
        self.name = f"MeanReversion_{period}"

    def generate_signal(self, prices: List[float], dates: List[str] = None) -> StrategySignal:
        """生成交易信号"""
        if len(prices) < self.period:
            return None

        # 计算均值和标准差
        recent_prices = prices[-self.period:]
        mean = np.mean(recent_prices)
        std = np.std(recent_prices)

        current_price = prices[-1]
        z_score = (current_price - mean) / std if std > 0 else 0

        date = dates[-1] if dates else datetime.now().strftime('%Y-%m-%d')

        # 判断信号
        if z_score < -self.std_dev:
            signal = "buy"
            confidence = min(0.9, 0.5 + abs(z_score) * 0.1)
            reasoning = f"超卖信号：价格低于均值{self.std_dev}个标准差，Z-score={z_score:.2f}"
        elif z_score > self.std_dev:
            signal = "sell"
            confidence = min(0.9, 0.5 + abs(z_score) * 0.1)
            reasoning = f"超买信号：价格高于均值{self.std_dev}个标准差，Z-score={z_score:.2f}"
        else:
            signal = "hold"
            confidence = 0.5
            reasoning = f"正常区间：Z-score={z_score:.2f}，在±{self.std_dev}范围内"

        return StrategySignal(
            strategy_name=self.name,
            ticker="",
            date=date,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            price=current_price
        )


class RSIStrategy:
    """RSI策略"""

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.name = f"RSI_{period}"

    def calculate_rsi(self, prices: List[float]) -> float:
        """计算RSI"""
        if len(prices) < self.period + 1:
            return 50

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-self.period:])
        avg_loss = np.mean(losses[-self.period:])

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def generate_signal(self, prices: List[float], dates: List[str] = None) -> StrategySignal:
        """生成交易信号"""
        if len(prices) < self.period + 1:
            return None

        rsi = self.calculate_rsi(prices)
        current_price = prices[-1]
        date = dates[-1] if dates else datetime.now().strftime('%Y-%m-%d')

        # 判断信号
        if rsi < self.oversold:
            signal = "buy"
            confidence = 0.7 + (self.oversold - rsi) * 0.01
            reasoning = f"RSI超卖：RSI={rsi:.2f}，低于{self.oversold}阈值"
        elif rsi > self.overbought:
            signal = "sell"
            confidence = 0.7 + (rsi - self.overbought) * 0.01
            reasoning = f"RSI超买：RSI={rsi:.2f}，高于{self.overbought}阈值"
        else:
            signal = "hold"
            confidence = 0.5
            reasoning = f"RSI正常：RSI={rsi:.2f}"

        return StrategySignal(
            strategy_name=self.name,
            ticker="",
            date=date,
            signal=signal,
            confidence=min(0.95, confidence),
            reasoning=reasoning,
            price=current_price
        )


class StrategyComposer:
    """策略组合器"""

    def __init__(self, strategies: List = None):
        self.strategies = strategies or [
            MovingAverageStrategy(),
            MomentumStrategy(),
            MeanReversionStrategy(),
            RSIStrategy(),
        ]

    def generate_combined_signal(self, prices: List[float], dates: List[str] = None) -> Dict:
        """生成组合信号"""
        signals = []

        for strategy in self.strategies:
            signal = strategy.generate_signal(prices, dates)
            if signal:
                signals.append(signal)

        if not signals:
            return {"signal": "hold", "confidence": 0.5, "reasoning": "数据不足"}

        # 投票机制
        buy_votes = sum(1 for s in signals if s.signal == "buy")
        sell_votes = sum(1 for s in signals if s.signal == "sell")
        hold_votes = sum(1 for s in signals if s.signal == "hold")

        total = len(signals)

        # 加权置信度
        avg_confidence = np.mean([s.confidence for s in signals])

        if buy_votes > sell_votes and buy_votes > hold_votes:
            final_signal = "buy"
            confidence = avg_confidence * (buy_votes / total)
        elif sell_votes > buy_votes and sell_votes > hold_votes:
            final_signal = "sell"
            confidence = avg_confidence * (sell_votes / total)
        else:
            final_signal = "hold"
            confidence = avg_confidence * 0.8

        # 汇总理由
        reasoning_parts = [f"{s.strategy_name}: {s.reasoning}" for s in signals]

        return {
            "signal": final_signal,
            "confidence": min(0.95, confidence),
            "reasoning": " | ".join(reasoning_parts),
            "buy_votes": buy_votes,
            "sell_votes": sell_votes,
            "hold_votes": hold_votes,
            "individual_signals": [
                {
                    "strategy": s.strategy_name,
                    "signal": s.signal,
                    "confidence": s.confidence,
                    "reasoning": s.reasoning
                }
                for s in signals
            ]
        }


if __name__ == "__main__":
    # 测试策略
    test_prices = [100, 101, 102, 101, 103, 105, 104, 106, 108, 107,
                   109, 111, 110, 112, 114, 113, 115, 117, 116, 118,
                   120, 119, 121, 123, 122, 124, 126, 125, 127, 129]

    composer = StrategyComposer()
    result = composer.generate_combined_signal(test_prices)

    print("组合策略信号:")
    print(f"  信号: {result['signal']}")
    print(f"  置信度: {result['confidence']:.2f}")
    print(f"  买入票数: {result['buy_votes']}, 卖出票数: {result['sell_votes']}, 持有票数: {result['hold_votes']}")
    print("\n各策略详情:")
    for s in result['individual_signals']:
        print(f"  {s['strategy']}: {s['signal']} ({s['confidence']:.2f})")