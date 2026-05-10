"""
下周热门板块分析脚本

基于消息面和技术面分析下周热门板块
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.utils.eastmoney_api import EastMoneyAPI
import logging

logging.basicConfig(level=logging.WARNING)


# 下周热门板块预测（基于消息面分析）
HOT_SECTORS = {
    "人工智能/AI应用": {
        "reason": "AI技术持续突破，大模型应用落地加速，算力需求增长",
        "hot_stocks": ["科大讯飞(002230)", "海康威视(002415)", "大华股份(002236)"],
        "investment_logic": "AI大模型商业化进程加快，应用端受益明显",
        "risk": "估值较高，需关注业绩兑现情况"
    },
    "半导体/芯片": {
        "reason": "国产替代持续推进，芯片自主可控政策支持",
        "hot_stocks": ["中芯国际(688981)", "北方华创(002371)", "韦尔股份(603501)"],
        "investment_logic": "政策扶持+国产替代双轮驱动",
        "risk": "技术迭代风险，国际竞争压力"
    },
    "新能源车": {
        "reason": "销量持续增长，智能化升级加速，出口市场扩大",
        "hot_stocks": ["比亚迪(002594)", "宁德时代(300750)", "理想汽车"],
        "investment_logic": "国内渗透率提升+海外市场拓展",
        "risk": "价格竞争激烈，利润率承压"
    },
    "医药/创新药": {
        "reason": "创新药审批加速，医保政策优化，老龄化需求增长",
        "hot_stocks": ["恒瑞医药(600276)", "药明康德(603259)", "云南白药(000538)"],
        "investment_logic": "创新药管线兑现+政策回暖",
        "risk": "研发投入大，审批周期长"
    },
    "消费/白酒": {
        "reason": "消费复苏预期，白酒龙头业绩稳健，估值修复",
        "hot_stocks": ["贵州茅台(600519)", "五粮液(000858)", "泸州老窖(000568)"],
        "investment_logic": "消费复苏+估值合理",
        "risk": "消费复苏节奏不确定"
    },
    "金融/券商": {
        "reason": "市场活跃度提升，注册制改革深化，并购重组活跃",
        "hot_stocks": ["中信证券(600030)", "华泰证券(601688)", "东方财富(300059)"],
        "investment_logic": "市场回暖+政策红利",
        "risk": "市场波动影响业绩"
    },
    "电力/新能源": {
        "reason": "电力需求增长，新能源装机加速，电价改革",
        "hot_stocks": ["长江电力(600900)", "国电电力(600795)", "三峡能源"],
        "investment_logic": "需求刚性+清洁能源转型",
        "risk": "电价政策变化"
    },
    "军工/国防": {
        "reason": "国防预算增长，装备升级需求，地缘政治因素",
        "hot_stocks": ["中航沈飞(600760)", "航发动力(600893)", "中国卫星"],
        "investment_logic": "订单确定性高+政策支持",
        "risk": "订单节奏波动"
    }
}


def analyze_sector_technical(sector_stocks: list) -> dict:
    """分析板块内股票的技术面"""
    results = []

    for stock_info in sector_stocks:
        try:
            # 解析股票代码
            if '(' in stock_info and ')' in stock_info:
                code = stock_info.split('(')[1].replace(')', '')
                name = stock_info.split('(')[0]
            else:
                continue
            # 获取K线数据
            if code.startswith('6'):
                market_code = f"{code}.SH"
            elif code.startswith(('0', '3')):
                market_code = f"{code}.SZ"
            else:
                continue

            klines = EastMoneyAPI.get_kline_data(market_code, count=30)
            if not klines or len(klines) < 20:
                continue

            # 简单技术分析
            closes = [k.close for k in klines]
            ma5 = sum(closes[-5:]) / 5
            ma10 = sum(closes[-10:]) / 10
            ma20 = sum(closes[-20:]) / 20
            current_price = closes[-1]

            # 判断均线状态
            if ma5 > ma10 > ma20 and current_price > ma5:
                ma_status = "多头排列"
                score = 8
            elif ma5 > ma10:
                ma_status = "短期多头"
                score = 6
            else:
                ma_status = "震荡"
                score = 5

            results.append({
                'code': code,
                'name': name,
                'price': current_price,
                'ma_status': ma_status,
                'score': score
            })

        except Exception as e:
            continue

    return results


def print_sector_analysis():
    """打印板块分析结果"""
    print("=" * 70)
    print("下周热门板块分析（消息面+技术面）")
    print("=" * 70)
    print("\n基于消息面分析，下周重点关注以下板块：")
    print("-" * 70)

    for i, (sector, info) in enumerate(HOT_SECTORS.items(), 1):
        print(f"\n【{i}】{sector}")
        print(f"    消息面驱动：{info['reason']}")
        print(f"    投资逻辑：{info['investment_logic']}")
        print(f"    风险提示：{info['risk']}")
        print(f"    关注标的：{', '.join(info['hot_stocks'])}")

        # 尝试分析技术面
        print(f"    技术面分析：")
        tech_results = analyze_sector_technical(info['hot_stocks'])
        if tech_results:
            for stock in tech_results:
                print(f"      - {stock['name']}({stock['code']}): "
                      f"价格{stock['price']:.2f}, {stock['ma_status']} (评分:{stock['score']})")
        else:
            print(f"      （数据获取受限）")

    print("\n" + "=" * 70)
    print("综合建议：")
    print("=" * 70)
    print("""
    1. AI/人工智能板块：技术突破+应用落地，中长期看好，关注应用端龙头
    2. 半导体板块：国产替代确定性高，但需关注估值水平
    3. 新能源车板块：销量增长确定，但价格竞争激烈，优选龙头
    4. 医药板块：政策回暖，创新药管线兑现期，关注研发实力强的企业
    5. 消费/白酒板块：估值修复+业绩稳健，防御性配置
    6. 金融/券商板块：市场活跃度提升，弹性较大
    7. 电力/新能源板块：需求刚性，稳健配置
    8. 军工板块：订单确定性高，但波动较大

    操作建议：
    - 短期：关注AI应用、券商板块的弹性机会
    - 中期：布局半导体、新能源车龙头
    - 长期：配置医药、消费、电力等稳健板块
    """)


if __name__ == "__main__":
    print_sector_analysis()