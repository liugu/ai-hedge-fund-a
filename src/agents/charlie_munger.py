"""
查理·芒格代理

使用查理·芒格的投资原则和思维模型分析股票：
1. 护城河强度
2. 管理层质量
3. 业务可预测性
4. 估值合理性
"""

from src.graph.state import AgentState, show_agent_reasoning
from src.tools.api import get_financial_metrics, get_market_cap, search_line_items, get_insider_trades, get_company_news
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
import json
from typing_extensions import Literal
from src.utils.progress import progress
from src.utils.llm import call_llm
from src.utils.api_key import get_api_key_from_state


class CharlieMungerSignal(BaseModel):
    """查理·芒格信号模型"""
    signal: Literal["bullish", "bearish", "neutral"]
    confidence: int
    reasoning: str


def charlie_munger_agent(state: AgentState, agent_id: str = "charlie_munger_agent"):
    """
    使用查理·芒格的投资原则和思维模型分析股票。
    重点关注护城河强度、管理层质量、可预测性和估值。
    """
    data = state["data"]
    end_date = data["end_date"]
    tickers = data["tickers"]
    api_key = get_api_key_from_state(state, "FINANCIAL_DATASETS_API_KEY")
    analysis_data = {}
    munger_analysis = {}

    for ticker in tickers:
        progress.update_status(agent_id, ticker, "获取财务指标")
        metrics = get_financial_metrics(ticker, end_date, period="annual", limit=10, api_key=api_key)

        progress.update_status(agent_id, ticker, "收集财务数据")
        financial_line_items = search_line_items(
            ticker,
            [
                "revenue",  # 营收
                "net_income",  # 净利润
                "operating_income",  # 营业收入
                "return_on_invested_capital",  # 投资资本回报率
                "gross_margin",  # 毛利率
                "operating_margin",  # 营业利润率
                "free_cash_flow",  # 自由现金流
                "capital_expenditure",  # 资本支出
                "cash_and_equivalents",  # 现金及等价物
                "total_debt",  # 总债务
                "shareholders_equity",  # 股东权益
                "outstanding_shares",  # 流通股
                "research_and_development",  # 研发支出
                "goodwill_and_intangible_assets",  # 商誉和无形资产
            ],
            end_date,
            period="annual",
            limit=10,
            api_key=api_key,
        )

        progress.update_status(agent_id, ticker, "获取市值")
        market_cap = get_market_cap(ticker, end_date, api_key=api_key)

        progress.update_status(agent_id, ticker, "获取内部交易")
        insider_trades = get_insider_trades(ticker, end_date, limit=100, api_key=api_key)

        progress.update_status(agent_id, ticker, "获取公司新闻")
        company_news = get_company_news(ticker, end_date, limit=10, api_key=api_key)

        progress.update_status(agent_id, ticker, "分析护城河强度")
        moat_analysis = analyze_moat_strength(metrics, financial_line_items)

        progress.update_status(agent_id, ticker, "分析管理层质量")
        management_analysis = analyze_management_quality(financial_line_items, insider_trades)

        progress.update_status(agent_id, ticker, "分析业务可预测性")
        predictability_analysis = analyze_predictability(financial_line_items)

        progress.update_status(agent_id, ticker, "计算芒格式估值")
        valuation_analysis = calculate_munger_valuation(financial_line_items, market_cap)

        # 按芒格的权重偏好组合各部分得分
        # 芒格更看重质量和可预测性，而非当前估值
        total_score = (
            moat_analysis["score"] * 0.35 +
            management_analysis["score"] * 0.25 +
            predictability_analysis["score"] * 0.25 +
            valuation_analysis["score"] * 0.15
        )

        max_possible_score = 10

        # 生成简单的买入/持有/卖出信号
        if total_score >= 7.5:  # 芒格标准很高
            signal = "bullish"
        elif total_score <= 5.5:
            signal = "bearish"
        else:
            signal = "neutral"

        analysis_data[ticker] = {
            "signal": signal,
            "score": total_score,
            "max_score": max_possible_score,
            "moat_analysis": moat_analysis,
            "management_analysis": management_analysis,
            "predictability_analysis": predictability_analysis,
            "valuation_analysis": valuation_analysis,
            "news_sentiment": analyze_news_sentiment(company_news) if company_news else "无新闻数据"
        }

        progress.update_status(agent_id, ticker, "生成查理·芒格分析")
        munger_output = generate_munger_output(
            ticker=ticker,
            analysis_data=analysis_data[ticker],
            state=state,
            agent_id=agent_id,
            confidence_hint=compute_confidence(analysis_data[ticker], signal)
        )

        munger_analysis[ticker] = {
            "signal": munger_output.signal,
            "confidence": munger_output.confidence,
            "reasoning": munger_output.reasoning
        }

        progress.update_status(agent_id, ticker, "完成", analysis=munger_output.reasoning)

    message = HumanMessage(content=json.dumps(munger_analysis), name=agent_id)

    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(munger_analysis, "查理·芒格代理")

    progress.update_status(agent_id, None, "完成")

    state["data"]["analyst_signals"][agent_id] = munger_analysis

    return {"messages": [message], "data": state["data"]}


