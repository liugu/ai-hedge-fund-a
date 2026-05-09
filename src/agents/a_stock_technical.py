"""
A股技术分析代理

专门针对A股市场的技术分析，包括：
1. K线形态识别
2. 均线系统分析
3. 成交量分析
4. 技术指标信号（MACD、KDJ、RSI等）
"""

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from typing_extensions import Literal
import json
import logging

from src.graph.state import AgentState, show_agent_reasoning
from src.utils.progress import progress

logger = logging.getLogger(__name__)


class AStockTechnicalSignal(BaseModel):
    """A股技术分析信号"""
    signal: Literal["bullish", "bearish", "neutral"]
    confidence: int = Field(description="置信度0-100")
    reasoning: str = Field(description="决策理由")


def a_stock_technical_agent(state: AgentState, agent_id: str = "a_stock_technical_agent"):
    """
    A股技术分析代理

    综合多种技术指标生成交易信号
    """
    data = state["data"]
    tickers = data["tickers"]
    technical_analysis = {}

    for ticker in tickers:
        progress.update_status(agent_id, ticker, "获取K线数据")

        # 获取K线数据
        kline_data = get_kline_data(ticker)

        if not kline_data:
            progress.update_status(agent_id, ticker, "失败：无K线数据")
            continue

        progress.update_status(agent_id, ticker, "分析均线系统")
        ma_analysis = analyze_ma_system(kline_data)

        progress.update_status(agent_id, ticker, "分析MACD指标")
        macd_analysis = analyze_macd(kline_data)

        progress.update_status(agent_id, ticker, "分析KDJ指标")
        kdj_analysis = analyze_kdj(kline_data)

        progress.update_status(agent_id, ticker, "分析RSI指标")
        rsi_analysis = analyze_rsi(kline_data)

        progress.update_status(agent_id, ticker, "分析成交量")
        volume_analysis = analyze_volume(kline_data)

        progress.update_status(agent_id, ticker, "识别K线形态")
        pattern_analysis = analyze_patterns(kline_data)

        # 综合评分
        total_score = (
            ma_analysis["score"] * 0.20 +
            macd_analysis["score"] * 0.20 +
            kdj_analysis["score"] * 0.15 +
            rsi_analysis["score"] * 0.15 +
            volume_analysis["score"] * 0.15 +
            pattern_analysis["score"] * 0.15
        )

        # 生成信号
        if total_score >= 7:
            signal = "bullish"
        elif total_score <= 4:
            signal = "bearish"
        else:
            signal = "neutral"

        confidence = min(100, max(0, int(total_score * 10)))

        technical_analysis[ticker] = {
            "signal": signal,
            "confidence": confidence,
            "reasoning": {
                "ma": ma_analysis,
                "macd": macd_analysis,
                "kdj": kdj_analysis,
                "rsi": rsi_analysis,
                "volume": volume_analysis,
                "pattern": pattern_analysis,
                "total_score": total_score,
            }
        }

        progress.update_status(agent_id, ticker, "完成", analysis=json.dumps(technical_analysis[ticker], ensure_ascii=False))

    # 创建消息
    message = HumanMessage(content=json.dumps(technical_analysis), name=agent_id)

    if state["metadata"].get("show_reasoning"):
        show_agent_reasoning(technical_analysis, "A股技术分析代理")

    state["data"]["analyst_signals"][agent_id] = technical_analysis

    progress.update_status(agent_id, None, "完成")

    return {"messages": [message], "data": state["data"]}


def get_kline_data(ticker: str) -> dict:
    """获取K线数据"""
    try:
        from src.utils.eastmoney_api import EastMoneyAPI

        klines = EastMoneyAPI.get_kline_data(ticker, period='day', count=60)

        if not klines:
            return None

        return {
            "klines": [
                {
                    "date": k.date,
                    "open": k.open,
                    "close": k.close,
                    "high": k.high,
                    "low": k.low,
                    "volume": k.volume,
                    "change_pct": k.change_pct,
                }
                for k in klines
            ]
        }

    except Exception as e:
        logger.error(f"获取K线数据失败: {ticker} - {e}")
        return None


