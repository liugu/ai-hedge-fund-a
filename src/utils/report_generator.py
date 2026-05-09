"""
分析报告生成器

生成完整的分析报告：
1. 个股分析报告
2. 市场分析报告
3. 组合分析报告
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import asdict

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        self.report_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def generate_stock_report(self, ticker: str, analysis_data: Dict) -> str:
        """
        生成个股分析报告

        参数:
            ticker: 股票代码
            analysis_data: 分析数据
        """
        report = f"""
{'='*60}
个股分析报告
{'='*60}

股票: {ticker} {analysis_data.get('name', '')}
行业: {analysis_data.get('sector', '')}
报告时间: {self.report_time}

{'='*60}
一、行情概况
{'='*60}

当前价格: {analysis_data.get('price', 0):.2f}
今日涨跌: {analysis_data.get('change_pct', 0):+.2f}%
成交量: {analysis_data.get('volume', 0):,}
成交额: {analysis_data.get('amount', 0):,.0f}万

{'='*60}
二、技术分析
{'='*60}
"""
        technical = analysis_data.get('technical', {})
        if technical:
            report += f"""
趋势判断: {technical.get('trend', 'N/A')}
信号强度: {technical.get('strength', 0)}%

MACD: {technical.get('macd', 'N/A')}
KDJ: K={technical.get('kdj_k', 'N/A')}, D={technical.get('kdj_d', 'N/A')}, J={technical.get('kdj_j', 'N/A')}
RSI(12): {technical.get('rsi_12', 'N/A')}

均线系统:
  MA5: {technical.get('ma5', 'N/A')}
  MA10: {technical.get('ma10', 'N/A')}
  MA20: {technical.get('ma20', 'N/A')}
"""
        else:
            report += "\n暂无技术分析数据\n"

        report += f"""
{'='*60}
三、资金流向
{'='*60}
"""
        fund_flow = analysis_data.get('fund_flow', {})
        if fund_flow:
            report += f"""
主力净流入: {fund_flow.get('main_net_inflow', 0):.0f}万
超大单净流入: {fund_flow.get('super_net_inflow', 0):.0f}万
大单净流入: {fund_flow.get('big_net_inflow', 0):.0f}万
中单净流入: {fund_flow.get('medium_net_inflow', 0):.0f}万
小单净流入: {fund_flow.get('small_net_inflow', 0):.0f}万

资金流向信号: {fund_flow.get('signal', 'N/A')}
"""
        else:
            report += "\n暂无资金流向数据\n"

        report += f"""
{'='*60}
四、基本面
{'='*60}
"""
        fundamentals = analysis_data.get('fundamentals', {})
        if fundamentals:
            report += f"""
市盈率(PE): {fundamentals.get('pe', 'N/A')}
市净率(PB): {fundamentals.get('pb', 'N/A')}
净资产收益率(ROE): {fundamentals.get('roe', 'N/A')}
毛利率: {fundamentals.get('gross_margin', 'N/A')}
"""
        else:
            report += "\n暂无基本面数据\n"

        report += f"""
{'='*60}
五、综合评估
{'='*60}

综合评分: {analysis_data.get('score', 0)}
投资信号: {analysis_data.get('signal', 'N/A')}
置信度: {analysis_data.get('confidence', 0)}%

投资建议: {analysis_data.get('recommendation', 'N/A')}

{'='*60}
免责声明: 以上分析仅供参考，不构成投资建议。
投资有风险，入市需谨慎。
{'='*60}
"""
        return report

    def generate_market_report(self, market_data: Dict) -> str:
        """
        生成市场分析报告

        参数:
            market_data: 市场数据
        """
        report = f"""
{'='*60}
市场分析报告
{'='*60}

报告时间: {self.report_time}

{'='*60}
一、市场概况
{'='*60}
"""
        overview = market_data.get('overview', {})
        if overview:
            report += f"""
上证指数: {overview.get('sh_index', 'N/A')} ({overview.get('sh_change', 0):+.2f}%)
深证成指: {overview.get('sz_index', 'N/A')} ({overview.get('sz_change', 0):+.2f}%)
创业板指: {overview.get('cyb_index', 'N/A')} ({overview.get('cyb_change', 0):+.2f}%)

上涨股票: {overview.get('advance', 0)} 只
下跌股票: {overview.get('decline', 0)} 只
涨停股票: {overview.get('limit_up', 0)} 只
跌停股票: {overview.get('limit_down', 0)} 只
"""
        else:
            report += "\n暂无市场概况数据\n"

        report += f"""
{'='*60}
二、市场情绪
{'='*60}
"""
        sentiment = market_data.get('sentiment', {})
        if sentiment:
            report += f"""
恐慌贪婪指数: {sentiment.get('fear_greed_index', 0):.1f}
情绪等级: {sentiment.get('sentiment_level', 'N/A')}
市场宽度: {sentiment.get('market_breadth', 0)*100:.1f}%