def analyze_moat_strength(metrics: list, financial_line_items: list) -> dict:
    """
    使用芒格的方法分析企业的竞争优势：
    - 持续的高资本回报率（ROIC）
    - 定价权（稳定/改善的毛利率）
    - 低资本需求
    - 网络效应和无形资产（研发投入、商誉）
    """
    score = 0
    details = []

    if not metrics or not financial_line_items:
        return {"score": 0, "details": "数据不足，无法分析护城河强度"}

    # 1. 投资资本回报率（ROIC）分析 - 芒格最喜欢的指标
    roic_values = [item.return_on_invested_capital for item in financial_line_items
                   if hasattr(item, 'return_on_invested_capital') and item.return_on_invested_capital is not None]

    if roic_values:
        high_roic_count = sum(1 for r in roic_values if r > 0.15)
        if high_roic_count >= len(roic_values) * 0.8:
            score += 3
            details.append(f"优秀的ROIC：{high_roic_count}/{len(roic_values)}期超过15%")
        elif high_roic_count >= len(roic_values) * 0.5:
            score += 2
            details.append(f"良好的ROIC：{high_roic_count}/{len(roic_values)}期超过15%")
        elif high_roic_count > 0:
            score += 1
            details.append(f"混合的ROIC：仅{high_roic_count}/{len(roic_values)}期超过15%")
        else:
            details.append("较差的ROIC：从未超过15%阈值")
    else:
        details.append("无ROIC数据")

    # 2. 定价权 - 检查毛利率稳定性和趋势
    gross_margins = [item.gross_margin for item in financial_line_items
                    if hasattr(item, 'gross_margin') and item.gross_margin is not None]

    if gross_margins and len(gross_margins) >= 3:
        margin_trend = sum(1 for i in range(1, len(gross_margins)) if gross_margins[i] >= gross_margins[i-1])
        if margin_trend >= len(gross_margins) * 0.7:
            score += 2
            details.append("强劲的定价权：毛利率持续改善")
        elif sum(gross_margins) / len(gross_margins) > 0.3:
            score += 1
            details.append(f"良好的定价权：平均毛利率{sum(gross_margins)/len(gross_margins):.1%}")
        else:
            details.append("有限的定价权：毛利率低或下降")
    else:
        details.append("毛利率数据不足")

    # 3. 资本密集度 - 芒格偏好低资本支出业务
    if len(financial_line_items) >= 3:
        capex_to_revenue = []
        for item in financial_line_items:
            if (hasattr(item, 'capital_expenditure') and item.capital_expenditure is not None and
                hasattr(item, 'revenue') and item.revenue is not None and item.revenue > 0):
                capex_ratio = abs(item.capital_expenditure) / item.revenue
                capex_to_revenue.append(capex_ratio)

        if capex_to_revenue:
            avg_capex_ratio = sum(capex_to_revenue) / len(capex_to_revenue)
            if avg_capex_ratio < 0.05:
                score += 2
                details.append(f"低资本需求：平均资本支出占营收{avg_capex_ratio:.1%}")
            elif avg_capex_ratio < 0.10:
                score += 1
                details.append(f"中等资本需求：平均资本支出占营收{avg_capex_ratio:.1%}")
            else:
                details.append(f"高资本需求：平均资本支出占营收{avg_capex_ratio:.1%}")
        else:
            details.append("无资本支出数据")
    else:
        details.append("资本密集度分析数据不足")

    # 4. 无形资产 - 芒格重视研发和知识产权
    r_and_d = [item.research_and_development for item in financial_line_items
              if hasattr(item, 'research_and_development') and item.research_and_development is not None]

    if r_and_d and sum(r_and_d) > 0:
        score += 1
        details.append("投资研发，构建知识产权")

    goodwill_and_intangible = [item.goodwill_and_intangible_assets for item in financial_line_items
               if hasattr(item, 'goodwill_and_intangible_assets') and item.goodwill_and_intangible_assets is not None]

    if goodwill_and_intangible and len(goodwill_and_intangible) > 0:
        score += 1
        details.append("显著的商誉/无形资产，表明品牌价值或知识产权")

    final_score = min(10, score * 10 / 9)

    return {"score": final_score, "details": "; ".join(details)}


