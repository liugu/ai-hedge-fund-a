"""
融资融券数据模块

支持融资融券相关数据：
1. 融资融券余额
2. 个股融资融券数据
3. 融资融券交易明细
"""

import subprocess
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class MarginTradingData:
    """融资融券数据"""
    ticker: str
    name: str
    date: str
    # 融资数据
    financing_balance: float  # 融资余额（亿元）
    financing_buy: float  # 融资买入额（亿元）
    financing_repay: float  # 融资偿还额（亿元）
    # 融券数据
    margin_balance: float  # 融券余额（亿元）
    margin_sell: float  # 融券卖出额（亿元）
    margin_repay: float  # 融券偿还额（亿元）
    # 合计
    total_balance: float  # 融资融券余额（亿元）


@dataclass
class MarginTradingSummary:
    """融资融券汇总"""
    date: str
    market_financing_balance: float  # 市场融资余额（亿元）
    market_margin_balance: float  # 市场融券余额（亿元）
    market_total_balance: float  # 市场融资融券余额（亿元）
    financing_net_buy: float  # 融资净买入（亿元）
    margin_net_sell: float  # 融券净卖出（亿元）


def fetch_json_via_powershell(url: str, timeout: int = 30) -> Optional[Dict]:
    """使用PowerShell获取JSON数据"""
    ps_script = f'''
try {{
    $response = Invoke-RestMethod -Uri "{url}" -TimeoutSec {timeout} -ErrorAction Stop
    $response | ConvertTo-Json -Depth 10
}} catch {{
    Write-Error $_.Exception.Message
    exit 1
}}
'''

    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=timeout + 10,
            encoding='utf-8'
        )

        if result.returncode != 0:
            return None

        return json.loads(result.stdout)

    except Exception as e:
        logger.error(f"PowerShell请求失败: {e}")
        return None


