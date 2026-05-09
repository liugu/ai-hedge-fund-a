"""
技术指标计算模块
支持MACD、KDJ、RSI、BOLL、MA等常用技术指标
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TechnicalIndicators:
    """技术指标结果"""
    # MACD
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None

    # KDJ
    kdj_k: Optional[float] = None
    kdj_d: Optional[float] = None
    kdj_j: Optional[float] = None

    # RSI
    rsi_6: Optional[float] = None
    rsi_12: Optional[float] = None
    rsi_24: Optional[float] = None

    # BOLL
    boll_upper: Optional[float] = None
    boll_middle: Optional[float] = None
    boll_lower: Optional[float] = None
    boll_width: Optional[float] = None  # 带宽

    # MA
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None

    # 趋势信号
    trend: str = "neutral"  # bullish/bearish/neutral
    signal_strength: int = 0  # 0-100


class TechnicalAnalyzer:
    """技术分析器"""

    def __init__(self, prices: List[float], highs: List[float] = None,
                 lows: List[float] = None, volumes: List[int] = None):
        """
        初始化技术分析器

        参数:
            prices: 收盘价列表
            highs: 最高价列表（可选，用于KDJ等）
            lows: 最低价列表（可选，用于KDJ等）
            volumes: 成交量列表（可选，用于量价分析）
        """
        self.prices = np.array(prices, dtype=float)
        self.highs = np.array(highs, dtype=float) if highs else self.prices
        self.lows = np.array(lows, dtype=float) if lows else self.prices
        self.volumes = np.array(volumes, dtype=float) if volumes else None

    def calculate_ma(self, period: int) -> Optional[float]:
        """计算移动平均线"""
        if len(self.prices) < period:
            return None
        return float(np.mean(self.prices[-period:]))

    def calculate_ema(self, period: int) -> Optional[float]:
        """计算指数移动平均线"""
        if len(self.prices) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = self.prices[0]

        for price in self.prices[1:]:
            ema = (price - ema) * multiplier + ema

        return float(ema)

    def calculate_macd(self, fast_period: int = 12, slow_period: int = 26,
                       signal_period: int = 9) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        计算MACD指标

        返回:
            (MACD线, 信号线, 柱状图)
        """
        if len(self.prices) < slow_period + signal_period:
            return None, None, None

        # 计算快慢EMA
        ema_fast = self._calculate_ema_series(fast_period)
        ema_slow = self._calculate_ema_series(slow_period)

        # MACD线 = 快线EMA - 慢线EMA
        macd_line = ema_fast - ema_slow

        # 信号线 = MACD线的EMA
        signal_line = self._calculate_ema_from_series(macd_line, signal_period)

        # 柱状图 = MACD线 - 信号线
        histogram = macd_line - signal_line

        return float(macd_line[-1]), float(signal_line[-1]), float(histogram[-1])

    def calculate_kdj(self, n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        计算KDJ指标

        返回:
            (K值, D值, J值)
        """
        if len(self.prices) < n:
            return None, None, None

        # 计算RSV
        high_n = np.max(self.highs[-n:])
        low_n = np.min(self.lows[-n:])

        if high_n == low_n:
            rsv = 50
        else:
            rsv = (self.prices[-1] - low_n) / (high_n - low_n) * 100

        # 计算K、D、J（需要历史数据，这里简化处理）
        # 使用前一天的K、D值（如果有）
        k = rsv  # 简化：第一天的K值等于RSV
        d = k    # 简化：第一天的D值等于K值

        # 更精确的计算需要历史K、D值
        # 这里使用滑动窗口计算
        if len(self.prices) >= n + m1:
            rsv_list = []
            for i in range(n, len(self.prices)):
                high_n = np.max(self.highs[i-n:i])
                low_n = np.min(self.lows[i-n:i])
                if high_n == low_n:
                    rsv_list.append(50)
                else:
                    rsv_list.append((self.prices[i] - low_n) / (high_n - low_n) * 100)

            # 计算K值
            k_list = [rsv_list[0]]
            for rsv in rsv_list[1:]:
                k_list.append((2/3) * k_list[-1] + (1/3) * rsv)

            # 计算D值
            d_list = [k_list[0]]
            for k in k_list[1:]:
                d_list.append((2/3) * d_list[-1] + (1/3) * k)

            k = k_list[-1]
            d = d_list[-1]

        j = 3 * k - 2 * d

        return float(k), float(d), float(j)

    def calculate_rsi(self, period: int = 14) -> Optional[float]:
        """
        计算RSI指标

        参数:
            period: 计算周期
        """
        if len(self.prices) < period + 1:
            return None

        # 计算价格变化
        deltas = np.diff(self.prices)

        # 分离上涨和下跌
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # 计算平均上涨和下跌
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi)

    def calculate_boll(self, period: int = 20, std_dev: float = 2.0) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        计算布林带指标

        返回:
            (上轨, 中轨, 下轨, 带宽)
        """
        if len(self.prices) < period:
            return None, None, None, None

        # 中轨 = N日移动平均
        middle = np.mean(self.prices[-period:])

        # 标准差
        std = np.std(self.prices[-period:])

        # 上轨 = 中轨 + K倍标准差
        upper = middle + std_dev * std

        # 下轨 = 中轨 - K倍标准差
        lower = middle - std_dev * std

        # 带宽 = (上轨 - 下轨) / 中轨
        width = (upper - lower) / middle if middle > 0 else 0

        return float(upper), float(middle), float(lower), float(width)

    def calculate_all(self) -> TechnicalIndicators:
        """计算所有技术指标"""
        indicators = TechnicalIndicators()

        # MACD
        macd, signal, hist = self.calculate_macd()
        indicators.macd = macd
        indicators.macd_signal = signal
        indicators.macd_hist = hist

        # KDJ
        k, d, j = self.calculate_kdj()
        indicators.kdj_k = k
        indicators.kdj_d = d
        indicators.kdj_j = j

        # RSI
        indicators.rsi_6 = self.calculate_rsi(6)
        indicators.rsi_12 = self.calculate_rsi(12)
        indicators.rsi_24 = self.calculate_rsi(24)

        # BOLL
        upper, middle, lower, width = self.calculate_boll()
        indicators.boll_upper = upper
        indicators.boll_middle = middle
        indicators.boll_lower = lower
        indicators.boll_width = width

        # MA
        indicators.ma5 = self.calculate_ma(5)
        indicators.ma10 = self.calculate_ma(10)
        indicators.ma20 = self.calculate_ma(20)
        indicators.ma60 = self.calculate_ma(60)

        # 分析趋势信号
        self._analyze_trend(indicators)

        return indicators

    def _analyze_trend(self, indicators: TechnicalIndicators):
        """分析趋势信号"""
        bullish_signals = 0
        bearish_signals = 0

        # MACD信号
        if indicators.macd and indicators.macd_signal:
            if indicators.macd > indicators.macd_signal:
                bullish_signals += 1
                if indicators.macd_hist and indicators.macd_hist > 0:
                    bullish_signals += 1
            else:
                bearish_signals += 1
                if indicators.macd_hist and indicators.macd_hist < 0:
                    bearish_signals += 1

        # KDJ信号
        if indicators.kdj_k and indicators.kdj_d:
            if indicators.kdj_k > indicators.kdj_d:
                bullish_signals += 1
            else:
                bearish_signals += 1

            # 超买超卖
            if indicators.kdj_j:
                if indicators.kdj_j < 20:
                    bullish_signals += 1  # 超卖，可能反弹
                elif indicators.kdj_j > 80:
                    bearish_signals += 1  # 超买，可能回调

        # RSI信号
        if indicators.rsi_12:
            if indicators.rsi_12 < 30:
                bullish_signals += 1  # 超卖
            elif indicators.rsi_12 > 70:
                bearish_signals += 1  # 超买

        # BOLL信号
        current_price = self.prices[-1] if len(self.prices) > 0 else 0
        if indicators.boll_upper and indicators.boll_lower:
            if current_price < indicators.boll_lower:
                bullish_signals += 1  # 跌破下轨，可能反弹
            elif current_price > indicators.boll_upper:
                bearish_signals += 1  # 突破上轨，可能回调

        # MA信号
        if indicators.ma5 and indicators.ma10 and indicators.ma20:
            if indicators.ma5 > indicators.ma10 > indicators.ma20:
                bullish_signals += 2  # 多头排列
            elif indicators.ma5 < indicators.ma10 < indicators.ma20:
                bearish_signals += 2  # 空头排列

        # 判断趋势
        total_signals = bullish_signals + bearish_signals
        if total_signals > 0:
            if bullish_signals > bearish_signals:
                indicators.trend = "bullish"
                indicators.signal_strength = int(bullish_signals / total_signals * 100)
            elif bearish_signals > bullish_signals:
                indicators.trend = "bearish"
                indicators.signal_strength = int(bearish_signals / total_signals * 100)
            else:
                indicators.trend = "neutral"
                indicators.signal_strength = 50
        else:
            indicators.trend = "neutral"
            indicators.signal_strength = 50

    def _calculate_ema_series(self, period: int) -> np.ndarray:
        """计算EMA序列"""
        multiplier = 2 / (period + 1)
        ema = np.zeros(len(self.prices))
        ema[0] = self.prices[0]

        for i in range(1, len(self.prices)):
            ema[i] = (self.prices[i] - ema[i-1]) * multiplier + ema[i-1]

        return ema

    def _calculate_ema_from_series(self, series: np.ndarray, period: int) -> np.ndarray:
        """从序列计算EMA"""
        multiplier = 2 / (period + 1)
        ema = np.zeros(len(series))
        ema[0] = series[0]

        for i in range(1, len(series)):
            ema[i] = (series[i] - ema[i-1]) * multiplier + ema[i-1]

        return ema


def analyze_technical(prices: List[float], highs: List[float] = None,
                      lows: List[float] = None, volumes: List[int] = None) -> TechnicalIndicators:
    """
    分析技术指标的便捷函数

    参数:
        prices: 收盘价列表
        highs: 最高价列表
        lows: 最低价列表
        volumes: 成交量列表

    返回:
        TechnicalIndicators对象
    """
    analyzer = TechnicalAnalyzer(prices, highs, lows, volumes)
    return analyzer.calculate_all()


if __name__ == "__main__":
    # 测试数据
    test_prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                   111, 110, 112, 114, 113, 115, 117, 116, 118, 120]

    indicators = analyze_technical(test_prices)

    print("技术指标分析结果:")
    print(f"  MACD: {indicators.macd:.4f}" if indicators.macd else "  MACD: N/A")
    print(f"  信号线: {indicators.macd_signal:.4f}" if indicators.macd_signal else "  信号线: N/A")
    print(f"  KDJ: K={indicators.kdj_k:.2f}, D={indicators.kdj_d:.2f}, J={indicators.kdj_j:.2f}" if indicators.kdj_k else "  KDJ: N/A")
    print(f"  RSI(12): {indicators.rsi_12:.2f}" if indicators.rsi_12 else "  RSI: N/A")
    print(f"  BOLL: 上={indicators.boll_upper:.2f}, 中={indicators.boll_middle:.2f}, 下={indicators.boll_lower:.2f}" if indicators.boll_upper else "  BOLL: N/A")
    print(f"  MA: MA5={indicators.ma5:.2f}, MA10={indicators.ma10:.2f}, MA20={indicators.ma20:.2f}" if indicators.ma5 else "  MA: N/A")
    print(f"  趋势: {indicators.trend}, 强度: {indicators.signal_strength}%")
