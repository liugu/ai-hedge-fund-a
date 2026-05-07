from colorama import Fore, Style
from tabulate import tabulate
from .analysts import ANALYST_ORDER
import os
import json


def sort_agent_signals(signals):
    """按一致顺序排序代理信号"""
    # 从ANALYST_ORDER创建顺序映射
    analyst_order = {display: idx for idx, (display, _) in enumerate(ANALYST_ORDER)}
    analyst_order["风险管理"] = len(ANALYST_ORDER)  # 在末尾添加风险管理

    return sorted(signals, key=lambda x: analyst_order.get(x[0], 999))


def print_trading_output(result: dict) -> None:
    """
    打印格式化的交易结果，支持多只股票的彩色表格。

    参数：
        result (dict): 包含多只股票决策和分析师信号的字典
    """
    decisions = result.get("decisions")
    if not decisions:
        print(f"{Fore.RED}没有可用的交易决策{Style.RESET_ALL}")
        return

    # 打印每只股票的决策
    for ticker, decision in decisions.items():
        print(f"\n{Fore.WHITE}{Style.BRIGHT}分析结果：{Fore.CYAN}{ticker}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{Style.BRIGHT}{'=' * 50}{Style.RESET_ALL}")

        # 准备该股票的分析师信号表格
        table_data = []
        for agent, signals in result.get("analyst_signals", {}).items():
            if ticker not in signals:
                continue

            # 在信号部分跳过风险管理代理
            if agent == "risk_management_agent":
                continue

            signal = signals[ticker]
            agent_name = agent.replace("_agent", "").replace("_", " ").title()
            signal_type = signal.get("signal", "").upper()
            confidence = signal.get("confidence", 0)

            signal_color = {
                "BULLISH": Fore.GREEN,
                "BEARISH": Fore.RED,
                "NEUTRAL": Fore.YELLOW,
            }.get(signal_type, Fore.WHITE)

            # 获取推理（如果可用）
            reasoning_str = ""
            if "reasoning" in signal and signal["reasoning"]:
                reasoning = signal["reasoning"]

                # 处理不同类型的推理（字符串、字典等）
                if isinstance(reasoning, str):
                    reasoning_str = reasoning
                elif isinstance(reasoning, dict):
                    # 将字典转换为字符串表示
                    reasoning_str = json.dumps(reasoning, indent=2)
                else:
                    # 将其他类型转换为字符串
                    reasoning_str = str(reasoning)

                # 换行长文本使其更易读
                wrapped_reasoning = ""
                current_line = ""
                # 使用固定宽度60字符以匹配表格列宽
                max_line_length = 60
                for word in reasoning_str.split():
                    if len(current_line) + len(word) + 1 > max_line_length:
                        wrapped_reasoning += current_line + "\n"
                        current_line = word
                    else:
                        if current_line:
                            current_line += " " + word
                        else:
                            current_line = word
                if current_line:
                    wrapped_reasoning += current_line

                reasoning_str = wrapped_reasoning

            table_data.append(
                [
                    f"{Fore.CYAN}{agent_name}{Style.RESET_ALL}",
                    f"{signal_color}{signal_type}{Style.RESET_ALL}",
                    f"{Fore.WHITE}{confidence}%{Style.RESET_ALL}",
                    f"{Fore.WHITE}{reasoning_str}{Style.RESET_ALL}",
                ]
            )

        # 按预定义顺序排序信号
        table_data = sort_agent_signals(table_data)

        print(f"\n{Fore.WHITE}{Style.BRIGHT}分析师分析：{Style.RESET_ALL} [{Fore.CYAN}{ticker}{Style.RESET_ALL}]")
        print(
            tabulate(
                table_data,
                headers=[f"{Fore.WHITE}分析师", "信号", "置信度", "分析理由"],
                tablefmt="grid",
                colalign=("left", "center", "right", "left"),
            )
        )

        # 打印交易决策表
        action = decision.get("action", "").upper()
        action_color = {
            "BUY": Fore.GREEN,
            "SELL": Fore.RED,
            "HOLD": Fore.YELLOW,
            "COVER": Fore.GREEN,
            "SHORT": Fore.RED,
        }.get(action, Fore.WHITE)

        # 获取推理并格式化
        reasoning = decision.get("reasoning", "")
        # 换行长文本使其更易读
        wrapped_reasoning = ""
        if reasoning:
            current_line = ""
            # 使用固定宽度60字符以匹配表格列宽
            max_line_length = 60
            for word in reasoning.split():
                if len(current_line) + len(word) + 1 > max_line_length:
                    wrapped_reasoning += current_line + "\n"
                    current_line = word
                else:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
            if current_line:
                wrapped_reasoning += current_line

        decision_data = [
            ["操作", f"{action_color}{action}{Style.RESET_ALL}"],
            ["数量", f"{action_color}{decision.get('quantity')}{Style.RESET_ALL}"],
            [
                "置信度",
                f"{Fore.WHITE}{decision.get('confidence'):.1f}%{Style.RESET_ALL}",
            ],
            ["理由", f"{Fore.WHITE}{wrapped_reasoning}{Style.RESET_ALL}"],
        ]

        print(f"\n{Fore.WHITE}{Style.BRIGHT}交易决策：{Style.RESET_ALL} [{Fore.CYAN}{ticker}{Style.RESET_ALL}]")
        print(tabulate(decision_data, tablefmt="grid", colalign=("left", "left")))

    # 打印组合摘要
    print(f"\n{Fore.WHITE}{Style.BRIGHT}投资组合摘要：{Style.RESET_ALL}")
    portfolio_data = []

    # 提取组合管理代理的推理（对所有股票通用）
    portfolio_manager_reasoning = None
    for ticker, decision in decisions.items():
        if decision.get("reasoning"):
            portfolio_manager_reasoning = decision.get("reasoning")
            break

    analyst_signals = result.get("analyst_signals", {})
    for ticker, decision in decisions.items():
        action = decision.get("action", "").upper()
        action_color = {
            "BUY": Fore.GREEN,
            "SELL": Fore.RED,
            "HOLD": Fore.YELLOW,
            "COVER": Fore.GREEN,
            "SHORT": Fore.RED,
        }.get(action, Fore.WHITE)

        # 计算分析师信号统计
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        if analyst_signals:
            for agent, signals in analyst_signals.items():
                if ticker in signals:
                    signal = signals[ticker].get("signal", "").upper()
                    if signal == "BULLISH":
                        bullish_count += 1
                    elif signal == "BEARISH":
                        bearish_count += 1
                    elif signal == "NEUTRAL":
                        neutral_count += 1

        portfolio_data.append(
            [
                f"{Fore.CYAN}{ticker}{Style.RESET_ALL}",
                f"{action_color}{action}{Style.RESET_ALL}",
                f"{action_color}{decision.get('quantity')}{Style.RESET_ALL}",
                f"{Fore.WHITE}{decision.get('confidence'):.1f}%{Style.RESET_ALL}",
                f"{Fore.GREEN}{bullish_count}{Style.RESET_ALL}",
                f"{Fore.RED}{bearish_count}{Style.RESET_ALL}",
                f"{Fore.YELLOW}{neutral_count}{Style.RESET_ALL}",
            ]
        )

    headers = [
        f"{Fore.WHITE}股票代码",
        f"{Fore.WHITE}操作",
        f"{Fore.WHITE}数量",
        f"{Fore.WHITE}置信度",
        f"{Fore.WHITE}看涨",
        f"{Fore.WHITE}看跌",
        f"{Fore.WHITE}中性",
    ]

    # 打印组合摘要表
    print(
        tabulate(
            portfolio_data,
            headers=headers,
            tablefmt="grid",
            colalign=("left", "center", "right", "right", "center", "center", "center"),
        )
    )

    # 打印组合管理代理的推理（如果可用）
    if portfolio_manager_reasoning:
        # 处理不同类型的推理（字符串、字典等）
        reasoning_str = ""
        if isinstance(portfolio_manager_reasoning, str):
            reasoning_str = portfolio_manager_reasoning
        elif isinstance(portfolio_manager_reasoning, dict):
            # 将字典转换为字符串表示
            reasoning_str = json.dumps(portfolio_manager_reasoning, indent=2)
        else:
            # 将其他类型转换为字符串
            reasoning_str = str(portfolio_manager_reasoning)

        # 换行长文本使其更易读
        wrapped_reasoning = ""
        current_line = ""
        # 使用固定宽度60字符以匹配表格列宽
        max_line_length = 60
        for word in reasoning_str.split():
            if len(current_line) + len(word) + 1 > max_line_length:
                wrapped_reasoning += current_line + "\n"
                current_line = word
            else:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
        if current_line:
            wrapped_reasoning += current_line

        print(f"\n{Fore.WHITE}{Style.BRIGHT}投资策略：{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{wrapped_reasoning}{Style.RESET_ALL}")


