"""
港股通数据模块

支持港股通相关数据获取：
1. 港股通标的列表
2. 港股通资金流向
3. AH股溢价
4. 港股实时行情
"""

import subprocess
import json
import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class HKStockQuote:
    """港股行情数据"""
    code: str
    name: str
    price: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    volume: int
    amount: float
    prev_close: float


@dataclass
class HKTongueFlow:
    """港股通资金流向"""
    date: str
    sh_tongue_buy: float  # 沪港通买入（亿元）
    sh_tongue_sell: float  # 沪港通卖出（亿元）
    sz_tongue_buy: float  # 深港通买入（亿元）
    sz_tongue_sell: float  # 深港通卖出（亿元）
    total_net_buy: float  # 总净买入（亿元）


@dataclass
class AHPremium:
    """AH股溢价数据"""
    a_code: str
    a_name: str
    a_price: float
    h_code: str
    h_name: str
    h_price: float
    premium_rate: float  # 溢价率（%）
    exchange_rate: float  # 汇率


def fetch_via_powershell(url: str, timeout: int = 30) -> Optional[str]:
    """使用PowerShell获取URL内容"""
    ps_script = f'''
try {{
    $response = Invoke-WebRequest -Uri "{url}" -TimeoutSec {timeout} -UseBasicParsing -ErrorAction Stop
    $response.Content
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
            logger.error(f"PowerShell请求失败: {result.stderr}")
            return None

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        logger.error(f"PowerShell请求超时: {url}")
        return None
    except Exception as e:
        logger.error(f"PowerShell请求异常: {e}")
        return None


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
            logger.error(f"PowerShell JSON请求失败: {result.stderr}")
            return None

        return json.loads(result.stdout)

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        return None
    except Exception as e:
        logger.error(f"PowerShell请求异常: {e}")
        return None


class HKTongueAPI:
    """港股通数据API"""

    # 港股通热门标的
    HK_TONGUE_HOT_STOCKS = [
        "00700",  # 腾讯控股
        "09988",  # 阿里巴巴-SW
        "03690",  # 美团-W
        "09999",  # 网易-S
        "01810",  # 小米集团-W
        "02318",  # 平安好医生
        "00285",  # 比亚迪电子
        "01211",  # 比亚迪股份
        "02313",  # 申洲国际
        "02269",  # 药明生物
        "01024",  # 快手-W
        "09618",  # 京东集团-SW
        "02015",  # 理想汽车-W
        "09868",  # 小鹏汽车-W
        "06618",  # 京东健康
    ]

    @staticmethod
    def get_hk_tongue_flow(days: int = 30) -> List[HKTongueFlow]:
        """
        获取港股通资金流向

        参数:
            days: 获取天数
        """
        url = f"https://push2his.eastmoney.com/api/qt/stock/fflow/kline/get?secid=116.HKSC&lmt={days}&klt=101&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57"

        data = fetch_json_via_powershell(url)
        if not data or 'data' not in data or 'klines' not in data['data']:
            return []

        flows = []
        for line in data['data']['klines']:
            try:
                parts = line.split(',')
                flows.append(HKTongueFlow(
                    date=parts[0],
                    sh_tongue_buy=float(parts[1]) / 100000000 if len(parts) > 1 else 0,
                    sh_tongue_sell=float(parts[2]) / 100000000 if len(parts) > 2 else 0,
                    sz_tongue_buy=float(parts[3]) / 100000000 if len(parts) > 3 else 0,
                    sz_tongue_sell=float(parts[4]) / 100000000 if len(parts) > 4 else 0,
                    total_net_buy=float(parts[5]) / 100000000 if len(parts) > 5 else 0,
                ))
            except Exception as e:
                logger.warning(f"解析港股通流向数据失败: {e}")
                continue

        return flows

    @staticmethod
    def get_ah_premium() -> List[AHPremium]:
        """获取AH股溢价数据"""
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_AH_LIST&columns=ALL&filter=(MARKET_CODE%3D%221%22)&pageSize=100&pageNumber=1"

        data = fetch_json_via_powershell(url)
        if not data or 'result' not in data or 'data' not in data['result']:
            return []

        premiums = []
        for item in data['result']['data']:
            try:
                premiums.append(AHPremium(
                    a_code=str(item.get('A_CODE', '')),
                    a_name=str(item.get('A_NAME', '')),
                    a_price=float(item.get('A_PRICE', 0)),
                    h_code=str(item.get('H_CODE', '')),
                    h_name=str(item.get('H_NAME', '')),
                    h_price=float(item.get('H_PRICE', 0)),
                    premium_rate=float(item.get('PREMIUM_RATE', 0)),
                    exchange_rate=float(item.get('EXCHANGE_RATE', 1)),
                ))
            except Exception as e:
                logger.warning(f"解析AH溢价数据失败: {e}")
                continue

        return premiums

    @staticmethod
    def get_hk_stock_quote(code: str) -> Optional[HKStockQuote]:
        """
        获取港股行情

        参数:
            code: 港股代码（如00700）
        """
        # 腾讯港股API
        url = f"https://web.sqt.gtimg.cn/q=hk{code}"

        data = fetch_via_powershell(url)
        if not data:
            return None

        try:
            # 解析腾讯数据格式
            match = re.search(r'"([^"]+)"', data)
            if not match:
                return None

            parts = match.group(1).split('~')
            if len(parts) < 30:
                return None

            return HKStockQuote(
                code=code,
                name=parts[1],
                price=float(parts[3]) if parts[3] else 0,
                change=float(parts[31]) if len(parts) > 31 and parts[31] else 0,
                change_pct=float(parts[32]) if len(parts) > 32 and parts[32] else 0,
                open=float(parts[5]) if parts[5] else 0,
                high=float(parts[33]) if len(parts) > 33 and parts[33] else 0,
                low=float(parts[34]) if len(parts) > 34 and parts[34] else 0,
                volume=int(parts[6]) if parts[6] else 0,
                amount=float(parts[37]) if len(parts) > 37 and parts[37] else 0,
                prev_close=float(parts[4]) if parts[4] else 0,
            )

        except Exception as e:
            logger.error(f"解析港股行情失败: {e}")
            return None

    @staticmethod
    def get_hk_stock_quotes(codes: List[str]) -> Dict[str, HKStockQuote]:
        """
        批量获取港股行情

        参数:
            codes: 港股代码列表
        """
        symbols = [f"hk{code}" for code in codes]
        url = f"https://web.sqt.gtimg.cn/q={','.join(symbols)}"

        data = fetch_via_powershell(url)
        if not data:
            return {}

        results = {}
        lines = data.strip().split('\n')

        for line in lines:
            try:
                match = re.match(r'v_hk(\d+)=', line)
                if match:
                    code = match.group(1)
                    quote_match = re.search(r'"([^"]+)"', line)
                    if quote_match:
                        parts = quote_match.group(1).split('~')
                        if len(parts) >= 30:
                            results[code] = HKStockQuote(
                                code=code,
                                name=parts[1],
                                price=float(parts[3]) if parts[3] else 0,
                                change=float(parts[31]) if len(parts) > 31 and parts[31] else 0,
                                change_pct=float(parts[32]) if len(parts) > 32 and parts[32] else 0,
                                open=float(parts[5]) if parts[5] else 0,
                                high=float(parts[33]) if len(parts) > 33 and parts[33] else 0,
                                low=float(parts[34]) if len(parts) > 34 and parts[34] else 0,
                                volume=int(parts[6]) if parts[6] else 0,
                                amount=float(parts[37]) if len(parts) > 37 and parts[37] else 0,
                                prev_close=float(parts[4]) if parts[4] else 0,
                            )
            except Exception as e:
                logger.warning(f"解析港股行情失败: {e}")
                continue

        return results

    @staticmethod
    def get_hk_tongue_stocks() -> List[Dict]:
        """获取港股通标的列表"""
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_HK_LIST&columns=ALL&pageSize=500&pageNumber=1"

        data = fetch_json_via_powershell(url)
        if not data or 'result' not in data or 'data' not in data['result']:
            return []

        stocks = []
        for item in data['result']['data']:
            try:
                stocks.append({
                    'code': str(item.get('CODE', '')),
                    'name': str(item.get('NAME', '')),
                    'price': float(item.get('NEW_PRICE', 0)),
                    'change_pct': float(item.get('CHG_PCT', 0)),
                    'volume': float(item.get('VOLUME', 0)),
                    'amount': float(item.get('TURNOVER', 0)),
                    'market_cap': float(item.get('MARKET_VALUE', 0)),
                })
            except Exception as e:
                logger.warning(f"解析港股通标的数据失败: {e}")
                continue

        return stocks


if __name__ == "__main__":
    print("测试港股通API...")

    # 测试港股通资金流向
    flows = HKTongueAPI.get_hk_tongue_flow(days=5)
    print(f"\n获取到 {len(flows)} 天港股通流向数据")
    if flows:
        print(f"最新: {flows[0].date} 净买入: {flows[0].total_net_buy:.2f}亿")

    # 测试港股行情
    quote = HKTongueAPI.get_hk_stock_quote("00700")
    if quote:
        print(f"\n腾讯控股: {quote.price} 港币, 涨跌: {quote.change_pct:+.2f}%")

    # 测试AH溢价
    premiums = HKTongueAPI.get_ah_premium()
    print(f"\n获取到 {len(premiums)} 只AH股溢价数据")
