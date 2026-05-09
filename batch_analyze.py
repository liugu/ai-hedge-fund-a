#!/usr/bin/env python3
"""批量股票分析脚本 - 分析A股主板和创业板股票，找出看涨标的"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from src.graph.state import AgentState
from src.utils.analysts import ANALYST_ORDER
from src.utils.progress import progress
import json

# 加载环境变量
load_dotenv()

def run_single_analysis(ticker: str, end_date: str, model_name: str = "claude-sonnet-4-20250514", model_provider: str = "Anthropic"):
    """分析单只股票"""
    from src.main import create_workflow

    # 使用所有分析师
    selected_analysts = [a[1] for a in ANALYST_ORDER]

    # 构建投资组合
    portfolio = {
        "cash": 100000.0,
        "margin_requirement": 0.0,
        "margin_used": 0.0,
        "positions": {
            ticker: {
                "long": 0,
                "short": 0,
                "long_cost_basis": 0.0,
                "short_cost_basis": 0.0,
                "short_margin_used": 0.0,
            }
        },
        "realized_gains": {
            ticker: {
                "long": 0.0,
                "short": 0.0,
            }
        },
    }

    # 计算开始日期（3个月前）
    from dateutil.relativedelta import relativedelta
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - relativedelta(months=3)).strftime("%Y-%m-%d")

    progress.start()
    try:
        workflow = create_workflow(selected_analysts)
        agent = workflow.compile()

        final_state = agent.invoke(
            {
                "messages": [
                    HumanMessage(content="根据提供的数据做出交易决策。")
                ],
                "data": {
                    "tickers": [ticker],
                    "portfolio": portfolio,
                    "start_date": start_date,
                    "end_date": end_date,
                    "analyst_signals": {},
                },
                "metadata": {
                    "show_reasoning": False,
                    "model_name": model_name,
                    "model_provider": model_provider,
                },
            },
        )

        response = final_state["messages"][-1].content
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            return {"raw_response": response}
    except Exception as e:
        return {"error": str(e)}
    finally:
        progress.stop()


def main():
    # 预定义股票列表
    main_board_stocks = [
        "600519",  # 贵州茅台
        "601318",  # 中国平安
        "600036",  # 招商银行
        "601166",  # 兴业银行
        "600276",  # 恒瑞医药
        "600887",  # 伊利股份
        "601888",  # 中国中免
        "600309",  # 万华化学
        "601012",  # 隆基绿能
        "600900",  # 长江电力
        "000001",  # 平安银行
        "000002",  # 万科A
        "000333",  # 美的集团
        "000651",  # 格力电器
        "000858",  # 五粮液
        "000568",  # 泸州老窖
        "002415",  # 海康威视
        "002304",  # 洋河股份
        "002594",  # 比亚迪
        "002352",  # 顺丰控股
    ]

    gem_stocks = [
        "300750",  # 宁德时代
        "300059",  # 东方财富
        "300015",  # 爱尔眼科
        "300014",  # 亿纬锂能
        "300124",  # 汇川技术
        "300274",  # 阳光电源
        "300122",  # 智飞生物
        "300347",  # 泰格医药
        "300760",  # 迈瑞医疗
        "300033",  # 同花顺
        "300498",  # 温氏股份
        "300146",  # 汤臣倍健
        "300408",  # 晶盛机电
        "300661",  # 圣邦股份
        "300782",  # 卓胜微
    ]

    all_stocks = main_board_stocks + gem_stocks
    end_date = datetime.now().strftime("%Y-%m-%d")

    print(f"开始批量分析 {len(all_stocks)} 只股票...")
    print(f"主板股票: {len(main_board_stocks)} 只")
    print(f"创业板股票: {len(gem_stocks)} 只")
    print("=" * 60)

    results = []
    bullish_stocks = []

    for i, ticker in enumerate(all_stocks, 1):
        print(f"\n[{i}/{len(all_stocks)}] 正在分析 {ticker}...")

        result = run_single_analysis(ticker, end_date)

        if "error" in result:
            print(f"  错误: {result['error']}")
            continue

        # 提取交易决策
        decisions = result.get("decisions", {})
        if isinstance(decisions, dict):
            ticker_decision = decisions.get(ticker, {})
            signal = ticker_decision.get("signal", "unknown")
            confidence = ticker_decision.get("confidence", 0)

            print(f"  信号: {signal}, 置信度: {confidence}")

            results.append({
                "ticker": ticker,
                "signal": signal,
                "confidence": confidence,
                "decision": ticker_decision
            })

            # 收集看涨标的
            if signal in ["long", "buy", "bullish"] or (signal == "long" and confidence >= 50):
                bullish_stocks.append({
                    "ticker": ticker,
                    "confidence": confidence,
                    "reasoning": ticker_decision.get("reasoning", "")
                })

    # 输出汇总结果
    print("\n" + "=" * 60)
    print("分析完成！看涨标的汇总：")
    print("=" * 60)

    if bullish_stocks:
        # 按置信度排序
        bullish_stocks.sort(key=lambda x: x["confidence"], reverse=True)

        for stock in bullish_stocks:
            print(f"\n{stock['ticker']}: 置信度 {stock['confidence']}%")
            print(f"  理由: {stock['reasoning'][:100]}..." if len(stock.get("reasoning", "")) > 100 else f"  理由: {stock.get('reasoning', 'N/A')}")
    else:
        print("未发现明确的看涨标的。")

    # 保存结果到文件
    output_file = "bullish_analysis_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "analysis_date": end_date,
            "total_analyzed": len(results),
            "bullish_stocks": bullish_stocks,
            "all_results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n详细结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