class MarginTradingAPI:
    """融资融券数据API"""

    @staticmethod
    def get_market_margin_summary(days: int = 30) -> List[MarginTradingSummary]:
        """
        获取市场融资融券汇总

        参数:
            days: 获取天数
        """
        url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_RZRQ_LSHJ&columns=ALL&pageSize={days}&pageNumber=1"

        data = fetch_json_via_powershell(url)
        if not data or 'result' not in data or 'data' not in data['result']:
            return []

        summaries = []
        for item in data['result']['data']:
            try:
                summaries.append(MarginTradingSummary(
                    date=str(item.get('TRADE_DATE', '')),
                    market_financing_balance=float(item.get('RZYE', 0)) / 100000000,
                    market_margin_balance=float(item.get('RQYE', 0)) / 100000000,
                    market_total_balance=float(item.get('RZRQYE', 0)) / 100000000,
                    financing_net_buy=float(item.get('RZMRE', 0)) / 100000000,
                    margin_net_sell=float(item.get('RQMCL', 0)) / 100000000,
                ))
            except Exception as e:
                logger.warning(f"解析融资融券汇总数据失败: {e}")
                continue

        return summaries

    @staticmethod
    def get_stock_margin_data(ticker: str, days: int = 30) -> List[MarginTradingData]:
        """
        获取个股融资融券数据

        参数:
            ticker: 股票代码
            days: 获取天数
        """
        # 确定市场代码
        if ticker.startswith('6'):
            market = '1'
        else:
            market = '0'

        url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_RZRQ_LSHJ_MX&columns=ALL&filter=(SECURITY_CODE%3D%22{ticker}%22)&pageSize={days}&pageNumber=1"

        data = fetch_json_via_powershell(url)
        if not data or 'result' not in data or 'data' not in data['result']:
            return []

        margin_data = []
        for item in data['result']['data']:
            try:
                margin_data.append(MarginTradingData(
                    ticker=ticker,
                    name=str(item.get('SECURITY_NAME_ABBR', '')),
                    date=str(item.get('TRADE_DATE', '')),
                    financing_balance=float(item.get('RZYE', 0)) / 100000000,
                    financing_buy=float(item.get('RZMRE', 0)) / 100000000,
                    financing_repay=float(item.get('RZCHE', 0)) / 100000000,
                    margin_balance=float(item.get('RQYE', 0)) / 100000000,
                    margin_sell=float(item.get('RQMCL', 0)) / 100000000,
                    margin_repay=float(item.get('RQCHL', 0)) / 100000000,
                    total_balance=float(item.get('RZRQYE', 0)) / 100000000,
                ))
            except Exception as e:
                logger.warning(f"解析个股融资融券数据失败: {e}")
                continue

        return margin_data

    @staticmethod
    def analyze_margin_trend(margin_data: List[MarginTradingData]) -> Dict:
        """
        分析融资融券趋势

        参数:
            margin_data: 融资融券数据列表
        """
        if not margin_data or len(margin_data) < 2:
            return {"trend": "unknown", "reasoning": "数据不足"}

        # 按日期排序
        margin_data.sort(key=lambda x: x.date)

        # 计算变化
        latest = margin_data[-1]
        previous = margin_data[-2]

        financing_change = latest.financing_balance - previous.financing_balance
        margin_change = latest.margin_balance - previous.margin_balance

        # 判断趋势
        signals = []

        # 融资趋势
        if financing_change > 0:
            signals.append(f"融资余额增加{financing_change:.2f}亿")
            financing_trend = "bullish"
        else:
            signals.append(f"融资余额减少{abs(financing_change):.2f}亿")
            financing_trend = "bearish"

        # 融券趋势
        if margin_change > 0:
            signals.append(f"融券余额增加{margin_change:.2f}亿")
            margin_trend = "bearish"  # 融券增加通常是看空
        else:
            signals.append(f"融券余额减少{abs(margin_change):.2f}亿")
            margin_trend = "bullish"

        # 综合判断
        if financing_trend == "bullish" and margin_trend == "bullish":
            trend = "bullish"
            confidence = 70
        elif financing_trend == "bearish" and margin_trend == "bearish":
            trend = "bearish"
            confidence = 70
        else:
            trend = "neutral"
            confidence = 50

        # 计算5日变化趋势
        if len(margin_data) >= 5:
            five_day_ago = margin_data[-5]
            five_day_change = latest.financing_balance - five_day_ago.financing_balance
            if five_day_change > 0:
                signals.append(f"5日融资净增加{five_day_change:.2f}亿")
            else:
                signals.append(f"5日融资净减少{abs(five_day_change):.2f}亿")

        return {
            "trend": trend,
            "confidence": confidence,
            "reasoning": "；".join(signals),
            "financing_balance": latest.financing_balance,
            "margin_balance": latest.margin_balance,
            "total_balance": latest.total_balance,
        }

    @staticmethod
    def get_top_financing_stocks(top_n: int = 20) -> List[Dict]:
        """
        获取融资余额最多的股票

        参数:
            top_n: 返回数量
        """
        url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_RZRQ_LSHJ_MX&columns=ALL&pageSize={top_n}&pageNumber=1&sortTypes=-1&sortColumns=RZYE"

        data = fetch_json_via_powershell(url)
        if not data or 'result' not in data or 'data' not in data['result']:
            return []

        stocks = []
        for item in data['result']['data']:
            try:
                stocks.append({
                    "ticker": str(item.get('SECURITY_CODE', '')),
                    "name": str(item.get('SECURITY_NAME_ABBR', '')),
                    "financing_balance": float(item.get('RZYE', 0)) / 100000000,
                    "margin_balance": float(item.get('RQYE', 0)) / 100000000,
                    "total_balance": float(item.get('RZRQYE', 0)) / 100000000,
                })
            except Exception as e:
                logger.warning(f"解析融资余额数据失败: {e}")
                continue

        return stocks


if __name__ == "__main__":
    print("测试融资融券API...")

    # 测试市场汇总
    summaries = MarginTradingAPI.get_market_margin_summary(days=5)
    print(f"\n市场融资融券汇总: {len(summaries)}天")
    if summaries:
        latest = summaries[0]
        print(f"  融资余额: {latest.market_financing_balance:.2f}亿")
        print(f"  融券余额: {latest.market_margin_balance:.2f}亿")
        print(f"  合计: {latest.market_total_balance:.2f}亿")

    # 测试个股数据
    margin_data = MarginTradingAPI.get_stock_margin_data("600519", days=5)
    print(f"\n贵州茅台融资融券: {len(margin_data)}天")
    if margin_data:
        latest = margin_data[0]
        print(f"  融资余额: {latest.financing_balance:.2f}亿")
        print(f"  融券余额: {latest.margin_balance:.2f}亿")

        # 分析趋势
        analysis = MarginTradingAPI.analyze_margin_trend(margin_data)
        print(f"\n趋势分析: {analysis['trend']}")
        print(f"理由: {analysis['reasoning']}")