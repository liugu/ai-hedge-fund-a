"""
技术面扫描器

扫描A股市场，找出技术面完美的标的
"""

import sys
import os
# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.utils.eastmoney_api import EastMoneyAPI
from src.agents.a_stock_technical import get_kline_data, analyze_ma_system, analyze_macd, analyze_kdj, analyze_rsi, analyze_volume, analyze_patterns
import logging

logging.basicConfig(level=logging.WARNING)

def get_stock_list():
    """获取股票列表"""
    import akshare as ak

    try:
        # 获取A股实时行情数据
        df = ak.stock_zh_a_spot_em()

        # 筛选涨幅在1%-9%之间的股票
        candidates = []
        for _, row in df.iterrows():
            try:
                code = str(row['代码'])
                name = str(row['名称'])
                change_pct = float(row['涨跌幅'])

                # 筛选涨幅在1%-9%之间，排除ST和退市股票
                if 1 <= change_pct <= 9 and not name.startswith('ST') and not name.startswith('*ST'):
                    candidates.append({
                        'code': code,
                        'name': name,
                        'change_pct': change_pct
                    })
            except:
                continue

        return candidates
    except Exception as e:
        print(f"AKShare获取失败: {e}")
        # 使用预设的热门股票列表作为备选
        print("使用预设股票列表...")
        return get_predefined_stock_list()


def get_predefined_stock_list():
    """预设的热门股票列表"""
    # 选择一些热门股票进行扫描
    predefined_stocks = [
        {'code': '600519', 'name': '贵州茅台'},
        {'code': '000858', 'name': '五粮液'},
        {'code': '000626', 'name': '远大控股'},
        {'code': '000001', 'name': '平安银行'},
        {'code': '600036', 'name': '招商银行'},
        {'code': '000333', 'name': '美的集团'},
        {'code': '600276', 'name': '恒瑞医药'},
        {'code': '000651', 'name': '格力电器'},
        {'code': '600030', 'name': '中信证券'},
        {'code': '601318', 'name': '中国平安'},
        {'code': '000002', 'name': '万科A'},
        {'code': '600000', 'name': '浦发银行'},
        {'code': '000725', 'name': '京东方A'},
        {'code': '002415', 'name': '海康威视'},
        {'code': '600900', 'name': '长江电力'},
        {'code': '000063', 'name': '中兴通讯'},
        {'code': '002230', 'name': '科大讯飞'},
        {'code': '600585', 'name': '海螺水泥'},
        {'code': '000568', 'name': '泸州老窖'},
        {'code': '002352', 'name': '顺丰控股'},
        {'code': '600887', 'name': '伊利股份'},
        {'code': '000538', 'name': '云南白药'},
        {'code': '002304', 'name': '洋河股份'},
        {'code': '600048', 'name': '保利地产'},
        {'code': '002594', 'name': '比亚迪'},
        {'code': '300750', 'name': '宁德时代'},
        {'code': '600690', 'name': '海尔智家'},
        {'code': '002475', 'name': '立讯精密'},
        {'code': '601166', 'name': '兴业银行'},
        {'code': '600809', 'name': '山西汾酒'},
    ]
    return predefined_stocks