def analyze_management_quality(financial_line_items: list, insider_trades: list) -> dict:
    """
    使用芒格的标准评估管理层质量：
    - 资本配置智慧
    - 内部人持股和交易
    - 现金管理效率
    - 坦诚和透明度
    - 长期导向
    """
    score = 0
    details = []

    if not financial_line_items:
        return {"score": 0, "details": "数据不足，无法分析管理层质量"}

    # 1. 资本配置 - 检查FCF与净利润比率
    fcf_values = [item.free_cash_flow for item in financial_line_items
                 if hasattr(item, 'free_cash_flow') and item.free_cash_flow is not None]

    net_income_values = [item.net_income for item in financial_line_items
                        if hasattr(item, 'net_income') and item.net_income is not None]

    if fcf_values and net_income_values and len(fcf_values) == len(net_income_values):
        fcf_to_ni_ratios = []
        for i in range(len(fcf_values)):
            if net_income_values[i] and net_income_values[i] > 0:
                fcf_to_ni_ratios.append(fcf_values[i] / net_income_values[i])

        if fcf_to_ni_ratios:
            avg_ratio = sum(fcf_to_ni_ratios) / len(fcf_to_ni_ratios)
            if avg_ratio > 1.1:
                score += 3
                details.append(f"优秀的现金转换：FCF/净利润比率{avg_ratio:.2f}")
            elif avg_ratio > 0.9:
                score += 2
                details.append(f"良好的现金转换：FCF/净利润比率{avg_ratio:.2f}")
            elif avg_ratio > 0.7:
                score += 1
                details.append(f"中等的现金转换：FCF/净利润比率{avg_ratio:.2f}")
            else:
                details.append(f"较差的现金转换：FCF/净利润比率仅{avg_ratio:.2f}")
    else:
        details.append("缺少FCF或净利润数据")

    # 2. 债务管理 - 芒格对债务很谨慎
    debt_values = [item.total_debt for item in financial_line_items
                  if hasattr(item, 'total_debt') and item.total_debt is not None]

    equity_values = [item.shareholders_equity for item in financial_line_items
                    if hasattr(item, 'shareholders_equity') and item.shareholders_equity is not None]

    recent_de_ratio = None
    if debt_values and equity_values and len(debt_values) == len(equity_values):
        recent_de_ratio = debt_values[0] / equity_values[0] if equity_values[0] > 0 else float('inf')

        if recent_de_ratio < 0.3:
            score += 3
            details.append(f"保守的债务管理：资产负债率{recent_de_ratio:.2f}")
        elif recent_de_ratio < 0.7:
            score += 2
            details.append(f"审慎的债务管理：资产负债率{recent_de_ratio:.2f}")
        elif recent_de_ratio < 1.5:
            score += 1
            details.append(f"中等的债务水平：资产负债率{recent_de_ratio:.2f}")
        else:
            details.append(f"高债务水平：资产负债率{recent_de_ratio:.2f}")
    else:
        details.append("缺少债务或权益数据")

    # 3. 现金管理效率
    cash_values = [item.cash_and_equivalents for item in financial_line_items
                  if hasattr(item, 'cash_and_equivalents') and item.cash_and_equivalents is not None]
    revenue_values = [item.revenue for item in financial_line_items
                     if hasattr(item, 'revenue') and item.revenue is not None]

    cash_to_revenue = None
    if cash_values and revenue_values and revenue_values[0] > 0:
        cash_to_revenue = cash_values[0] / revenue_values[0]

        if 0.1 <= cash_to_revenue <= 0.25:
            score += 2
            details.append(f"审慎的现金管理：现金/营收比率{cash_to_revenue:.2f}")
        elif 0.05 <= cash_to_revenue < 0.1 or 0.25 < cash_to_revenue <= 0.4:
            score += 1
            details.append(f"可接受的现金头寸：现金/营收比率{cash_to_revenue:.2f}")
        elif cash_to_revenue > 0.4:
            details.append(f"过多的现金储备：现金/营收比率{cash_to_revenue:.2f}")
        else:
            details.append(f"低现金储备：现金/营收比率{cash_to_revenue:.2f}")
    else:
        details.append("现金或营收数据不足")

    # 4. 内部人活动 - 芒格重视利益绑定
    insider_buy_ratio = None
    if insider_trades and len(insider_trades) > 0:
        buys = sum(1 for trade in insider_trades if hasattr(trade, 'transaction_type') and
                   trade.transaction_type and trade.transaction_type.lower() in ['buy', 'purchase'])
        sells = sum(1 for trade in insider_trades if hasattr(trade, 'transaction_type') and
                    trade.transaction_type and trade.transaction_type.lower() in ['sell', 'sale'])

        total_trades = buys + sells
        if total_trades > 0:
            insider_buy_ratio = buys / total_trades
            if insider_buy_ratio > 0.7:
                score += 2
                details.append(f"强劲的内部人买入：{buys}/{total_trades}笔交易为买入")
            elif insider_buy_ratio > 0.4:
                score += 1
                details.append(f"平衡的内部人交易：{buys}/{total_trades}笔交易为买入")
            elif insider_buy_ratio < 0.1 and sells > 5:
                score -= 1
                details.append(f"令人担忧的内部人卖出：{sells}/{total_trades}笔交易为卖出")
            else:
                details.append(f"混合的内部人活动：{buys}/{total_trades}笔交易为买入")
        else:
            details.append("无记录的内部人交易")
    else:
        details.append("无内部人交易数据")

    # 5. 股份数量一致性 - 芒格偏好稳定/减少的股份
    share_counts = [item.outstanding_shares for item in financial_line_items
                   if hasattr(item, 'outstanding_shares') and item.outstanding_shares is not None]

    share_count_trend = "unknown"
    if share_counts and len(share_counts) >= 3:
        if share_counts[0] < share_counts[-1] * 0.95:
            score += 2
            share_count_trend = "decreasing"
            details.append("对股东友好：股份数量随时间减少")
        elif share_counts[0] < share_counts[-1] * 1.05:
            score += 1
            share_count_trend = "stable"
            details.append("稳定的股份数量：有限稀释")
        elif share_counts[0] > share_counts[-1] * 1.2:
            score -= 1
            share_count_trend = "increasing"
            details.append("令人担忧的稀释：股份数量显著增加")
        else:
            share_count_trend = "stable"
            details.append("股份数量随时间适度增加")
    else:
        details.append("股份数量数据不足")

    final_score = max(0, min(10, score * 10 / 12))

    return {
        "score": final_score,
        "details": "; ".join(details),
        "insider_buy_ratio": insider_buy_ratio,
        "recent_de_ratio": recent_de_ratio,
        "cash_to_revenue": cash_to_revenue,
        "share_count_trend": share_count_trend,
    }