情绪信号: {sentiment.get('signal', 'N/A')}
理由: {sentiment.get('reasoning', 'N/A')}
"""
        else:
            report += "\n暂无市场情绪数据\n"

        report += f"""
{'='*60}
三、北向资金
{'='*60}
"""
        northbound = market_data.get('northbound', {})
        if northbound:
            report += f"""
今日净买入: {northbound.get('net_buy', 0):.2f} 亿元
5日净买入: {northbound.get('net_buy_5d', 0):.2f} 亿元
20日净买入: {northbound.get('net_buy_20d', 0):.2f} 亿元

资金趋势: {northbound.get('trend', 'N/A')}
"""
        else:
            report += "\n暂无北向资金数据\n"

        report += f"""
{'='*60}
四、板块表现
{'='*60}
"""
        sectors = market_data.get('sectors', [])
        if sectors:
            report += "\n领涨板块:\n"
            for s in sectors[:5]:
                report += f"  {s.get('name', '')}: {s.get('change_pct', 0):+.2f}%\n"

            report += "\n领跌板块:\n"
            for s in sectors[-5:]:
                report += f"  {s.get('name', '')}: {s.get('change_pct', 0):+.2f}%\n"
        else:
            report += "\n暂无板块数据\n"

        report += f"""
{'='*60}
免责声明: 以上分析仅供参考，不构成投资建议。
{'='*60}
"""
        return report

    def generate_portfolio_report(self, portfolio_data: Dict) -> str:
        """
        生成组合分析报告

        参数:
            portfolio_data: 组合数据
        """
        report = f"""
{'='*60}
投资组合分析报告
{'='*60}

报告时间: {self.report_time}

{'='*60}
一、组合概况
{'='*60}
"""
        summary = portfolio_data.get('summary', {})
        if summary:
            report += f"""
总资产: {summary.get('total_capital', 0):,.2f}
持仓市值: {summary.get('total_position_value', 0):,.2f}
现金余额: {summary.get('cash', 0):,.2f}
持仓数量: {summary.get('position_count', 0)} 只

总盈亏: {summary.get('total_profit_loss', 0):,.2f}
收益率: {summary.get('return_pct', 0)*100:.2f}%
"""
        else:
            report += "\n暂无组合概况数据\n"

        report += f"""
{'='*60}
二、持仓明细
{'='*60}
"""
        positions = portfolio_data.get('positions', [])
        if positions:
            for p in positions:
                report += f"""
{p.get('ticker', '')} {p.get('name', '')}
  持仓: {p.get('shares', 0)} 股
  成本: {p.get('cost_price', 0):.2f}
  现价: {p.get('current_price', 0):.2f}
  盈亏: {p.get('profit_loss_pct', 0):+.2f}%
  止损: {p.get('stop_loss', 0):.2f}
  止盈: {p.get('take_profit', 0):.2f}
"""
        else:
            report += "\n暂无持仓\n"

        report += f"""
{'='*60}
三、风险分析
{'='*60}
"""
        risk = portfolio_data.get('risk', {})
        if risk:
            report += f"""
总风险敞口: {risk.get('total_risk', 0):.2f}
持仓集中度: {risk.get('concentration', 0):.2f}
现金比例: {risk.get('cash_ratio', 0)*100:.1f}%

风险预警:
"""
            warnings = risk.get('warnings', [])
            if warnings:
                for w in warnings:
                    report += f"  - {w}\n"
            else:
                report += "  无\n"
        else:
            report += "\n暂无风险分析数据\n"

        report += f"""
{'='*60}
免责声明: 以上分析仅供参考，不构成投资建议。
{'='*60}
"""
        return report

    def save_report(self, report: str, filepath: str):
        """保存报告"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"报告已保存: {filepath}")

    def generate_json_report(self, data: Dict) -> str:
        """生成JSON格式报告"""
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)


if __name__ == "__main__":
    # 测试报告生成
    generator = ReportGenerator()

    # 测试个股报告
    stock_data = {
        "name": "贵州茅台",
        "sector": "白酒",
        "price": 1750.00,
        "change_pct": 1.5,
        "volume": 5000000,
        "amount": 875000,
        "technical": {
            "trend": "bullish",
            "strength": 75,
            "macd": 15.5,
            "kdj_k": 65,
            "kdj_d": 55,
            "kdj_j": 85,
            "rsi_12": 60,
            "ma5": 1740,
            "ma10": 1720,
            "ma20": 1700,
        },
        "fund_flow": {
            "main_net_inflow": 15000,
            "super_net_inflow": 8000,
            "big_net_inflow": 7000,
            "medium_net_inflow": -3000,
            "small_net_inflow": -12000,
            "signal": "主力流入",
        },
        "score": 75,
        "signal": "bullish",
        "confidence": 75,
        "recommendation": "建议关注，技术面看涨，主力资金流入",
    }

    report = generator.generate_stock_report("600519", stock_data)
    print(report)