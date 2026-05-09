"""
东方财富数据源 - 通过PowerShell获取数据
支持更多数据类型：K线、资金流向、龙虎榜等
"""

import subprocess
import json
import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class KLineData:
    """K线数据"""
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: int
    amount: float
    change_pct: float
    turnover_rate: float


@dataclass
class FundFlow:
    """资金流向数据"""
    ticker: str
    name: str
    main_net_inflow: float  # 主力净流入
    retail_net_inflow: float  # 散户净流入
    super_net_inflow: float  # 超大单净流入
    big_net_inflow: float  # 大单净流入
    medium_net_inflow: float  # 中单净流入
    small_net_inflow: float  # 小单净流入


@dataclass
class BlockTrade:
    """大宗交易数据"""
    ticker: str
    name: str
    date: str
    price: float
    volume: int
    amount: float
    buyer: str
    seller: str
    premium_rate: float  # 溢价率


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
    except subprocess.TimeoutExpired:
        logger.error(f"PowerShell请求超时: {url}")
        return None
    except Exception as e:
        logger.error(f"PowerShell请求异常: {e}")
        return None


class EastMoneyAPI:
    """东方财富数据API"""

    @staticmethod
    def get_kline_data(code: str, period: str = 'day', count: int = 100) -> List[KLineData]:
        """
        获取K线数据

        参数:
            code: 股票代码
            period: 周期 (day/week/month)
            count: 获取数量
        """
        # 确定市场代码
        if code.startswith('6'):
            secid = f"1.{code}"
        else:
            secid = f"0.{code}"

        # K线周期映射
        klt_map = {'day': '101', 'week': '102', 'month': '103'}
        klt = klt_map.get(period, '101')

        url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt={klt}&fqt=1&end=20500101&lmt={count}"

        data = fetch_json_via_powershell(url)
        if not data or 'data' not in data or 'klines' not in data['data']:
            return []

        klines = []
        for line in data['data']['klines']:
            try:
                parts = line.split(',')
                klines.append(KLineData(
                    date=parts[0],
                    open=float(parts[1]) if parts[1] else 0,
                    close=float(parts[2]) if parts[2] else 0,
                    high=float(parts[3]) if parts[3] else 0,
                    low=float(parts[4]) if parts[4] else 0,
                    volume=int(float(parts[5])) if parts[5] else 0,
                    amount=float(parts[6]) if parts[6] else 0,
                    change_pct=float(parts[7]) if len(parts) > 7 and parts[7] else 0,
                    turnover_rate=float(parts[8]) if len(parts) > 8 and parts[8] else 0,
                ))
            except Exception as e:
                logger.warning(f"解析K线数据失败: {e}")
                continue

        return klines

    @staticmethod
    def get_fund_flow(code: str) -> Optional[FundFlow]:
        """
        获取资金流向数据

        参数:
            code: 股票代码
        """
        # 确定市场代码
        if code.startswith('6'):
            secid = f"1.{code}"
        else:
            secid = f"0.{code}"

        url = f"https://push2.eastmoney.com/api/qt/stock/fflow/kline/get?secid={secid}&lmt=0&klt=101&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60"

        data = fetch_json_via_powershell(url)
        if not data or 'data' not in data:
            return None

        try:
            info = data['data'].get('info', {})
            flows = data['data'].get('klines', [])
            if not flows:
                return None

            # 获取最新一天的数据
            latest = flows[-1] if isinstance(flows, list) else flows
            if isinstance(latest, str):
                parts = latest.split(',')
                return FundFlow(
                    ticker=code,
                    name=info.get('name', ''),
                    main_net_inflow=float(parts[1]) if len(parts) > 1 else 0,
                    retail_net_inflow=float(parts[5]) if len(parts) > 5 else 0,
                    super_net_inflow=float(parts[1]) if len(parts) > 1 else 0,
                    big_net_inflow=float(parts[2]) if len(parts) > 2 else 0,
                    medium_net_inflow=float(parts[3]) if len(parts) > 3 else 0,
                    small_net_inflow=float(parts[4]) if len(parts) > 4 else 0,
                )
        except Exception as e:
            logger.error(f"解析资金流向失败: {e}")

        return None

    @staticmethod
    def get_sector_fund_flow() -> List[Dict]:
        """获取板块资金流向"""
        url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:2&fields=f1,f2,f3,f12,f14"

        data = fetch_json_via_powershell(url)
        if not data or 'data' not in data or 'diff' not in data['data']:
            return []

        sectors = []
        for item in data['data']['diff']:
            try:
                sectors.append({
                    'code': item.get('f12', ''),
                    'name': item.get('f14', ''),
                    'change_pct': item.get('f3', 0),
                    'net_inflow': item.get('f2', 0),
                })
            except Exception as e:
                logger.warning(f"解析板块数据失败: {e}")
                continue

        return sectors

    @staticmethod
    def get_block_trades(date: str = None) -> List[BlockTrade]:
        """
        获取大宗交易数据

        参数:
            date: 日期 (YYYY-MM-DD格式)
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # 转换日期格式
        date_str = date.replace('-', '')

        url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_DATA_BLOCKTRADE&columns=ALL&filter=(TRADE_DATE%3D%27{date_str}%27)&pageSize=500&pageNumber=1"

        data = fetch_json_via_powershell(url)
        if not data or 'result' not in data or 'data' not in data['result']:
            return []

        trades = []
        for item in data['result']['data']:
            try:
                trades.append(BlockTrade(
                    ticker=str(item.get('SECURITY_CODE', '')),
                    name=str(item.get('SECURITY_ABBR', '')),
                    date=date,
                    price=float(item.get('TRADE_PRICE', 0)),
                    volume=int(item.get('TRADE_VOLUME', 0)),
                    amount=float(item.get('TRADE_VALUE', 0)),
                    buyer=str(item.get('BUYER_NAME', '')),
                    seller=str(item.get('SELLER_NAME', '')),
                    premium_rate=float(item.get('PREMIUM_RATE', 0)),
                ))
            except Exception as e:
                logger.warning(f"解析大宗交易失败: {e}")
                continue

        return trades

    @staticmethod
    def get_realtime_quotes(codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取实时行情

        参数:
            codes: 股票代码列表
        """
        # 构建secid列表
        secids = []
        for code in codes:
            if code.startswith('6'):
                secids.append(f"1.{code}")
            else:
                secids.append(f"0.{code}")

        url = f"https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids={','.join(secids)}&fields=f1,f2,f3,f4,f5,f6,f7,f12,f14"

        data = fetch_json_via_powershell(url)
        if not data or 'data' not in data or 'diff' not in data['data']:
            return {}

        quotes = {}
        for item in data['data']['diff']:
            try:
                code = str(item.get('f12', ''))
                quotes[code] = {
                    'code': code,
                    'name': item.get('f14', ''),
                    'price': item.get('f2', 0),
                    'change_pct': item.get('f3', 0),
                    'change': item.get('f4', 0),
                    'volume': item.get('f5', 0),
                    'amount': item.get('f6', 0),
                    'turnover_rate': item.get('f7', 0),
                }
            except Exception as e:
                logger.warning(f"解析行情数据失败: {e}")
                continue

        return quotes

    @staticmethod
    def get_stock_info(code: str) -> Optional[Dict]:
        """获取股票基本信息"""
        if code.startswith('6'):
            secid = f"1.{code}"
        else:
            secid = f"0.{code}"

        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f57,f58,f162,f167,f92,f173,f187,f105,f116,f117"

        data = fetch_json_via_powershell(url)
        if not data or 'data' not in data:
            return None

        return data['data']


if __name__ == "__main__":
    print("测试东方财富API...")

    # 测试K线数据
    klines = EastMoneyAPI.get_kline_data("600519", count=10)
    print(f"\n获取到 {len(klines)} 条K线数据")
    if klines:
        print(f"最新: {klines[-1].date} 收盘: {klines[-1].close}")

    # 测试资金流向
    flow = EastMoneyAPI.get_fund_flow("600519")
    if flow:
        print(f"\n资金流向: {flow.name}")
        print(f"  主力净流入: {flow.main_net_inflow:.2f}万")

    # 测试板块资金流向
    sectors = EastMoneyAPI.get_sector_fund_flow()
    print(f"\n获取到 {len(sectors)} 个板块数据")
