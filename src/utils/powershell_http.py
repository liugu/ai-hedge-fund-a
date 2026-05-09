"""
使用PowerShell的Invoke-RestMethod获取数据
绕过Python SSL与singbox代理的兼容性问题
"""

import subprocess
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def fetch_url_via_powershell(url: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
    """
    使用PowerShell的Invoke-RestMethod获取URL数据

    参数:
        url: 要获取的URL
        timeout: 超时时间（秒）

    返回:
        解析后的JSON数据，如果失败返回None
    """
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
            logger.error(f"PowerShell请求失败: {result.stderr}")
            return None

        # 解析JSON响应
        data = json.loads(result.stdout)
        return data

    except subprocess.TimeoutExpired:
        logger.error(f"PowerShell请求超时: {url}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        return None
    except Exception as e:
        logger.error(f"PowerShell请求异常: {e}")
        return None


def get_eastmoney_stock_data(code: str, start_date: str = None, end_date: str = None) -> Optional[Dict]:
    """
    获取东方财富股票数据

    参数:
        code: 股票代码（如600519）
        start_date: 开始日期（YYYYMMDD格式）
        end_date: 结束日期（YYYYMMDD格式）
    """
    # 确定市场代码
    if code.startswith('6'):
        secid = f"1.{code}"  # 上海
    else:
        secid = f"0.{code}"  # 深圳

    url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1"

    if end_date:
        url += f"&end={end_date}"

    return fetch_url_via_powershell(url)


def get_eastmoney_realtime_quotes() -> Optional[list]:
    """获取A股实时行情列表"""
    url = "https://82.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f12&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f1,f2,f3,f4,f5,f6,f7,f12,f14"

    data = fetch_url_via_powershell(url)
    if data and 'data' in data and 'diff' in data['data']:
        return data['data']['diff']
    return None


def get_eastmoney_financial_indicator(code: str) -> Optional[Dict]:
    """获取财务指标"""
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid=1.{code}&fields=f57,f58,f162,f167,f92,f173,f187,f105,f116,f117"

    return fetch_url_via_powershell(url)


if __name__ == "__main__":
    # 测试
    print("测试获取股票数据...")

    # 测试获取K线数据
    data = get_eastmoney_stock_data("600519")
    if data:
        print("K线数据获取成功")
        print(f"数据键: {list(data.keys())}")
    else:
        print("K线数据获取失败")

    # 测试获取实时行情
    quotes = get_eastmoney_realtime_quotes()
    if quotes:
        print(f"实时行情获取成功，共{len(quotes)}只股票")
        if quotes:
            print(f"示例: {quotes[0]}")
    else:
        print("实时行情获取失败")