def analyze_predictability(financial_line_items: list) -> dict:
    """
    评估业务的可预测性 - 芒格强烈偏好未来运营和现金流相对容易预测的业务。
    """
    score = 0
    details = []

    if not financial_line_items or len(financial_line_items) < 5:
        return {"score": 0, "details": "数据不足，无法分析业务可预测性（需要5年以上）"}

    # 1. 营收稳定性和增长
    revenues = [item.revenue for item in financial_line_items
               if hasattr(item, 'revenue') and item.revenue is not None]

    if revenues and len(revenues) >= 5:
        growth_rates = []
        for i in range(len(revenues)-1):
            if revenues[i+1] != 0:
                growth_rate = (revenues[i] / revenues[i+1] - 1)
                growth_rates.append(growth_rate)

        if growth_rates:
            avg_growth = sum(growth_rates) / len(growth_rates)
            growth_volatility = sum(abs(r - avg_growth) for r in growth_rates) / len(growth_rates)

            if avg_growth > 0.05 and growth_volatility < 0.1:
                score += 3
                details.append(f"高度可预测的营收：{avg_growth:.1%}平均增长，低波动性")
            elif avg_growth > 0 and growth_volatility < 0.2:
                score += 2
                details.append(f"中等可预测的营收：{avg_growth:.1%}平均增长，有些波动")
            elif avg_growth > 0:
                score += 1
                details.append(f"增长但可预测性较低的营收：{avg_growth:.1%}平均增长，高波动性")
            else:
                details.append(f"下降或高度不可预测的营收：{avg_growth:.1%}平均增长")
    else:
        details.append("营收历史不足以进行可预测性分析")

    # 2. 营业收入稳定性
    op_income = [item.operating_income for item in financial_line_items
                if hasattr(item, 'operating_income') and item.operating_income is not None]

    if op_income and len(op_income) >= 5:
        positive_periods = sum(1 for income in op_income if income > 0)

        if positive_periods == len(op_income):
            score += 3
            details.append("高度可预测的运营：所有期营业收入均为正")
        elif positive_periods >= len(op_income) * 0.8:
            score += 2
            details.append(f"可预测的运营：{positive_periods}/{len(op_income)}期营业收入为正")
        elif positive_periods >= len(op_income) * 0.6:
            score += 1
            details.append(f"有些可预测的运营：{positive_periods}/{len(op_income)}期营业收入为正")
        else:
            details.append(f"不可预测的运营：仅{positive_periods}/{len(op_income)}期营业收入为正")
    else:
        details.append("营业收入历史不足")

    # 3. 利润率一致性 - 芒格重视稳定的利润率
    op_margins = [item.operating_margin for item in financial_line_items
                 if hasattr(item, 'operating_margin') and item.operating_margin is not None]

    if op_margins and len(op_margins) >= 5:
        avg_margin = sum(op_margins) / len(op_margins)
        margin_volatility = sum(abs(m - avg_margin) for m in op_margins) / len(op_margins)

        if margin_volatility < 0.03:
            score += 2
            details.append(f"高度可预测的利润率：{avg_margin:.1%}平均，最小波动")
        elif margin_volatility < 0.07:
            score += 1
            details.append(f"中等可预测的利润率：{avg_margin:.1%}平均，有些波动")
        else:
            details.append(f"不可预测的利润率：{avg_margin:.1%}平均，高波动性（{margin_volatility:.1%}）")
    else:
        details.append("利润率历史不足")

    # 4. 现金生成可靠性
    fcf_values = [item.free_cash_flow for item in financial_line_items
                 if hasattr(item, 'free_cash_flow') and item.free_cash_flow is not None]

    if fcf_values and len(fcf_values) >= 5:
        positive_fcf_periods = sum(1 for fcf in fcf_values if fcf > 0)

        if positive_fcf_periods == len(fcf_values):
            score += 2
            details.append("高度可预测的现金生成：所有期FCF为正")
        elif positive_fcf_periods >= len(fcf_values) * 0.8:
            score += 1
            details.append(f"可预测的现金生成：{positive_fcf_periods}/{len(fcf_values)}期FCF为正")
        else:
            details.append(f"不可预测的现金生成：仅{positive_fcf_periods}/{len(fcf_values)}期FCF为正")
    else:
        details.append("自由现金流历史不足")

    final_score = min(10, score)

    return {"score": final_score, "details": "; ".join(details)}