def print_backtest_results(table_rows: list) -> None:
    """以格式化表格打印回测结果"""
    # 清屏
    os.system("cls" if os.name == "nt" else "clear")

    # 将行分为股票行和摘要行
    ticker_rows = []
    summary_rows = []

    for row in table_rows:
        if isinstance(row[1], str) and "投资组合摘要" in row[1]:
            summary_rows.append(row)
        else:
            ticker_rows.append(row)

    # 显示最新的投资组合摘要
    if summary_rows:
        # 按日期选择最近的摘要（YYYY-MM-DD）
        latest_summary = max(summary_rows, key=lambda r: r[0])
        print(f"\n{Fore.WHITE}{Style.BRIGHT}投资组合摘要：{Style.RESET_ALL}")

        # 添加长/短股份后的调整索引
        position_str = latest_summary[7].split("$")[1].split(Style.RESET_ALL)[0].replace(",", "")
        cash_str     = latest_summary[8].split("$")[1].split(Style.RESET_ALL)[0].replace(",", "")
        total_str    = latest_summary[9].split("$")[1].split(Style.RESET_ALL)[0].replace(",", "")

        print(f"现金余额：{Fore.CYAN}${float(cash_str):,.2f}{Style.RESET_ALL}")
        print(f"持仓总值：{Fore.YELLOW}${float(position_str):,.2f}{Style.RESET_ALL}")
        print(f"账户总值：{Fore.WHITE}${float(total_str):,.2f}{Style.RESET_ALL}")
        print(f"组合收益率：{latest_summary[10]}")
        if len(latest_summary) > 14 and latest_summary[14]:
            print(f"基准收益率：{latest_summary[14]}")

        # 显示绩效指标（如果可用）
        if latest_summary[11]:  # 夏普比率
            print(f"夏普比率：{latest_summary[11]}")
        if latest_summary[12]:  # 索提诺比率
            print(f"索提诺比率：{latest_summary[12]}")
        if latest_summary[13]:  # 最大回撤
            print(f"最大回撤：{latest_summary[13]}")

    # 添加垂直间距
    print("\n" * 2)

    # 只打印股票行的表格
    print(
        tabulate(
            ticker_rows,
            headers=[
                "日期",
                "股票代码",
                "操作",
                "数量",
                "价格",
                "多头股份",
                "空头股份",
                "持仓价值",
            ],
            tablefmt="grid",
            colalign=(
                "left",    # 日期
                "left",    # 股票代码
                "center",  # 操作
                "right",   # 数量
                "right",   # 价格
                "right",   # 多头股份
                "right",   # 空头股份
                "right",   # 持仓价值
            ),
        )
    )

    # 添加垂直间距
    print("\n" * 4)


