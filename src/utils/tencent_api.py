"""
腾讯财经API数据源
解决与singbox代理的SSL兼容性问题
"""

import subprocess
import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StockQuote:
    """股票行情数据"""
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
    time: str


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


def parse_tencent_stock_data(data: str, code: str) -> Optional[StockQuote]:
    """解析腾讯股票数据格式"""
    try:
        # 格式: v_sh600519="1~贵州茅台~600519~1372.99~..."
        if not data or '="' not in data:
            return None

        # 提取引号内的数据
        match = re.search(r'"([^"]+)"', data)
        if not match:
            return None

        parts = match.group(1).split('~')
        if len(parts) < 30:
            return None

        return StockQuote(
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
            time=parts[30] if len(parts) > 30 else ""
        )

    except Exception as e:
        logger.error(f"解析腾讯数据失败: {e}")
        return None


def get_stock_quote(code: str) -> Optional[StockQuote]:
    """
    获取单只股票行情

    参数:
        code: 股票代码（如600519）
    """
    # 确定市场前缀
    if code.startswith('6'):
        prefix = 'sh'
    else:
        prefix = 'sz'

    url = f"https://web.sqt.gtimg.cn/q={prefix}{code}"

    data = fetch_via_powershell(url)
    if data:
        return parse_tencent_stock_data(data, code)
    return None


def get_stock_quotes(codes: List[str]) -> Dict[str, StockQuote]:
    """
    批量获取股票行情

    参数:
        codes: 股票代码列表
    """
    # 构建URL
    symbols = []
    for code in codes:
        if code.startswith('6'):
            symbols.append(f"sh{code}")
        else:
            symbols.append(f"sz{code}")

    url = f"https://web.sqt.gtimg.cn/q={','.join(symbols)}"

    data = fetch_via_powershell(url)
    if not data:
        return {}

    # 解析多只股票数据
    results = {}
    lines = data.strip().split('\n')

    for line in lines:
        # 提取股票代码
        match = re.match(r'v_(sh|sz)(\d+)=', line)
        if match:
            market = match.group(1)
            code = match.group(2)
            quote = parse_tencent_stock_data(line, code)
            if quote:
                results[code] = quote

    return results


def get_stock_kline(code: str, period: str = 'day', count: int = 100) -> Optional[List[Dict]]:
    """
    获取股票K线数据（通过腾讯财经接口）

    参数:
        code: 股票代码
        period: 周期 (day/week/month)
        count: 获取数量
    """
    # 确定市场前缀
    if code.startswith('6'):
        prefix = 'sh'
    else:
        prefix = 'sz'

    # 腾讯K线API
    url = f"https://web.sqt.gtimg.cn/q={prefix}{code}&format=json"

    data = fetch_via_powershell(url)
    if not data:
        return None

    # 解析K线数据（简化版，实际需要更复杂的解析）
    quote = parse_tencent_stock_data(data, code)
    if quote:
        return [{
            'date': quote.time[:8] if quote.time else '',
            'open': quote.open,
            'close': quote.price,
            'high': quote.high,
            'low': quote.low,
            'volume': quote.volume
        }]
    return None


if __name__ == "__main__":
    print("测试腾讯财经API...")

    # 测试单只股票
    quote = get_stock_quote("600519")
    if quote:
        print(f"\n{quote.code} {quote.name}")
        print(f"  价格: {quote.price}")
        print(f"  涨跌: {quote.change} ({quote.change_pct}%)")
        print(f"  成交量: {quote.volume}")

    # 测试批量获取
    codes = ["600519", "000001", "300750"]
    quotes = get_stock_quotes(codes)
    print(f"\n批量获取 {len(quotes)} 只股票:")
    for code, q in quotes.items():
        print(f"  {code} {q.name}: {q.price}")