def calculate_munger_valuation(financial_line_items: list, market_cap: float) -> dict:
    """
    使用芒格的方法计算内在价值：
    - 关注所有者收益（近似为FCF）
    - 对正常化收益应用简单倍数
    - 宁愿以合理价格买入优秀企业
    """
    score = 0
    details = []

    if not financial_line_items or market_cap is None:
        return {"score": 0, "details": "数据不足，无法进行估值"}

    fcf_values = [item.free_cash_flow for item in financial_line_items
                 if hasattr(item, 'free_cash_flow') and item.free_cash_flow is not None]

    if not fcf_values or len(fcf_values) < 3:
        return {"score": 0, "details": "自由现金流数据不足以进行估值"}

    # 1. 通过取最近3-5年的平均值来正常化收益
    normalized_fcf = sum(fcf_values[:min(5, len(fcf_values))]) / min(5, len(fcf_values))

    if normalized_fcf <= 0:
        return {"score": 0, "details": f"负或零的正常化FCF（{normalized_fcf}），无法估值", "intrinsic_value": None}

    # 2. 计算FCF收益率
    if market_cap <= 0:
        return {"score": 0, "details": f"无效的市值（{market_cap}），无法估值"}

    fcf_yield = normalized_fcf / market_cap

    # 3. 根据业务质量应用芒格的FCF倍数
    if fcf_yield > 0.08:
        score += 4
        details.append(f"优秀的价值：{fcf_yield:.1%} FCF收益率")
    elif fcf_yield > 0.05:
        score += 3
        details.append(f"良好的价值：{fcf_yield:.1%} FCF收益率")
    elif fcf_yield > 0.03:
        score += 1
        details.append(f"合理的价值：{fcf_yield:.1%} FCF收益率")
    else:
        details.append(f"昂贵：仅{fcf_yield:.1%} FCF收益率")

    # 4. 计算简单的内在价值范围
    conservative_value = normalized_fcf * 10
    reasonable_value = normalized_fcf * 15
    optimistic_value = normalized_fcf * 20

    # 5. 计算安全边际
    margin_of_safety_vs_fair_value = (reasonable_value - market_cap) / market_cap

    if margin_of_safety_vs_fair_value > 0.3:
        score += 3
        details.append(f"大的安全边际：相对合理价值{margin_of_safety_vs_fair_value:.1%}上涨空间")
    elif margin_of_safety_vs_fair_value > 0.1:
        score += 2
        details.append(f"中等安全边际：相对合理价值{margin_of_safety_vs_fair_value:.1%}上涨空间")
    elif margin_of_safety_vs_fair_value > -0.1:
        score += 1
        details.append(f"合理的价格：在合理价值的10%以内（{margin_of_safety_vs_fair_value:.1%}）")
    else:
        details.append(f"昂贵：相对合理价值{-margin_of_safety_vs_fair_value:.1%}溢价")

    # 6. 检查收益轨迹
    if len(fcf_values) >= 3:
        recent_avg = sum(fcf_values[:3]) / 3
        older_avg = sum(fcf_values[-3:]) / 3 if len(fcf_values) >= 6 else fcf_values[-1]

        if recent_avg > older_avg * 1.2:
            score += 3
            details.append("增长的FCF趋势增加了内在价值")
        elif recent_avg > older_avg:
            score += 2
            details.append("稳定到增长的FCF支持估值")
        else:
            details.append("下降的FCF趋势令人担忧")

    final_score = min(10, score)

    return {
        "score": final_score,
        "details": "; ".join(details),
        "intrinsic_value_range": {
            "conservative": conservative_value,
            "reasonable": reasonable_value,
            "optimistic": optimistic_value
        },
        "fcf_yield": fcf_yield,
        "normalized_fcf": normalized_fcf,
        "margin_of_safety_vs_fair_value": margin_of_safety_vs_fair_value,
    }


