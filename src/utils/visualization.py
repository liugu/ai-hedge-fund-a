"""
A股数据可视化模块

支持：
1. K线图表
2. 技术指标图表
3. 资金流向图表
4. 板块轮动热力图
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_kline_chart_data(klines: List[Dict], title: str = "K线图") -> Dict:
    """
    生成K线图表数据（用于前端展示）

    参数:
        klines: K线数据列表
        title: 图表标题
    """
    return {
        "chart_type": "candlestick",
        "title": title,
        "data": {
            "dates": [k.get('date', '') for k in klines],
            "ohlc": [[
                k.get('open', 0),
                k.get('high', 0),
                k.get('low', 0),
                k.get('close', 0)
            ] for k in klines],
            "volume": [k.get('volume', 0) for k in klines],
        },
        "options": {
            "xAxis": {"type": "category"},
            "yAxis": [
                {"type": "value", "name": "价格"},
                {"type": "value", "name": "成交量", "position": "right"}
            ]
        }
    }


def generate_technical_chart_data(klines: List[Dict], indicators: Dict) -> Dict:
    """
    生成技术指标图表数据
    """
    return {
        "chart_type": "multi_panel",
        "panels": [
            {
                "name": "价格",
                "type": "candlestick",
                "data": [[k['open'], k['high'], k['low'], k['close']] for k in klines]
            },
            {
                "name": "MACD",
                "type": "line",
                "data": {
                    "macd": indicators.get('macd', []),
                    "signal": indicators.get('macd_signal', []),
                    "histogram": indicators.get('macd_hist', [])
                }
            },
            {
                "name": "KDJ",
                "type": "line",
                "data": {
                    "k": indicators.get('kdj_k', []),
                    "d": indicators.get('kdj_d', []),
                    "j": indicators.get('kdj_j', [])
                }
            },
            {
                "name": "RSI",
                "type": "line",
                "data": {
                    "rsi6": indicators.get('rsi_6', []),
                    "rsi12": indicators.get('rsi_12', []),
                    "rsi24": indicators.get('rsi_24', [])
                }
            }
        ]
    }


def generate_fund_flow_chart_data(flow_data: List[Dict]) -> Dict:
    """
    生成资金流向图表数据
    """
    return {
        "chart_type": "bar",
        "title": "资金流向分析",
        "data": {
            "categories": ["超大单", "大单", "中单", "小单"],
            "values": [
                flow_data[0].get('super_net_inflow', 0) if flow_data else 0,
                flow_data[0].get('big_net_inflow', 0) if flow_data else 0,
                flow_data[0].get('medium_net_inflow', 0) if flow_data else 0,
                flow_data[0].get('small_net_inflow', 0) if flow_data else 0,
            ]
        },
        "options": {
            "colors": ["#ef5350" if v < 0 else "#26a69a" for v in [
                flow_data[0].get('super_net_inflow', 0) if flow_data else 0,
                flow_data[0].get('big_net_inflow', 0) if flow_data else 0,
                flow_data[0].get('medium_net_inflow', 0) if flow_data else 0,
                flow_data[0].get('small_net_inflow', 0) if flow_data else 0,
            ]]
        }
    }


def generate_sector_heatmap_data(sectors: List[Dict]) -> Dict:
    """
    生成板块热力图数据
    """
    return {
        "chart_type": "heatmap",
        "title": "板块涨跌分布",
        "data": [
            {
                "name": s.get('name', s.get('sector_name', '')),
                "value": s.get('change_pct', 0),
                "volume": s.get('turnover', 0),
                "inflow": s.get('net_inflow', 0)
            }
            for s in sectors
        ],
        "options": {
            "min": -5,
            "max": 5,
            "color_range": ["#d32f2f", "#fff", "#388e3c"]
        }
    }


def generate_northbound_flow_chart_data(flows: List[Dict]) -> Dict:
    """
    生成北向资金流向图表数据
    """
    return {
        "chart_type": "combo",
        "title": "北向资金流向",
        "data": {
            "dates": [f.get('date', '') for f in flows],
            "net_buy": [f.get('net_buy', 0) for f in flows],
            "total_balance": [f.get('total_balance', 0) for f in flows]
        },
        "options": {
            "series": [
                {"type": "bar", "name": "净买入"},
                {"type": "line", "name": "累计净买入"}
            ]
        }
    }


def generate_analysis_report_html(analysis_result: Dict) -> str:
    """
    生成分析报告HTML
    """
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A股分析报告</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #1a237e, #283593);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .section {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .stock-card {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .bullish {{ border-left: 4px solid #4caf50; }}
        .neutral {{ border-left: 4px solid #ff9800; }}
        .bearish {{ border-left: 4px solid #f44336; }}
        .score {{
            font-size: 24px;
            font-weight: bold;
        }}
        .score-high {{ color: #4caf50; }}
        .score-medium {{ color: #ff9800; }}
        .score-low {{ color: #f44336; }}
        .tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin: 2px;
        }}
        .tag-bullish {{ background: #e8f5e9; color: #2e7d32; }}
        .tag-bearish {{ background: #ffebee; color: #c62828; }}
        .tag-neutral {{ background: #fff3e0; color: #ef6c00; }}
        .footer {{
            text-align: center;
            color: #9e9e9e;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>A股智能分析报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
"""

    # 看涨标的
    bullish = analysis_result.get('bullish_stocks', [])
    if bullish:
        html += """
    <div class="section">
        <h2>📈 看涨标的</h2>
"""
        for stock in bullish:
            signal_class = 'bullish'
            score_class = 'score-high' if stock.get('confidence', 50) >= 70 else 'score-medium'
            html += f"""
        <div class="stock-card {signal_class}">
            <div>
                <strong>{stock.get('ticker', '')} {stock.get('name', '')}</strong>
                <span style="color: #666; margin-left: 10px;">{stock.get('sector', '')}</span>
                <div>
                    {' '.join([f'<span class="tag tag-bullish">{s}</span>' for s in stock.get('signals', [])])}
                </div>
            </div>
            <div>
                <div class="score {score_class}">{stock.get('confidence', 0)}%</div>
                <div style="font-size: 12px; color: #666;">置信度</div>
            </div>
        </div>
"""
        html += "    </div>"

    # 中性标的
    neutral = analysis_result.get('neutral_stocks', [])
    if neutral:
        html += """
    <div class="section">
        <h2>➖ 中性标的</h2>
"""
        for stock in neutral[:10]:
            html += f"""
        <div class="stock-card neutral">
            <div>
                <strong>{stock.get('ticker', '')} {stock.get('name', '')}</strong>
                <span style="color: #666; margin-left: 10px;">{stock.get('sector', '')}</span>
            </div>
            <div class="score score-medium">{stock.get('confidence', 0)}%</div>
        </div>
"""
        html += "    </div>"

    # 看跌标的
    bearish = analysis_result.get('bearish_stocks', [])
    if bearish:
        html += """
    <div class="section">
        <h2>📉 谨慎标的</h2>
"""
        for stock in bearish:
            html += f"""
        <div class="stock-card bearish">
            <div>
                <strong>{stock.get('ticker', '')} {stock.get('name', '')}</strong>
                <span style="color: #666; margin-left: 10px;">{stock.get('sector', '')}</span>
                <div style="font-size: 12px; color: #666;">{stock.get('reasoning', '')}</div>
            </div>
            <div class="score score-low">{stock.get('confidence', 0)}%</div>
        </div>
"""
        html += "    </div>"

    # 板块分布
    sector_dist = analysis_result.get('sector_distribution', {})
    if sector_dist:
        html += """
    <div class="section">
        <h2>📊 板块分布</h2>
        <div style="display: flex; flex-wrap: wrap; gap: 10px;">
"""
        for sector, count in sorted(sector_dist.items(), key=lambda x: x[1], reverse=True):
            html += f"""
            <div class="tag tag-bullish">{sector}: {count}只</div>
"""
        html += "        </div>\n    </div>"

    html += """
    <div class="footer">
        <p>免责声明: 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。</p>
    </div>
</body>
</html>
"""
    return html


def save_analysis_report(analysis_result: Dict, output_path: str = "analysis_report.html"):
    """保存分析报告"""
    html = generate_analysis_report_html(analysis_result)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    logger.info(f"分析报告已保存到: {output_path}")


if __name__ == "__main__":
    # 测试生成报告
    test_result = {
        "bullish_stocks": [
            {"ticker": "600519", "name": "贵州茅台", "sector": "白酒", "confidence": 75, "signals": ["行业景气", "技术面强"]},
            {"ticker": "300750", "name": "宁德时代", "sector": "新能源电池", "confidence": 72, "signals": ["行业景气", "资金流入"]},
        ],
        "neutral_stocks": [
            {"ticker": "600036", "name": "招商银行", "sector": "银行", "confidence": 55},
        ],
        "bearish_stocks": [
            {"ticker": "000002", "name": "万科A", "sector": "房地产", "confidence": 35, "reasoning": "行业调整期"},
        ],
        "sector_distribution": {"白酒": 2, "新能源": 3, "银行": 1}
    }

    save_analysis_report(test_result)
    print("测试报告已生成")