def scan_technical_perfect(top_n: int = 3):
    """
    扫描技术面完美的标的

    完美技术面标准：
    1. 均线系统：多头排列，股价站上所有均线（评分>=8）
    2. MACD：金叉或即将金叉（评分>=7）
    3. KDJ：未超买（J值<80）
    4. RSI：未超买（RSI<70）
    5. 成交量：放量或量价配合良好（评分>=5）
    6. K线形态：看涨形态（评分>=6）
    """

    print("=" * 60)
    print("技术面完美标的扫描器")
    print("=" * 60)
    print("\n扫描标准：")
    print("  1. 均线系统：多头排列，股价站上所有均线")
    print("  2. MACD：金叉信号")
    print("  3. KDJ：未超买区域")
    print("  4. RSI：未超买区域")
    print("  5. 成交量：量价配合良好")
    print("  6. K线形态：看涨形态")
    print("\n" + "-" * 60)

    # 获取股票列表
    print("\n正在获取股票列表...")
    candidates = get_stock_list()

    if not candidates:
        print("未获取到股票数据")
        return []

    print(f"获取到 {len(candidates)} 只股票")
    print(f"筛选出 {len(candidates)} 只涨幅合理的股票")

    # 分析每只股票的技术面
    print("\n开始技术面分析...")
    print("-" * 60)

    results = []

    for i, stock in enumerate(candidates[:50]):  # 只分析前50只
        code = stock['code']
        name = stock['name']
        print(f"\r分析进度: {i+1}/{min(50, len(candidates))} - {code} {name}    ", end="", flush=True)

        try:
            # 获取K线数据 - 根据代码判断市场
            if code.startswith('6'):
                market_code = f"{code}.SH"  # 上海
            elif code.startswith(('0', '3')):
                market_code = f"{code}.SZ"  # 深圳
            else:
                market_code = code

            kline_data = get_kline_data(market_code)

            if not kline_data or 'klines' not in kline_data:
                continue

            klines = kline_data['klines']
            if len(klines) < 30:
                continue

            # 分析各项指标
            ma_analysis = analyze_ma_system(kline_data)
            macd_analysis = analyze_macd(kline_data)
            kdj_analysis = analyze_kdj(kline_data)
            rsi_analysis = analyze_rsi(kline_data)
            volume_analysis = analyze_volume(kline_data)
            pattern_analysis = analyze_patterns(kline_data)

            # 计算综合评分
            total_score = (
                ma_analysis["score"] * 0.25 +
                macd_analysis["score"] * 0.20 +
                kdj_analysis["score"] * 0.15 +
                rsi_analysis["score"] * 0.15 +
                volume_analysis["score"] * 0.10 +
                pattern_analysis["score"] * 0.15
            )

            # 判断是否符合完美技术面（放宽部分条件）
            is_perfect = (
                ma_analysis["score"] >= 7 and  # 均线多头排列（放宽到7）
                macd_analysis["score"] >= 6 and  # MACD金叉或即将金叉（放宽到6）
                kdj_analysis.get("j", 100) < 85 and  # KDJ未超买（放宽到85）
                rsi_analysis.get("rsi", 100) < 75 and  # RSI未超买（放宽到75）
                volume_analysis["score"] >= 4 and  # 成交量配合（放宽到4）
                pattern_analysis["score"] >= 5  # 看涨形态（放宽到5）
            )

            if is_perfect:
                latest = klines[-1]
                change_pct = stock.get('change_pct', 0)
                results.append({
                    'code': code,
                    'name': name,
                    'price': latest['close'],
                    'change_pct': change_pct,
                    'total_score': total_score,
                    'ma': ma_analysis,
                    'macd': macd_analysis,
                    'kdj': kdj_analysis,
                    'rsi': rsi_analysis,
                    'volume': volume_analysis,
                    'pattern': pattern_analysis
                })

                print(f"\n找到完美技术面标的: {code} {name}")
                print(f"  当前价: {latest['close']:.2f}元, 综合评分: {total_score:.2f}")

        except Exception as e:
            continue

    # 按综合评分排序
    results.sort(key=lambda x: x['total_score'], reverse=True)

    # 输出结果
    print("\n" + "=" * 60)
    print(f"技术面完美标的 TOP {min(top_n, len(results))}")
    print("=" * 60)

    for i, r in enumerate(results[:top_n], 1):
        print(f"\n【{i}】{r['code']} {r['name']}")
        print(f"    当前价: {r['price']:.2f}元 | 综合评分: {r['total_score']:.2f}")
        print(f"    ─────────────────────────────────────")
        print(f"    均线系统: {r['ma']['details']} (评分: {r['ma']['score']})")
        print(f"    MACD指标: {r['macd']['details']} (评分: {r['macd']['score']})")
        print(f"    KDJ指标: {r['kdj']['details']} (评分: {r['kdj']['score']})")
        print(f"    RSI指标: {r['rsi']['details']} (评分: {r['rsi']['score']})")
        print(f"    成交量: {r['volume']['details']} (评分: {r['volume']['score']})")
        print(f"    K线形态: {r['pattern']['details']} (评分: {r['pattern']['score']})")

    return results[:top_n]


if __name__ == "__main__":
    scan_technical_perfect(3)