def analyze_news_sentiment(news_items: list) -> str:
    """简单的新闻情绪定性分析"""
    if not news_items or len(news_items) == 0:
        return "无新闻数据"

    return f"需要对{len(news_items)}条近期新闻进行定性审查"


def _r(x, n=3):
    try:
        return round(float(x), n)
    except Exception:
        return None


def make_munger_facts_bundle(analysis: dict) -> dict:
    """构建芒格的事实包"""
    moat = analysis.get("moat_analysis") or {}
    mgmt = analysis.get("management_analysis") or {}
    pred = analysis.get("predictability_analysis") or {}
    val = analysis.get("valuation_analysis") or {}
    ivr = val.get("intrinsic_value_range") or {}

    moat_score = _r(moat.get("score"), 2) or 0
    mgmt_score = _r(mgmt.get("score"), 2) or 0
    pred_score = _r(pred.get("score"), 2) or 0
    val_score = _r(val.get("score"), 2) or 0

    flags = {
        "moat_strong": moat_score >= 7,
        "predictable": pred_score >= 7,
        "owner_aligned": (mgmt_score >= 7) or ((mgmt.get("insider_buy_ratio") or 0) >= 0.6),
        "low_leverage": (mgmt.get("recent_de_ratio") is not None and mgmt.get("recent_de_ratio") < 0.7),
        "sensible_cash": (mgmt.get("cash_to_revenue") is not None and 0.1 <= mgmt.get("cash_to_revenue") <= 0.25),
        "mos_positive": (val.get("margin_of_safety_vs_fair_value") or 0) > 0.0,
        "fcf_yield_ok": (val.get("fcf_yield") or 0) >= 0.05,
        "share_count_friendly": (mgmt.get("share_count_trend") == "decreasing"),
    }

    return {
        "pre_signal": analysis.get("signal"),
        "score": _r(analysis.get("score"), 2),
        "max_score": _r(analysis.get("max_score"), 2),
        "moat_score": moat_score,
        "mgmt_score": mgmt_score,
        "predictability_score": pred_score,
        "valuation_score": val_score,
        "fcf_yield": _r(val.get("fcf_yield"), 4),
        "normalized_fcf": _r(val.get("normalized_fcf"), 0),
        "reasonable_value": _r(ivr.get("reasonable"), 0),
        "margin_of_safety_vs_fair_value": _r(val.get("margin_of_safety_vs_fair_value"), 3),
        "insider_buy_ratio": _r(mgmt.get("insider_buy_ratio"), 2),
        "recent_de_ratio": _r(mgmt.get("recent_de_ratio"), 2),
        "cash_to_revenue": _r(mgmt.get("cash_to_revenue"), 2),
        "share_count_trend": mgmt.get("share_count_trend"),
        "flags": flags,
        "notes": {
            "moat": (moat.get("details") or "")[:120],
            "mgmt": (mgmt.get("details") or "")[:120],
            "predictability": (pred.get("details") or "")[:120],
            "valuation": (val.get("details") or "")[:120],
        },
    }


