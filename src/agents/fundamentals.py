from langchain_core.messages import HumanMessage
from src.graph.state import AgentState, show_agent_reasoning
from src.utils.api_key import get_api_key_from_state
from src.utils.progress import progress
import json

from src.tools.api import get_financial_metrics


##### 基本面分析代理 #####
def fundamentals_analyst_agent(state: AgentState, agent_id: str = "fundamentals_analyst_agent"):
    """分析基本面数据并为多只股票生成交易信号"""
    data = state["data"]
    end_date = data["end_date"]
    tickers = data["tickers"]
    api_key = get_api_key_from_state(state, "FINANCIAL_DATASETS_API_KEY")
    # 初始化每只股票的基本面分析
    fundamental_analysis = {}

    for ticker in tickers:
        progress.update_status(agent_id, ticker, "获取财务指标")

        # 获取财务指标
        financial_metrics = get_financial_metrics(
            ticker=ticker,
            end_date=end_date,
            period="ttm",
            limit=10,
            api_key=api_key,
        )

        if not financial_metrics:
            progress.update_status(agent_id, ticker, "失败：未找到财务指标")
            continue

        # 提取最近的财务指标
        metrics = financial_metrics[0]

        # 初始化不同基本面方面的信号列表
        signals = []
        reasoning = {}

        progress.update_status(agent_id, ticker, "分析盈利能力")
        # 1. 盈利能力分析
        return_on_equity = metrics.return_on_equity  # 净资产收益率
        net_margin = metrics.net_margin  # 净利润率
        operating_margin = metrics.operating_margin  # 营业利润率

        thresholds = [
            (return_on_equity, 0.15),  # 强劲的ROE超过15%
            (net_margin, 0.20),  # 健康的净利润率
            (operating_margin, 0.15),  # 强劲的运营效率
        ]
        profitability_score = sum(metric is not None and metric > threshold for metric, threshold in thresholds)

        signals.append("bullish" if profitability_score >= 2 else "bearish" if profitability_score == 0 else "neutral")
        reasoning["profitability_signal"] = {
            "signal": signals[0],
            "details": (f"ROE: {return_on_equity:.2%}" if return_on_equity else "ROE: 无数据") + ", " + (f"净利润率: {net_margin:.2%}" if net_margin else "净利润率: 无数据") + ", " + (f"营业利润率: {operating_margin:.2%}" if operating_margin else "营业利润率: 无数据"),
        }

        progress.update_status(agent_id, ticker, "分析增长")
        # 2. 增长分析
        revenue_growth = metrics.revenue_growth  # 营收增长
        earnings_growth = metrics.earnings_growth  # 盈利增长
        book_value_growth = metrics.book_value_growth  # 账面价值增长

        thresholds = [
            (revenue_growth, 0.10),  # 10%营收增长
            (earnings_growth, 0.10),  # 10%盈利增长
            (book_value_growth, 0.10),  # 10%账面价值增长
        ]
        growth_score = sum(metric is not None and metric > threshold for metric, threshold in thresholds)

        signals.append("bullish" if growth_score >= 2 else "bearish" if growth_score == 0 else "neutral")
        reasoning["growth_signal"] = {
            "signal": signals[1],
            "details": (f"营收增长: {revenue_growth:.2%}" if revenue_growth else "营收增长: 无数据") + ", " + (f"盈利增长: {earnings_growth:.2%}" if earnings_growth else "盈利增长: 无数据"),
        }

        progress.update_status(agent_id, ticker, "分析财务健康")
        # 3. 财务健康分析
        current_ratio = metrics.current_ratio  # 流动比率
        debt_to_equity = metrics.debt_to_equity  # 资产负债率
        free_cash_flow_per_share = metrics.free_cash_flow_per_share  # 每股自由现金流
        earnings_per_share = metrics.earnings_per_share  # 每股收益

        health_score = 0
        if current_ratio and current_ratio > 1.5:  # 强劲的流动性
            health_score += 1
        if debt_to_equity and debt_to_equity < 0.5:  # 保守的债务水平
            health_score += 1
        if free_cash_flow_per_share and earnings_per_share and free_cash_flow_per_share > earnings_per_share * 0.8:  # 强劲的FCF转换
            health_score += 1

        signals.append("bullish" if health_score >= 2 else "bearish" if health_score == 0 else "neutral")
        reasoning["financial_health_signal"] = {
            "signal": signals[2],
            "details": (f"流动比率: {current_ratio:.2f}" if current_ratio else "流动比率: 无数据") + ", " + (f"资产负债率: {debt_to_equity:.2f}" if debt_to_equity else "资产负债率: 无数据"),
        }

        progress.update_status(agent_id, ticker, "分析估值比率")
        # 4. 价格比率分析
        pe_ratio = metrics.price_to_earnings_ratio  # 市盈率
        pb_ratio = metrics.price_to_book_ratio  # 市净率
        ps_ratio = metrics.price_to_sales_ratio  # 市销率

        thresholds = [
            (pe_ratio, 25),  # 合理的市盈率
            (pb_ratio, 3),  # 合理的市净率
            (ps_ratio, 5),  # 合理的市销率
        ]
        price_ratio_score = sum(metric is not None and metric > threshold for metric, threshold in thresholds)

        signals.append("bearish" if price_ratio_score >= 2 else "bullish" if price_ratio_score == 0 else "neutral")
        reasoning["price_ratios_signal"] = {
            "signal": signals[3],
            "details": (f"市盈率: {pe_ratio:.2f}" if pe_ratio else "市盈率: 无数据") + ", " + (f"市净率: {pb_ratio:.2f}" if pb_ratio else "市净率: 无数据") + ", " + (f"市销率: {ps_ratio:.2f}" if ps_ratio else "市销率: 无数据"),
        }

        progress.update_status(agent_id, ticker, "计算最终信号")
        # 确定整体信号
        bullish_signals = signals.count("bullish")
        bearish_signals = signals.count("bearish")

        if bullish_signals > bearish_signals:
            overall_signal = "bullish"
        elif bearish_signals > bullish_signals:
            overall_signal = "bearish"
        else:
            overall_signal = "neutral"

        # 计算置信度水平
        total_signals = len(signals)
        confidence = round(max(bullish_signals, bearish_signals) / total_signals, 2) * 100

        fundamental_analysis[ticker] = {
            "signal": overall_signal,
            "confidence": confidence,
            "reasoning": reasoning,
        }

        progress.update_status(agent_id, ticker, "完成", analysis=json.dumps(reasoning, indent=4))

    # 创建基本面分析消息
    message = HumanMessage(
        content=json.dumps(fundamental_analysis),
        name=agent_id,
    )

    # 如果设置了标志，打印推理过程
    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(fundamental_analysis, "基本面分析代理")

    # 将信号添加到analyst_signals列表
    state["data"]["analyst_signals"][agent_id] = fundamental_analysis

    progress.update_status(agent_id, None, "完成")

    return {
        "messages": [message],
        "data": data,
    }