def format_backtest_row(
    date: str,
    ticker: str,
    action: str,
    quantity: float,
    price: float,
    long_shares: float = 0,
    short_shares: float = 0,
    position_value: float = 0,
    is_summary: bool = False,
    total_value: float = None,
    return_pct: float = None,
    cash_balance: float = None,
    total_position_value: float = None,
    sharpe_ratio: float = None,
    sortino_ratio: float = None,
    max_drawdown: float = None,
    benchmark_return_pct: float | None = None,
) -> list[any]:
    """格式化回测结果表格的行"""
    # 为操作着色
    action_color = {
        "BUY": Fore.GREEN,
        "COVER": Fore.GREEN,
        "SELL": Fore.RED,
        "SHORT": Fore.RED,
        "HOLD": Fore.WHITE,
    }.get(action.upper(), Fore.WHITE)

    if is_summary:
        return_color = Fore.GREEN if return_pct >= 0 else Fore.RED
        benchmark_str = ""
        if benchmark_return_pct is not None:
            bench_color = Fore.GREEN if benchmark_return_pct >= 0 else Fore.RED
            benchmark_str = f"{bench_color}{benchmark_return_pct:+.2f}%{Style.RESET_ALL}"
        return [
            date,
            f"{Fore.WHITE}{Style.BRIGHT}投资组合摘要{Style.RESET_ALL}",
            "",  # 操作
            "",  # 数量
            "",  # 价格
            "",  # 多头股份
            "",  # 空头股份
            f"{Fore.YELLOW}${total_position_value:,.2f}{Style.RESET_ALL}",  # 持仓总值
            f"{Fore.CYAN}${cash_balance:,.2f}{Style.RESET_ALL}",  # 现金余额
            f"{Fore.WHITE}${total_value:,.2f}{Style.RESET_ALL}",  # 账户总值
            f"{return_color}{return_pct:+.2f}%{Style.RESET_ALL}",  # 收益率
            f"{Fore.YELLOW}{sharpe_ratio:.2f}{Style.RESET_ALL}" if sharpe_ratio is not None else "",  # 夏普比率
            f"{Fore.YELLOW}{sortino_ratio:.2f}{Style.RESET_ALL}" if sortino_ratio is not None else "",  # 索提诺比率
            f"{Fore.RED}{max_drawdown:.2f}%{Style.RESET_ALL}" if max_drawdown is not None else "",  # 最大回撤（带符号）
            benchmark_str,  # 基准（沪深300）
        ]
    else:
        return [
            date,
            f"{Fore.CYAN}{ticker}{Style.RESET_ALL}",
            f"{action_color}{action.upper()}{Style.RESET_ALL}",
            f"{action_color}{quantity:,.0f}{Style.RESET_ALL}",
            f"{Fore.WHITE}{price:,.2f}{Style.RESET_ALL}",
            f"{Fore.GREEN}{long_shares:,.0f}{Style.RESET_ALL}",   # 多头股份
            f"{Fore.RED}{short_shares:,.0f}{Style.RESET_ALL}",    # 空头股份
            f"{Fore.YELLOW}{position_value:,.2f}{Style.RESET_ALL}",
        ]