def compute_confidence(analysis: dict, signal: str) -> int:
    """计算置信度"""
    moat = float((analysis.get("moat_analysis") or {}).get("score") or 0)
    mgmt = float((analysis.get("management_analysis") or {}).get("score") or 0)
    pred = float((analysis.get("predictability_analysis") or {}).get("score") or 0)
    val = float((analysis.get("valuation_analysis") or {}).get("score") or 0)

    quality = 0.35 * moat + 0.25 * mgmt + 0.25 * pred
    quality_pct = 100 * (quality / 8.5) if quality > 0 else 0

    mos = (analysis.get("valuation_analysis") or {}).get("margin_of_safety_vs_fair_value")
    mos = float(mos) if mos is not None else 0.0
    val_adj = max(-10.0, min(10.0, mos * 100.0 / 3.0))

    base = 0.85 * quality_pct + 0.15 * (val * 10)
    base = base + val_adj

    if signal == "bullish":
        upper = 100 if mos > 0 else 69
        lower = 50 if quality_pct >= 55 else 30
    elif signal == "bearish":
        lower = 10 if mos < -0.05 else 30
        upper = 49
    else:
        lower, upper = 50, 69

    conf = int(round(max(lower, min(upper, base))))
    return max(10, min(100, conf))


def generate_munger_output(
    ticker: str,
    analysis_data: dict,
    state: AgentState,
    agent_id: str,
    confidence_hint: int,
) -> CharlieMungerSignal:
    """生成芒格风格的输出"""
    facts_bundle = make_munger_facts_bundle(analysis_data)
    template = ChatPromptTemplate.from_messages([
        ("system",
         "你是查理·芒格。仅根据事实决定看涨、看跌或中性。"
         "只返回JSON。推理保持在120字符以内。"
         "使用提供的置信度，不要更改。"),
        ("human",
         "股票代码：{ticker}\n"
         "事实：\n{facts}\n"
         "置信度：{confidence}\n"
         "返回：\n"
         "{{\n"
         '  "signal": "bullish" | "bearish" | "neutral",\n'
         f'  "confidence": {confidence_hint},\n'
         '  "reasoning": "简短理由"\n'
         "}}")
    ])

    prompt = template.invoke({
        "ticker": ticker,
        "facts": json.dumps(facts_bundle, separators=(",", ":"), ensure_ascii=False),
        "confidence": confidence_hint,
    })

    def _default():
        return CharlieMungerSignal(signal="neutral", confidence=confidence_hint, reasoning="数据不足")

    return call_llm(
        prompt=prompt,
        pydantic_model=CharlieMungerSignal,
        agent_name=agent_id,
        state=state,
        default_factory=_default,
    )