def analyze_ma_system(kline_data: dict) -> dict:
    """分析均线系统"""
    klines = kline_data.get("klines", [])
    if len(klines) < 20:
        return {"score": 5, "details": "均线数据不足"}

    closes = [k["close"] for k in klines]

    # 计算均线
    ma5 = sum(closes[-5:]) / 5
    ma10 = sum(closes[-10:]) / 10
    ma20 = sum(closes[-20:]) / 20
    current_price = closes[-1]

    # 判断均线排列
    if ma5 > ma10 > ma20:
        if current_price > ma5:
            score = 9
            details = "多头排列，股价站上所有均线"
        else:
            score = 7
            details = "多头排列，但股价低于MA5"
    elif ma5 < ma10 < ma20:
        if current_price < ma5:
            score = 2
            details = "空头排列，股价跌破所有均线"
        else:
            score = 4
            details = "空头排列，但股价高于MA5"
    else:
        score = 5
        details = "均线纠缠，方向不明"

    return {"score": score, "details": details, "ma5": ma5, "ma10": ma10, "ma20": ma20}


def analyze_macd(kline_data: dict) -> dict:
    """分析MACD指标"""
    klines = kline_data.get("klines", [])
    if len(klines) < 35:
        return {"score": 5, "details": "MACD数据不足"}

    closes = [k["close"] for k in klines]

    try:
        from src.utils.technical_indicators import TechnicalAnalyzer
        analyzer = TechnicalAnalyzer(closes)
        macd, signal, hist = analyzer.calculate_macd()

        if macd is None:
            return {"score": 5, "details": "MACD计算失败"}

        if macd > signal and hist and hist > 0:
            score = 8
            details = f"MACD金叉，柱状图为正 ({hist:.4f})"
        elif macd > signal:
            score = 6
            details = "MACD在信号线上方"
        elif macd < signal and hist and hist < 0:
            score = 3
            details = f"MACD死叉，柱状图为负 ({hist:.4f})"
        else:
            score = 5
            details = "MACD在信号线下方"

        return {"score": score, "details": details, "macd": macd, "signal": signal, "hist": hist}

    except Exception as e:
        return {"score": 5, "details": f"MACD分析失败: {e}"}


