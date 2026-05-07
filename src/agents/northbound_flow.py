"""
北向资金分析代理

分析北向资金（外资）流入流出情况，包括：
1. 北向资金净流入趋势
2. 个股北向资金持仓变化
3. 行业资金流向
4. 资金流向与股价相关性

北向资金是A股市场重要的风向标，对股价有显著影响。
"""

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing_extensions import Literal
import json
import logging

from src.graph.state import AgentState, show_agent_reasoning
from src.utils.progress import progress
from src.utils.llm import call_llm

logger = logging.getLogger(__name__)


class NorthboundFlowSignal(BaseModel):
    """北向资金信号模型"""
    signal: Literal["bullish", "bearish", "neutral"]
    confidence: int = Field(description="置信度0-100")
    reasoning: str = Field(description="决策理由")


def northbound_flow_agent(state: AgentState, agent_id: str = "northbound_flow_agent"):
    """
    北向资金分析代理

    分析北向资金流向，生成交易信号：
    - 持续净流入：看涨信号
    - 持续净流出：看跌信号
    - 波动较大：中性信号
    """
    data = state["data"]
    tickers = data["tickers"]
    northbound_analysis = {}

    for ticker in tickers:
        progress.update_status(agent_id, ticker, "获取北向资金数据")

        # 获取北向资金数据
        flow_data = get_northbound_flow_data(ticker)

        if not flow_data:
            progress.update_status(agent_id, ticker, "失败：无北向资金数据")
            continue

        progress.update_status(agent_id, ticker, "分析资金流向趋势")
        trend_analysis = analyze_flow_trend(flow_data)

        progress.update_status(agent_id, ticker, "分析资金强度")
        strength_analysis = analyze_flow_strength(flow_data)

        progress.update_status(agent_id, ticker, "分析资金持续性")
        persistence_analysis = analyze_flow_persistence(flow_data)

        # 组合分析结果
        total_score = (
            trend_analysis["score"] * 0.40 +
            strength_analysis["score"] * 0.35 +
            persistence_analysis["score"] * 0.25
        )

        # 生成信号
        if total_score >= 7:
            signal = "bullish"
        elif total_score <= 4:
            signal = "bearish"
        else:
            signal = "neutral"

        confidence = min(100, max(0, int(total_score * 10)))

        northbound_analysis[ticker] = {
            "signal": signal,
            "confidence": confidence,
            "reasoning": {
                "trend": trend_analysis,
                "strength": strength_analysis,
                "persistence": persistence_analysis,
                "total_score": total_score,
            }
        }

        progress.update_status(agent_id, ticker, "完成", analysis=json.dumps(northbound_analysis[ticker], ensure_ascii=False))

    # 创建消息
    message = HumanMessage(content=json.dumps(northbound_analysis), name=agent_id)

    if state["metadata"].get("show_reasoning"):
        show_agent_reasoning(northbound_analysis, "北向资金分析代理")

    state["data"]["analyst_signals"][agent_id] = northbound_analysis

    progress.update_status(agent_id, None, "完成")

    return {"messages": [message], "data": state["data"]}


def get_northbound_flow_data(ticker: str) -> dict:
    """
    获取北向资金数据

    返回：
        {
            "recent_flows": [...],  # 最近N天的资金流向
            "net_buy_5d": float,    # 5日净买入
            "net_buy_20d": float,   # 20日净买入
            "net_buy_60d": float,   # 60日净买入
            "total_balance": float, # 累计净买入
        }
    """
    try:
        from src.tools.api import get_northbound_flow

        # 获取最近60天的北向资金数据
        flows = get_northbound_flow(days=60)

        if not flows:
            return None

        # 计算各期净买入
        net_buy_5d = sum(f.get("net_buy", 0) for f in flows[:5]) if len(flows) >= 5 else None
        net_buy_20d = sum(f.get("net_buy", 0) for f in flows[:20]) if len(flows) >= 20 else None
        net_buy_60d = sum(f.get("net_buy", 0) for f in flows[:60]) if len(flows) >= 60 else None

        return {
            "recent_flows": flows[:20],  # 最近20天
            "net_buy_5d": net_buy_5d,
            "net_buy_20d": net_buy_20d,
            "net_buy_60d": net_buy_60d,
            "total_balance": flows[0].get("total_balance") if flows else None,
        }

    except Exception as e:
        logger.error(f"获取北向资金数据失败: {ticker} - {e}")
        return None


