"""
期权数据模块

支持期权相关数据获取：
1. 期权合约列表
2. 期权行情数据
3. 期权隐含波动率
4. 期权PCR指标
"""

import subprocess
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class OptionContract:
    """期权合约"""
    code: str
    name: str
    underlying: str  # 标的代码
    option_type: str  # call/put
    strike_price: float  # 行权价
    expire_date: str  # 到期日
    price: float
    change_pct: float
    volume: int
    open_interest: int  # 持仓量
    implied_vol: Optional[float] = None


@dataclass
class OptionPCR:
    """期权PCR指标"""
    date: str
    call_volume: int
    put_volume: int
    call_open_interest: int
    put_open_interest: int
    volume_pcr: float  # 成交量PCR
    oi_pcr: float  # 持仓量PCR


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


class OptionAPI:
    """期权数据API"""

    # 主要期权标的
    OPTION_UNDERLYINGS = {
        "510050": "50ETF期权",
        "510300": "300ETF期权",
        "159919": "300ETF期权(深)",
        "000300": "沪深300股指期权",
    }

    @staticmethod
    def get_option_list(underlying: str = "510050") -> List[OptionContract]:
        """
        获取期权合约列表

        参数:
            underlying: 标的代码
        """
        # 东方财富期权接口
        url = f"https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:23&fields=f1,f2,f3,f4,f5,f6,f7,f12,f14"

        data = fetch_json_via_powershell(url)
        if not data or 'data' not in data or 'diff' not in data['data']:
            return []

        contracts = []
        for item in data['data']['diff']:
            try:
                code = str(item.get('f12', ''))
                name = str(item.get('f14', ''))

                # 判断期权类型
                option_type = 'call' if '购' in name or 'C' in name else 'put'

                contracts.append(OptionContract(
                    code=code,
                    name=name,
                    underlying=underlying,
                    option_type=option_type,
                    strike_price=0,  # 需要额外解析
                    expire_date='',  # 需要额外解析
                    price=float(item.get('f2', 0)),
                    change_pct=float(item.get('f3', 0)),
                    volume=int(item.get('f5', 0)),
                    open_interest=int(item.get('f6', 0)),
                ))
            except Exception as e:
                logger.warning(f"解析期权数据失败: {e}")
                continue

        return contracts

    @staticmethod
    def get_option_quote(code: str) -> Optional[OptionContract]:
        """
        获取期权行情

        参数:
            code: 期权合约代码
        """
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid=90.{code}&fields=f1,f2,f3,f4,f5,f6,f7,f12,f14"

        data = fetch_json_via_powershell(url)
        if not data or 'data' not in data:
            return None

        try:
            item = data['data']
            return OptionContract(
                code=code,
                name=str(item.get('f14', '')),
                underlying='',
                option_type='',
                strike_price=0,
                expire_date='',
                price=float(item.get('f2', 0)),
                change_pct=float(item.get('f3', 0)),
                volume=int(item.get('f5', 0)),
                open_interest=int(item.get('f6', 0)),
            )
        except Exception as e:
            logger.error(f"解析期权行情失败: {e}")
            return None

    @staticmethod
    def get_option_pcr(underlying: str = "510050") -> Optional[OptionPCR]:
        """
        获取期权PCR指标

        PCR = Put/Call Ratio，反映市场情绪
        PCR > 1: 市场偏悲观
        PCR < 1: 市场偏乐观
        """
        contracts = OptionAPI.get_option_list(underlying)

        if not contracts:
            return None

        call_volume = sum(c.volume for c in contracts if c.option_type == 'call')
        put_volume = sum(c.volume for c in contracts if c.option_type == 'put')
        call_oi = sum(c.open_interest for c in contracts if c.option_type == 'call')
        put_oi = sum(c.open_interest for c in contracts if c.option_type == 'put')

        volume_pcr = put_volume / call_volume if call_volume > 0 else 0
        oi_pcr = put_oi / call_oi if call_oi > 0 else 0

        return OptionPCR(
            date=datetime.now().strftime('%Y-%m-%d'),
            call_volume=call_volume,
            put_volume=put_volume,
            call_open_interest=call_oi,
            put_open_interest=put_oi,
            volume_pcr=volume_pcr,
            oi_pcr=oi_pcr,
        )

    @staticmethod
    def analyze_option_sentiment(pcr: OptionPCR) -> Dict:
        """
        分析期权市场情绪

        参数:
            pcr: PCR指标数据
        """
        sentiment = "neutral"
        confidence = 50
        reasoning = ""

        # 基于持仓量PCR判断
        if pcr.oi_pcr > 1.2:
            sentiment = "bearish"
            confidence = 70
            reasoning = f"持仓量PCR={pcr.oi_pcr:.2f}，市场偏悲观，看跌期权持仓较多"
        elif pcr.oi_pcr > 1.0:
            sentiment = "bearish"
            confidence = 60
            reasoning = f"持仓量PCR={pcr.oi_pcr:.2f}，市场略偏悲观"
        elif pcr.oi_pcr < 0.8:
            sentiment = "bullish"
            confidence = 70
            reasoning = f"持仓量PCR={pcr.oi_pcr:.2f}，市场偏乐观，看涨期权持仓较多"
        elif pcr.oi_pcr < 1.0:
            sentiment = "bullish"
            confidence = 60
            reasoning = f"持仓量PCR={pcr.oi_pcr:.2f}，市场略偏乐观"
        else:
            sentiment = "neutral"
            confidence = 50
            reasoning = f"持仓量PCR={pcr.oi_pcr:.2f}，市场情绪中性"

        # 基于成交量PCR辅助判断
        if pcr.volume_pcr > 1.5:
            reasoning += f"；成交量PCR={pcr.volume_pcr:.2f}，当日看跌期权交易活跃"
        elif pcr.volume_pcr < 0.7:
            reasoning += f"；成交量PCR={pcr.volume_pcr:.2f}，当日看涨期权交易活跃"

        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "reasoning": reasoning,
            "oi_pcr": pcr.oi_pcr,
            "volume_pcr": pcr.volume_pcr,
        }


if __name__ == "__main__":
    print("测试期权API...")

    # 测试PCR指标
    pcr = OptionAPI.get_option_pcr("510050")
    if pcr:
        print(f"\n期权PCR指标:")
        print(f"  持仓量PCR: {pcr.oi_pcr:.2f}")
        print(f"  成交量PCR: {pcr.volume_pcr:.2f}")

        # 分析情绪
        sentiment = OptionAPI.analyze_option_sentiment(pcr)
        print(f"\n市场情绪分析:")
        print(f"  情绪: {sentiment['sentiment']}")
        print(f"  置信度: {sentiment['confidence']}%")
        print(f"  理由: {sentiment['reasoning']}")