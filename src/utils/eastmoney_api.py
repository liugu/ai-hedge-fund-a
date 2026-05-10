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
            encoding='utf-8',
            errors='ignore'  # 忽略编码错误
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
            encoding='utf-8',
            errors='ignore'  # 忽略编码错误
        )

        if result.returncode != 0:
            logger.error(f"PowerShell JSON请求失败: {result.stderr}")
            return None

        if not result.stdout or result.stdout.strip() == '':
            logger.error(f"PowerShell JSON请求返回空内容")
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
    def _normalize_code(code: str) -> str:
        """
        标准化股票代码，去除后缀

        参数:
            code: 股票代码（可能带后缀如 000626.SZ 或 600519.SH）

        返回:
            纯股票代码（如 000626 或 600519）
        """
        # 去除后缀 (.SZ, .SH, .BJ 等)
        if '.' in code:
            code = code.split('.')[0]
        return code.strip()

    @staticmethod
    def get_kline_data(code: str, period: str = 'day', count: int = 100) -> List[KLineData]:
        """
        获取K线数据

        参数:
            code: 股票代码（支持带后缀格式如 000626.SZ）
            period: 周期 (day/week/month)
            count: 获取数量
        """
        # 标准化代码
        code = EastMoneyAPI._normalize_code(code)

        # 确定市场代码 (sz或sh)
        if code.startswith('6'):
            market = 'sh'
        else:
            market = 'sz'

        # K线周期映射 (腾讯API格式)
        klt_map = {'day': 'day', 'week': 'week', 'month': 'month'}
        klt = klt_map.get(period, 'day')

        # 使用腾讯API获取K线数据
        # 参数格式: param=市场代码+股票代码,周期,开始日期,结束日期,数量,复权类型
        # 例如: param=sz000626,day,,,10,qfq
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={market}{code},{klt},,,{count},qfq"

        try:
            result = fetch_via_powershell(url)
            if not result:
                return []

            data = json.loads(result)
            if not data or 'data' not in data:
                return []

            stock_data = data.get('data', {})
            if not stock_data:
                return []

            # stock_data是一个字典，key是股票代码
            stock_key = f'{market}{code}'
            if stock_key not in stock_data:
                # 尝试其他可能的key
                stock_key = list(stock_data.keys())[0] if stock_data else None
                if not stock_key:
                    return []

            stock_info = stock_data.get(stock_key, {})
            klines_raw = stock_info.get('qfqday', []) or stock_info.get('day', [])

            if not klines_raw:
                return []

            klines = []
            for item in klines_raw[-count:]:  # 只取最近count条
                try:
                    # 腾讯API格式: [日期, 开盘, 收盘, 最高, 最低, 成交量]
                    klines.append(KLineData(
                        date=item[0],
                        open=float(item[1]) if item[1] else 0,
                        close=float(item[2]) if item[2] else 0,
                        high=float(item[3]) if item[3] else 0,
                        low=float(item[4]) if item[4] else 0,
                        volume=int(float(item[5])) if item[5] else 0,
                        amount=0,  # 腾讯API不提供成交额
                        change_pct=0,  # 需要计算
                        turnover_rate=0,
                    ))
                except Exception as e:
                    logger.warning(f"解析K线数据失败: {e}")
                    continue

            # 计算涨跌幅
            for i in range(1, len(klines)):
                if klines[i-1].close > 0:
                    klines[i].change_pct = round((klines[i].close - klines[i-1].close) / klines[i-1].close * 100, 2)

            return klines

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return []
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            return []

    @staticmethod
    def get_fund_flow(code: str) -> Optional[FundFlow]:
        """
        获取资金流向数据

        参数:
            code: 股票代码（支持带后缀格式如 000626.SZ）
        """
        # 标准化代码
        code = EastMoneyAPI._normalize_code(code)

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
            info = data['data'].get('info', {}) or {}
            # info可能为空，从data中获取name
            name = info.get('name', '') or data['data'].get('name', '')
            flows = data['data'].get('klines', [])
            if not flows:
                return None

            # 获取最新一天的数据
            latest = flows[-1] if isinstance(flows, list) else flows
            if isinstance(latest, str):
                parts = latest.split(',')
                # 数据格式: 日期,主力净流入,超大单净流入,大单净流入,中单净流入,小单净流入
                # 单位是元，需要转换为万元
                return FundFlow(
                    ticker=code,
                    name=name,
                    main_net_inflow=float(parts[1]) / 10000 if len(parts) > 1 and parts[1] else 0,
                    retail_net_inflow=(float(parts[4]) + float(parts[5])) / 10000 if len(parts) > 5 else 0,
                    super_net_inflow=float(parts[2]) / 10000 if len(parts) > 2 and parts[2] else 0,
                    big_net_inflow=float(parts[3]) / 10000 if len(parts) > 3 and parts[3] else 0,
                    medium_net_inflow=float(parts[4]) / 10000 if len(parts) > 4 and parts[4] else 0,
                    small_net_inflow=float(parts[5]) / 10000 if len(parts) > 5 and parts[5] else 0,
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
            codes: 股票代码列表（支持带后缀格式如 000626.SZ）
        """
        # 构建secid列表
        secids = []
        for code in codes:
            # 标准化代码
            code = EastMoneyAPI._normalize_code(code)
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
        # 标准化代码
        code = EastMoneyAPI._normalize_code(code)

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
