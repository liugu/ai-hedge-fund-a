"""
ETF数据模块

支持ETF相关数据：
1. ETF列表和行情
2. ETF持仓数据
3. ETF资金流向
4. ETF套利分析
"""

import subprocess
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ETFQuote:
    """ETF行情"""
    code: str
    name: str
    price: float
    change_pct: float
    volume: int
    amount: float
    premium_rate: float  # 溢价率
    nav: float  # 净值
    tracking_error: Optional[float] = None


@dataclass
class ETFFundFlow:
    """ETF资金流向"""
    code: str
    name: str
    date: str
    net_inflow: float  # 净流入（亿元）
    shares_change: int  # 份额变化
    total_shares: int  # 总份额


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


class ETFAPI:
    """ETF数据API"""

    # 热门ETF
    HOT_ETFS = {
        "510050": {"name": "50ETF", "type": "宽基"},
        "510300": {"name": "300ETF", "type": "宽基"},
        "510500": {"name": "500ETF", "type": "宽基"},
        "159915": {"name": "创业板ETF", "type": "宽基"},
        "588000": {"name": "科创50ETF", "type": "宽基"},
        "512880": {"name": "证券ETF", "type": "行业"},
        "512690": {"name": "酒ETF", "type": "行业"},
        "159996": {"name": "芯片ETF", "type": "行业"},
        "515790": {"name": "光伏ETF", "type": "行业"},
        "512480": {"name": "半导体ETF", "type": "行业"},
        "159766": {"name": "旅游ETF", "type": "行业"},
        "512660": {"name": "军工ETF", "type": "行业"},
        "515180": {"name": "银行ETF", "type": "行业"},
        "159949": {"name": "创业板50ETF", "type": "宽基"},
        "588200": {"name": "科创板50ETF", "type": "宽基"},
    }

    @staticmethod
    def get_etf_list(category: str = None) -> List[Dict]:
        """
        获取ETF列表

        参数:
            category: ETF类别 (宽基/行业/主题/跨境)
        """
        url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:1+t:2,m:1+t:23&fields=f1,f2,f3,f4,f5,f6,f12,f14"

        data = fetch_json_via_powershell(url)
        if not data or 'data' not in data or 'diff' not in data['data']:
            return []

        etfs = []
        for item in data['data']['diff']:
            try:
                etfs.append({
                    "code": str(item.get('f12', '')),
                    "name": str(item.get('f14', '')),
                    "price": float(item.get('f2', 0)),
                    "change_pct": float(item.get('f3', 0)),
                    "volume": int(item.get('f5', 0)),
                    "amount": float(item.get('f6', 0)),
                })
            except Exception as e:
                logger.warning(f"解析ETF数据失败: {e}")
                continue

        return etfs

    @staticmethod
    def get_etf_quote(code: str) -> Optional[ETFQuote]:
        """
        获取ETF行情

        参数:
            code: ETF代码
        """
        # 确定市场代码
        if code.startswith('5'):
            market = '1'
        else:
            market = '0'

        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={market}.{code}&fields=f1,f2,f3,f4,f5,f6,f12,f14,f124,f125"

        data = fetch_json_via_powershell(url)
        if not data or 'data' not in data:
            return None

        try:
            item = data['data']
            return ETFQuote(
                code=code,
                name=str(item.get('f14', '')),
                price=float(item.get('f2', 0)),
                change_pct=float(item.get('f3', 0)),
                volume=int(item.get('f5', 0)),
                amount=float(item.get('f6', 0)),
                premium_rate=0,  # 需要额外计算
                nav=float(item.get('f125', 0)) if item.get('f125') else float(item.get('f2', 0)),
            )
        except Exception as e:
            logger.error(f"解析ETF行情失败: {e}")
            return None

    @staticmethod
    def get_etf_fund_flow(code: str, days: int = 30) -> List[ETFFundFlow]:
        """
        获取ETF资金流向

        参数:
            code: ETF代码
            days: 获取天数
        """
        url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_ETF_LIST&columns=ALL&filter=(SECURITY_CODE%3D%22{code}%22)&pageSize={days}&pageNumber=1"

        data = fetch_json_via_powershell(url)
        if not data or 'result' not in data or 'data' not in data['result']:
            return []

        flows = []
        for item in data['result']['data']:
            try:
                flows.append(ETFFundFlow(
                    code=code,
                    name=str(item.get('SECURITY_NAME_ABBR', '')),
                    date=str(item.get('TRADE_DATE', '')),
                    net_inflow=float(item.get('NET_INFLOW', 0)) / 100000000,
                    shares_change=int(item.get('SHARES_CHANGE', 0)),
                    total_shares=int(item.get('TOTAL_SHARES', 0)),
                ))
            except Exception as e:
                logger.warning(f"解析ETF资金流向失败: {e}")
                continue

        return flows

    @staticmethod
    def get_etf_holdings(code: str) -> List[Dict]:
        """
        获取ETF持仓

        参数:
            code: ETF代码
        """
        url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_ETF_HOLDS_DETAIL&columns=ALL&filter=(ETF_CODE%3D%22{code}%22)&pageSize=50&pageNumber=1"

        data = fetch_json_via_powershell(url)
        if not data or 'result' not in data or 'data' not in data['result']:
            return []

        holdings = []
        for item in data['result']['data']:
            try:
                holdings.append({
                    "ticker": str(item.get('STOCK_CODE', '')),
                    "name": str(item.get('STOCK_NAME', '')),
                    "shares": int(item.get('HOLD_SHARES', 0)),
                    "value": float(item.get('HOLD_VALUE', 0)),
                    "weight": float(item.get('HOLD_RATIO', 0)),
                })
            except Exception as e:
                logger.warning(f"解析ETF持仓失败: {e}")
                continue

        return holdings

    @staticmethod
    def analyze_etf_arbitrage(code: str) -> Dict:
        """
        分析ETF套利机会

        参数:
            code: ETF代码
        """
        quote = ETFAPI.get_etf_quote(code)
        if not quote:
            return {"opportunity": False, "reasoning": "无法获取ETF行情"}

        # 计算溢价率
        if quote.nav > 0:
            premium_rate = (quote.price - quote.nav) / quote.nav * 100
        else:
            premium_rate = 0

        # 判断套利机会
        if premium_rate > 2:
            return {
                "opportunity": True,
                "direction": "sell",
                "reasoning": f"ETF溢价{premium_rate:.2f}%，可考虑申购ETF份额后卖出套利",
                "premium_rate": premium_rate,
            }
        elif premium_rate < -2:
            return {
                "opportunity": True,
                "direction": "buy",
                "reasoning": f"ETF折价{abs(premium_rate):.2f}%，可考虑买入ETF后赎回套利",
                "premium_rate": premium_rate,
            }
        else:
            return {
                "opportunity": False,
                "reasoning": f"ETF溢价率{premium_rate:.2f}%，套利空间有限",
                "premium_rate": premium_rate,
            }

    @staticmethod
    def get_top_inflow_etfs(top_n: int = 10) -> List[Dict]:
        """
        获取资金流入最多的ETF

        参数:
            top_n: 返回数量
        """
        url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_ETF_LIST&columns=ALL&pageSize={top_n}&pageNumber=1&sortTypes=-1&sortColumns=NET_INFLOW"

        data = fetch_json_via_powershell(url)
        if not data or 'result' not in data or 'data' not in data['result']:
            return []

        etfs = []
        for item in data['result']['data']:
            try:
                etfs.append({
                    "code": str(item.get('SECURITY_CODE', '')),
                    "name": str(item.get('SECURITY_NAME_ABBR', '')),
                    "net_inflow": float(item.get('NET_INFLOW', 0)) / 100000000,
                    "change_pct": float(item.get('CHG_PCT', 0)),
                })
            except Exception as e:
                logger.warning(f"解析ETF流入数据失败: {e}")
                continue

        return etfs


if __name__ == "__main__":
    print("测试ETF API...")

    # 测试ETF行情
    quote = ETFAPI.get_etf_quote("510050")
    if quote:
        print(f"\n50ETF: {quote.price:.3f}, 涨跌: {quote.change_pct:+.2f}%")

    # 测试资金流向
    flows = ETFAPI.get_etf_fund_flow("510300", days=5)
    print(f"\n300ETF资金流向: {len(flows)}天")
    if flows:
        for f in flows[:3]:
            print(f"  {f.date}: 净流入 {f.net_inflow:.2f}亿")

    # 测试套利分析
    arb = ETFAPI.analyze_etf_arbitrage("510050")
    print(f"\n套利分析: {arb['reasoning']}")

    # 测试热门ETF流入
    top_etfs = ETFAPI.get_top_inflow_etfs(5)
    print(f"\n资金流入TOP5 ETF:")
    for etf in top_etfs:
        print(f"  {etf['code']} {etf['name']}: {etf['net_inflow']:.2f}亿")