"""
A股资金流向分析代理

分析A股市场各类资金流向，包括：
1. 主力资金（大单、超大单）
2. 散户资金（小单、中单）
3. 北向资金
4. 机构资金

资金流向是A股市场重要的先行指标
"""

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from typing_extensions import Literal
import json
import logging

from src.graph.state import AgentState, show_agent_reasoning
from src.utils.progress import progress

logger = logging.getLogger(__name__)


class AStockFundFlowSignal(BaseModel):
    """A股资金流向信号"""
    signal: Literal["bullish", "bearish", "neutral"]
    confidence: int = Field(description="置信度0-100")
    reasoning: str = Field(description="决策理由")


def a_stock_fund_flow_agent(state: AgentState, agent_id: str = "a_stock_fund_flow_agent"):
    """
    A股资金流向分析代理

    分析主力资金、散户资金、北向资金流向
    """
    data = state["data"]
    tickers = data["tickers"]
    fund_flow_analysis = {}

    for ticker in tickers:
        progress.update_status(agent_id, ticker, "获取资金流向数据")

        # 获取资金流向数据
        flow_data = get_fund_flow_data(ticker)

        if not flow_data:
            progress.update_status(agent_id, ticker, "失败：无资金流向数据")
            continue

        progress.update_status(agent_id, ticker, "分析主力资金")
        main_fund_analysis = analyze_main_fund(flow_data)

        progress.update_status(agent_id, ticker, "分析散户资金")
        retail_analysis = analyze_retail_fund(flow_data)

        progress.update_status(agent_id, ticker, "分析资金分歧")
        divergence_analysis = analyze_fund_divergence(flow_data)

        progress.update_status(agent_id, ticker, "分析资金趋势")
        trend_analysis = analyze_fund_trend(flow_data)

        # 综合评分
        total_score = (
            main_fund_analysis["score"] * 0.40 +
            retail_analysis["score"] * 0.20 +
            divergence_analysis["score"] * 0.20 +
            trend_analysis["score"] * 0.20
        )

        # 生成信号
        if total_score >= 7:
            signal = "bullish"
        elif total_score <= 4:
            signal = "bearish"
        else:
            signal = "neutral"

        confidence = min(100, max(0, int(total_score * 10)))

        fund_flow_analysis[ticker] = {
            "signal": signal,
            "confidence": confidence,
            "reasoning": {
                "main_fund": main_fund_analysis,
                "retail": retail_analysis,
                "divergence": divergence_analysis,
                "trend": trend_analysis,
                "total_score": total_score,
            }
        }

        progress.update_status(agent_id, ticker, "完成", analysis=json.dumps(fund_flow_analysis[ticker], ensure_ascii=False))

    # 创建消息
    message = HumanMessage(content=json.dumps(fund_flow_analysis), name=agent_id)

    if state["metadata"].get("show_reasoning"):
        show_agent_reasoning(fund_flow_analysis, "A股资金流向分析代理")

    state["data"]["analyst_signals"][agent_id] = fund_flow_analysis

    progress.update_status(agent_id, None, "完成")

    return {"messages": [message], "data": state["data"]}


def get_fund_flow_data(ticker: str) -> dict:
    """获取资金流向数据"""
    try:
        from src.utils.eastmoney_api import EastMoneyAPI

        flow = EastMoneyAPI.get_fund_flow(ticker)

        if not flow:
            return None

        return {
            "main_net_inflow": flow.main_net_inflow,  # 主力净流入（万）
            "super_net_inflow": flow.super_net_inflow,  # 超大单净流入
            "big_net_inflow": flow.big_net_inflow,  # 大单净流入
            "medium_net_inflow": flow.medium_net_inflow,  # 中单净流入
            "small_net_inflow": flow.small_net_inflow,  # 小单净流入
            "retail_net_inflow": flow.small_net_inflow + flow.medium_net_inflow,  # 散户净流入
            "name": flow.name,
        }

    except Exception as e:
        logger.error(f"获取资金流向数据失败: {ticker} - {e}")
        return None