def analyze_kdj(kline_data: dict) -> dict:
    """分析KDJ指标"""
    klines = kline_data.get("klines", [])
    if len(klines) < 15:
        return {"score": 5, "details": "KDJ数据不足"}

    closes = [k["close"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]

    try:
        from src.utils.technical_indicators import TechnicalAnalyzer
        analyzer = TechnicalAnalyzer(closes, highs, lows)
        k, d, j = analyzer.calculate_kdj()

        if k is None:
            return {"score": 5, "details": "KDJ计算失败"}

        # 超买超卖判断
        if j < 20:
            score = 8
            details = f"KDJ超卖区域，J值={j:.2f}，可能反弹"
        elif j > 80:
            score = 3
            details = f"KDJ超买区域，J值={j:.2f}，可能回调"
        elif k > d:
            score = 6
            details = f"KDJ金叉，K={k:.2f}>D={d:.2f}"
        elif k < d:
            score = 4
            details = f"KDJ死叉，K={k:.2f}<D={d:.2f}"
        else:
            score = 5
            details = f"KDJ中性，K={k:.2f}，D={d:.2f}，J={j:.2f}"

        return {"score": score, "details": details, "k": k, "d": d, "j": j}

    except Exception as e:
        return {"score": 5, "details": f"KDJ分析失败: {e}"}


def analyze_rsi(kline_data: dict) -> dict:
    """分析RSI指标"""
    klines = kline_data.get("klines", [])
    if len(klines) < 20:
        return {"score": 5, "details": "RSI数据不足"}

    closes = [k["close"] for k in klines]

    try:
        from src.utils.technical_indicators import TechnicalAnalyzer
        analyzer = TechnicalAnalyzer(closes)
        rsi = analyzer.calculate_rsi(14)

        if rsi is None:
            return {"score": 5, "details": "RSI计算失败"}

        if rsi < 30:
            score = 8
            details = f"RSI超卖区域 ({rsi:.2f})，可能反弹"
        elif rsi > 70:
            score = 3
            details = f"RSI超买区域 ({rsi:.2f})，可能回调"
        elif rsi > 50:
            score = 6
            details = f"RSI偏强 ({rsi:.2f})"
        else:
            score = 4
            details = f"RSI偏弱 ({rsi:.2f})"

        return {"score": score, "details": details, "rsi": rsi}

    except Exception as e:
        return {"score": 5, "details": f"RSI分析失败: {e}"}


def analyze_volume(kline_data: dict) -> dict:
    """分析成交量"""
    klines = kline_data.get("klines", [])
    if len(klines) < 5:
        return {"score": 5, "details": "成交量数据不足"}

    volumes = [k["volume"] for k in klines]
    changes = [k["change_pct"] for k in klines]

    # 计算平均成交量
    avg_volume = sum(volumes[-5:]) / 5
    current_volume = volumes[-1]
    current_change = changes[-1]

    # 量比
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

    # 量价关系
    if current_change > 0 and volume_ratio > 1.5:
        score = 8
        details = f"放量上涨，量比{volume_ratio:.2f}"
    elif current_change > 0 and volume_ratio < 0.8:
        score = 5
        details = f"缩量上涨，量比{volume_ratio:.2f}"
    elif current_change < 0 and volume_ratio > 1.5:
        score = 3
        details = f"放量下跌，量比{volume_ratio:.2f}"
    elif current_change < 0 and volume_ratio < 0.8:
        score = 6
        details = f"缩量下跌，量比{volume_ratio:.2f}"
    else:
        score = 5
        details = f"量价正常，量比{volume_ratio:.2f}"

    return {"score": score, "details": details, "volume_ratio": volume_ratio}


def analyze_patterns(kline_data: dict) -> dict:
    """分析K线形态"""
    klines = kline_data.get("klines", [])
    if len(klines) < 5:
        return {"score": 5, "details": "K线形态数据不足"}

    patterns = []
    score = 5

    # 获取最近几根K线
    k1 = klines[-1]  # 最新
    k2 = klines[-2] if len(klines) > 1 else None  # 前一根
    k3 = klines[-3] if len(klines) > 2 else None  # 前两根

    # 阳线/阴线
    if k1["close"] > k1["open"]:
        body1 = k1["close"] - k1["open"]
        upper1 = k1["high"] - k1["close"]
        lower1 = k1["open"] - k1["low"]

        # 大阳线
        if body1 > (k1["high"] - k1["low"]) * 0.6:
            patterns.append("大阳线")
            score += 1

        # 光头阳线
        if upper1 < body1 * 0.1:
            patterns.append("光头阳线")
            score += 0.5

    else:
        body1 = k1["open"] - k1["close"]
        # 大阴线
        if body1 > (k1["high"] - k1["low"]) * 0.6:
            patterns.append("大阴线")
            score -= 1

    # 十字星
    if abs(k1["close"] - k1["open"]) < (k1["high"] - k1["low"]) * 0.1:
        patterns.append("十字星")
        # 需要结合前一根K线判断

    # 锤子线/上吊线
    if k1["open"] != k1["close"]:
        body = abs(k1["close"] - k1["open"])
        lower = min(k1["open"], k1["close"]) - k1["low"]
        upper = k1["high"] - max(k1["open"], k1["close"])

        if lower > body * 2 and upper < body * 0.5:
            if k1["close"] > k1["open"]:
                patterns.append("锤子线（看涨）")
                score += 1
            else:
                patterns.append("上吊线（看跌）")
                score -= 0.5

    # 吞没形态
    if k2:
        # 看涨吞没
        if (k2["close"] < k2["open"] and  # 前一根是阴线
            k1["close"] > k1["open"] and  # 当前是阳线
            k1["close"] > k2["open"] and  # 当前收盘高于前一根开盘
            k1["open"] < k2["close"]):    # 当前开盘低于前一根收盘
            patterns.append("看涨吞没")
            score += 1.5

        # 看跌吞没
        if (k2["close"] > k2["open"] and  # 前一根是阳线
            k1["close"] < k1["open"] and  # 当前是阴线
            k1["close"] < k2["open"] and  # 当前收盘低于前一根开盘
            k1["open"] > k2["close"]):    # 当前开盘高于前一根收盘
            patterns.append("看跌吞没")
            score -= 1.5

    details = "，".join(patterns) if patterns else "无明显形态"

    return {"score": min(10, max(0, score)), "details": details, "patterns": patterns}


# 注册到分析师配置
ANALYST_CONFIG = {
    "a_stock_technical": {
        "display_name": "A股技术分析师",
        "description": "技术分析专家",
        "investing_style": "运用K线形态、均线系统、MACD、KDJ、RSI等技术指标，结合成交量分析，识别A股市场的买卖时机。注重趋势跟踪和形态识别。",
        "agent_func": a_stock_technical_agent,
        "type": "analyst",
        "order": 20,
    }
}


__all__ = [
    "a_stock_technical_agent",
    "AStockTechnicalSignal",
    "ANALYST_CONFIG",
]