def analyze_flow_trend(flow_data: dict) -> dict:
    """
    分析资金流向趋势

    判断：
    - 持续流入
    - 持续流出
    - 波动震荡
    """
    flows = flow_data.get("recent_flows", [])
    if not flows:
        return {"score": 5, "details": "无资金流向数据"}

    # 计算流入/流出天数
    inflow_days = sum(1 for f in flows if f.get("net_buy", 0) > 0)
    outflow_days = len(flows) - inflow_days

    # 计算趋势得分
    if inflow_days >= len(flows) * 0.7:
        score = 9
        details = f"持续流入：{inflow_days}/{len(flows)}天净买入"
    elif inflow_days >= len(flows) * 0.55:
        score = 7
        details = f"偏多流入：{inflow_days}/{len(flows)}天净买入"
    elif outflow_days >= len(flows) * 0.7:
        score = 2
        details = f"持续流出：{outflow_days}/{len(flows)}天净卖出"
    elif outflow_days >= len(flows) * 0.55:
        score = 4
        details = f"偏多流出：{outflow_days}/{len(flows)}天净卖出"
    else:
        score = 5
        details = f"震荡格局：{inflow_days}天流入，{outflow_days}天流出"

    return {"score": score, "details": details}


def analyze_flow_strength(flow_data: dict) -> dict:
    """
    分析资金流向强度

    判断：
    - 大额流入
    - 大额流出
    - 小幅波动
    """
    net_buy_5d = flow_data.get("net_buy_5d")
    net_buy_20d = flow_data.get("net_buy_20d")

    if net_buy_5d is None or net_buy_20d is None:
        return {"score": 5, "details": "资金强度数据不足"}

    # 计算日均流入
    avg_5d = net_buy_5d / 5
    avg_20d = net_buy_20d / 20

    # 判断强度（单位：亿元）
    if avg_5d > 50:  # 日均流入超过50亿
        score = 10
        details = f"极强流入：5日均流入{avg_5d:.1f}亿"
    elif avg_5d > 20:
        score = 8
        details = f"强劲流入：5日均流入{avg_5d:.1f}亿"
    elif avg_5d > 5:
        score = 7
        details = f"中等流入：5日均流入{avg_5d:.1f}亿"
    elif avg_5d > 0:
        score = 6
        details = f"小幅流入：5日均流入{avg_5d:.1f}亿"
    elif avg_5d > -5:
        score = 5
        details = f"小幅流出：5日均流出{-avg_5d:.1f}亿"
    elif avg_5d > -20:
        score = 4
        details = f"中等流出：5日均流出{-avg_5d:.1f}亿"
    elif avg_5d > -50:
        score = 2
        details = f"强劲流出：5日均流出{-avg_5d:.1f}亿"
    else:
        score = 1
        details = f"极强流出：5日均流出{-avg_5d:.1f}亿"

    return {"score": score, "details": details}


def analyze_flow_persistence(flow_data: dict) -> dict:
    """
    分析资金流向持续性

    判断资金是否持续流入或流出
    """
    flows = flow_data.get("recent_flows", [])
    if not flows or len(flows) < 5:
        return {"score": 5, "details": "资金持续性数据不足"}

    # 计算连续流入/流出天数
    max_consecutive_inflow = 0
    max_consecutive_outflow = 0
    current_inflow = 0
    current_outflow = 0

    for f in flows:
        if f.get("net_buy", 0) > 0:
            current_inflow += 1
            current_outflow = 0
            max_consecutive_inflow = max(max_consecutive_inflow, current_inflow)
        else:
            current_outflow += 1
            current_inflow = 0
            max_consecutive_outflow = max(max_consecutive_outflow, current_outflow)

    # 判断持续性
    if max_consecutive_inflow >= 10:
        score = 9
        details = f"持续流入{max_consecutive_inflow}天"
    elif max_consecutive_inflow >= 5:
        score = 7
        details = f"连续流入{max_consecutive_inflow}天"
    elif max_consecutive_outflow >= 10:
        score = 2
        details = f"持续流出{max_consecutive_outflow}天"
    elif max_consecutive_outflow >= 5:
        score = 4
        details = f"连续流出{max_consecutive_outflow}天"
    else:
        score = 5
        details = f"最大连续流入{max_consecutive_inflow}天，流出{max_consecutive_outflow}天"

    return {"score": score, "details": details}


# 注册到分析师配置
ANALYST_CONFIG = {
    "northbound_flow": {
        "display_name": "北向资金分析师",
        "description": "外资流向专家",
        "investing_style": "跟踪北向资金流向，分析外资对A股的态度和配置变化。北向资金被视为'聪明钱'，其流向对市场有重要参考价值。",
        "agent_func": northbound_flow_agent,
        "type": "analyst",
        "order": 19,
    }
}


__all__ = [
    "northbound_flow_agent",
    "NorthboundFlowSignal",
    "ANALYST_CONFIG",
]