def analyze_main_fund(flow_data: dict) -> dict:
    """分析主力资金"""
    main_inflow = flow_data.get("main_net_inflow", 0)
    super_inflow = flow_data.get("super_net_inflow", 0)
    big_inflow = flow_data.get("big_net_inflow", 0)

    # 主力资金判断（单位：万）
    if main_inflow > 10000:  # 主力净流入超过1亿
        score = 9
        details = f"主力大幅流入：{main_inflow/10000:.2f}亿"
    elif main_inflow > 5000:
        score = 7
        details = f"主力中等流入：{main_inflow/10000:.2f}亿"
    elif main_inflow > 1000:
        score = 6
        details = f"主力小幅流入：{main_inflow:.0f}万"
    elif main_inflow > 0:
        score = 5
        details = f"主力微幅流入：{main_inflow:.0f}万"
    elif main_inflow > -1000:
        score = 5
        details = f"主力微幅流出：{-main_inflow:.0f}万"
    elif main_inflow > -5000:
        score = 4
        details = f"主力小幅流出：{-main_inflow:.0f}万"
    elif main_inflow > -10000:
        score = 3
        details = f"主力中等流出：{-main_inflow/10000:.2f}亿"
    else:
        score = 2
        details = f"主力大幅流出：{-main_inflow/10000:.2f}亿"

    # 超大单分析
    if super_inflow > 5000:
        details += f"，超大单流入{super_inflow/10000:.2f}亿"
    elif super_inflow < -5000:
        details += f"，超大单流出{-super_inflow/10000:.2f}亿"

    return {"score": score, "details": details, "main_inflow": main_inflow}


def analyze_retail_fund(flow_data: dict) -> dict:
    """分析散户资金"""
    retail_inflow = flow_data.get("retail_net_inflow", 0)
    small_inflow = flow_data.get("small_net_inflow", 0)

    # 散户资金判断
    if retail_inflow > 5000:
        score = 3  # 散户大量流入通常是反向指标
        details = f"散户大幅流入：{retail_inflow:.0f}万（反向信号）"
    elif retail_inflow > 1000:
        score = 4
        details = f"散户中等流入：{retail_inflow:.0f}万"
    elif retail_inflow > 0:
        score = 5
        details = f"散户小幅流入：{retail_inflow:.0f}万"
    elif retail_inflow > -1000:
        score = 5
        details = f"散户小幅流出：{-retail_inflow:.0f}万"
    elif retail_inflow > -5000:
        score = 6
        details = f"散户中等流出：{-retail_inflow:.0f}万"
    else:
        score = 7  # 散户大量流出可能是正向指标
        details = f"散户大幅流出：{-retail_inflow:.0f}万（正向信号）"

    return {"score": score, "details": details, "retail_inflow": retail_inflow}


def analyze_fund_divergence(flow_data: dict) -> dict:
    """分析资金分歧"""
    main_inflow = flow_data.get("main_net_inflow", 0)
    retail_inflow = flow_data.get("retail_net_inflow", 0)

    # 主力与散户分歧
    divergence = main_inflow - retail_inflow

    if divergence > 10000:
        score = 8
        details = "主力吸筹：主力大幅流入，散户大幅流出"
    elif divergence > 5000:
        score = 7
        details = "主力偏多：主力流入，散户流出"
    elif divergence > 0:
        score = 6
        details = "资金分歧：主力流入大于散户"
    elif divergence > -5000:
        score = 5
        details = "资金分歧：散户流入大于主力"
    elif divergence > -10000:
        score = 4
        details = "散户偏多：散户流入，主力流出"
    else:
        score = 3
        details = "散户接盘：散户大幅流入，主力大幅流出"

    return {"score": score, "details": details, "divergence": divergence}


def analyze_fund_trend(flow_data: dict) -> dict:
    """分析资金趋势"""
    # 由于只有单日数据，这里简化处理
    # 实际应用中需要多日数据来判断趋势
    main_inflow = flow_data.get("main_net_inflow", 0)

    # 根据当日数据推断趋势
    if main_inflow > 5000:
        score = 7
        details = "当日主力资金强势流入，趋势偏多"
    elif main_inflow > 0:
        score = 6
        details = "当日主力资金流入，趋势中性偏多"
    elif main_inflow > -5000:
        score = 4
        details = "当日主力资金流出，趋势中性偏空"
    else:
        score = 3
        details = "当日主力资金强势流出，趋势偏空"

    return {"score": score, "details": details}


# 注册到分析师配置
ANALYST_CONFIG = {
    "a_stock_fund_flow": {
        "display_name": "A股资金流向分析师",
        "description": "资金流向专家",
        "investing_style": "跟踪主力资金、散户资金流向，分析资金分歧和趋势。主力资金被视为市场'聪明钱'，其流向对股价有重要影响。散户资金流向可作为反向指标参考。",
        "agent_func": a_stock_fund_flow_agent,
        "type": "analyst",
        "order": 21,
    }
}


__all__ = [
    "a_stock_fund_flow_agent",
    "AStockFundFlowSignal",
    "ANALYST_CONFIG",
]