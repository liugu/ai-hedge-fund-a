"""
板块轮动分析模块
分析板块资金流向，识别热点板块和轮动机会
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class SectorFlow:
    """板块资金流向"""
    sector_name: str
    sector_code: str
    change_pct: float  # 涨跌幅
    net_inflow: float  # 净流入金额（亿元）
    turnover: float  # 成交额
    leading_stock: str  # 领涨股
    leading_change: float  # 领涨股涨幅
    rank: int = 0  # 排名
    trend: str = "neutral"  # bullish/bearish/neutral
    rotation_signal: str = ""  # 轮动信号


@dataclass
class RotationAnalysis:
    """轮动分析结果"""
    hot_sectors: List[SectorFlow]  # 热点板块
    cold_sectors: List[SectorFlow]  # 冷门板块
    inflow_sectors: List[SectorFlow]  # 资金流入板块
    outflow_sectors: List[SectorFlow]  # 资金流出板块
    rotation_direction: str  # 轮动方向
    market_sentiment: str  # 市场情绪
    recommended_sectors: List[str]  # 推荐关注板块


class SectorRotationAnalyzer:
    """板块轮动分析器"""

    # 板块分类
    GROWTH_SECTORS = ["新能源电池", "新能源汽车", "光伏", "光伏逆变器", "芯片", "半导体设备", "医疗器械"]
    DEFENSIVE_SECTORS = ["白酒", "银行", "电力", "食品饮料", "医药"]
    CYCLICAL_SECTORS = ["化工", "有色金属", "煤炭", "钢铁", "房地产"]
    CONCEPT_SECTORS = ["人工智能", "机器人", "数字经济", "元宇宙", "量子科技"]

    def __init__(self):
        self.sector_history = defaultdict(list)  # 板块历史数据
        self.flow_history = defaultdict(list)  # 资金流向历史

    def analyze(self, sector_data: List[Dict], fund_flow_data: List[Dict] = None,
                historical_data: List[List[Dict]] = None) -> RotationAnalysis:
        """
        分析板块轮动

        参数:
            sector_data: 当前板块数据
            fund_flow_data: 资金流向数据
            historical_data: 历史板块数据（用于趋势分析）
        """
        # 构建板块流向列表
        sectors = self._build_sector_flows(sector_data, fund_flow_data)

        # 排序
        sectors_by_change = sorted(sectors, key=lambda x: x.change_pct, reverse=True)
        sectors_by_flow = sorted(sectors, key=lambda x: x.net_inflow, reverse=True)

        # 设置排名
        for i, s in enumerate(sectors_by_change):
            s.rank = i + 1

        # 分类板块
        hot_sectors = [s for s in sectors_by_change[:5]]
        cold_sectors = [s for s in sectors_by_change[-5:]]
        inflow_sectors = [s for s in sectors_by_flow if s.net_inflow > 0][:5]
        outflow_sectors = [s for s in sectors_by_flow if s.net_inflow < 0][-5:]

        # 分析趋势
        for sector in sectors:
            sector.trend = self._analyze_sector_trend(sector)
            sector.rotation_signal = self._generate_rotation_signal(sector, sectors)

        # 判断轮动方向
        rotation_direction = self._analyze_rotation_direction(sectors)

        # 判断市场情绪
        market_sentiment = self._analyze_market_sentiment(sectors)

        # 推荐板块
        recommended = self._recommend_sectors(sectors, rotation_direction)

        return RotationAnalysis(
            hot_sectors=hot_sectors,
            cold_sectors=cold_sectors,
            inflow_sectors=inflow_sectors,
            outflow_sectors=outflow_sectors,
            rotation_direction=rotation_direction,
            market_sentiment=market_sentiment,
            recommended_sectors=recommended
        )

    def _build_sector_flows(self, sector_data: List[Dict], fund_flow_data: List[Dict] = None) -> List[SectorFlow]:
        """构建板块流向列表"""
        sectors = []

        # 构建资金流向映射
        flow_map = {}
        if fund_flow_data:
            for flow in fund_flow_data:
                flow_map[flow.get('code', '')] = flow.get('net_inflow', 0)
                flow_map[flow.get('name', '')] = flow.get('net_inflow', 0)

        for data in sector_data:
            code = data.get('code', data.get('sector_code', ''))
            name = data.get('name', data.get('sector_name', ''))

            # 获取净流入
            net_inflow = flow_map.get(code, flow_map.get(name, data.get('net_inflow', 0)))

            sectors.append(SectorFlow(
                sector_name=name,
                sector_code=code,
                change_pct=data.get('change_pct', data.get('涨跌幅', 0)),
                net_inflow=net_inflow / 100000000 if abs(net_inflow) > 100000000 else net_inflow,  # 转换为亿
                turnover=data.get('turnover', data.get('成交额', 0)),
                leading_stock=data.get('leading_stock', data.get('领涨股', '')),
                leading_change=data.get('leading_change', data.get('领涨股涨幅', 0)),
            ))

        return sectors

    def _analyze_sector_trend(self, sector: SectorFlow) -> str:
        """分析板块趋势"""
        if sector.change_pct > 2 and sector.net_inflow > 0:
            return "bullish"
        elif sector.change_pct < -2 and sector.net_inflow < 0:
            return "bearish"
        else:
            return "neutral"

    def _generate_rotation_signal(self, sector: SectorFlow, all_sectors: List[SectorFlow]) -> str:
        """生成轮动信号"""
        avg_change = sum(s.change_pct for s in all_sectors) / len(all_sectors) if all_sectors else 0

        signals = []

        # 相对强度
        if sector.change_pct > avg_change + 1:
            signals.append("相对强势")
        elif sector.change_pct < avg_change - 1:
            signals.append("相对弱势")

        # 资金流向
        if sector.net_inflow > 10:
            signals.append("资金大幅流入")
        elif sector.net_inflow > 0:
            signals.append("资金流入")
        elif sector.net_inflow < -10:
            signals.append("资金大幅流出")
        elif sector.net_inflow < 0:
            signals.append("资金流出")

        # 板块类型
        if sector.sector_name in self.GROWTH_SECTORS:
            signals.append("成长板块")
        elif sector.sector_name in self.DEFENSIVE_SECTORS:
            signals.append("防御板块")
        elif sector.sector_name in self.CYCLICAL_SECTORS:
            signals.append("周期板块")

        return ", ".join(signals) if signals else "无明确信号"

    def _analyze_rotation_direction(self, sectors: List[SectorFlow]) -> str:
        """分析轮动方向"""
        # 统计各类板块表现
        growth_avg = self._calc_category_avg(sectors, self.GROWTH_SECTORS)
        defensive_avg = self._calc_category_avg(sectors, self.DEFENSIVE_SECTORS)
        cyclical_avg = self._calc_category_avg(sectors, self.CYCLICAL_SECTORS)

        # 判断轮动方向
        if growth_avg > defensive_avg and growth_avg > cyclical_avg:
            return "成长板块领涨，市场风险偏好上升"
        elif defensive_avg > growth_avg and defensive_avg > cyclical_avg:
            return "防御板块领涨，市场避险情绪升温"
        elif cyclical_avg > growth_avg and cyclical_avg > defensive_avg:
            return "周期板块领涨，经济复苏预期增强"
        else:
            return "板块表现均衡，无明显轮动方向"

    def _calc_category_avg(self, sectors: List[SectorFlow], category: List[str]) -> float:
        """计算板块类别平均涨跌幅"""
        matching = [s for s in sectors if s.sector_name in category]
        if not matching:
            return 0
        return sum(s.change_pct for s in matching) / len(matching)

    def _analyze_market_sentiment(self, sectors: List[SectorFlow]) -> str:
        """分析市场情绪"""
        # 统计涨跌板块数量
        rising = sum(1 for s in sectors if s.change_pct > 0)
        falling = sum(1 for s in sectors if s.change_pct < 0)

        # 统计资金流向
        inflow = sum(1 for s in sectors if s.net_inflow > 0)
        outflow = sum(1 for s in sectors if s.net_inflow < 0)

        # 判断情绪
        if rising > falling * 1.5 and inflow > outflow:
            return "乐观"
        elif falling > rising * 1.5 and outflow > inflow:
            return "悲观"
        elif rising > falling:
            return "偏乐观"
        elif falling > rising:
            return "偏悲观"
        else:
            return "中性"

    def _recommend_sectors(self, sectors: List[SectorFlow], rotation_direction: str) -> List[str]:
        """推荐关注板块"""
        recommendations = []

        # 根据轮动方向推荐
        if "成长" in rotation_direction:
            # 推荐强势成长板块
            growth = [s for s in sectors if s.sector_name in self.GROWTH_SECTORS and s.trend == "bullish"]
            recommendations.extend([s.sector_name for s in growth[:3]])
        elif "防御" in rotation_direction:
            # 推荐防御板块
            defensive = [s for s in sectors if s.sector_name in self.DEFENSIVE_SECTORS and s.net_inflow > 0]
            recommendations.extend([s.sector_name for s in defensive[:3]])
        elif "周期" in rotation_direction:
            # 推荐周期板块
            cyclical = [s for s in sectors if s.sector_name in self.CYCLICAL_SECTORS and s.trend == "bullish"]
            recommendations.extend([s.sector_name for s in cyclical[:3]])

        # 添加资金流入最多的板块
        inflow_sorted = sorted(sectors, key=lambda x: x.net_inflow, reverse=True)
        for s in inflow_sorted[:3]:
            if s.sector_name not in recommendations:
                recommendations.append(s.sector_name)

        return recommendations[:5]


def analyze_sector_rotation(sector_data: List[Dict], fund_flow_data: List[Dict] = None) -> RotationAnalysis:
    """
    分析板块轮动的便捷函数

    参数:
        sector_data: 板块数据列表
        fund_flow_data: 资金流向数据

    返回:
        RotationAnalysis对象
    """
    analyzer = SectorRotationAnalyzer()
    return analyzer.analyze(sector_data, fund_flow_data)


def print_rotation_analysis(analysis: RotationAnalysis):
    """打印轮动分析结果"""
    print("\n" + "=" * 60)
    print("板块轮动分析报告")
    print("=" * 60)

    print(f"\n市场情绪: {analysis.market_sentiment}")
    print(f"轮动方向: {analysis.rotation_direction}")

    print("\n热点板块 TOP5:")
    for i, s in enumerate(analysis.hot_sectors, 1):
        print(f"  {i}. {s.sector_name}: {s.change_pct:+.2f}% 净流入: {s.net_inflow:.2f}亿")

    print("\n冷门板块 BOTTOM5:")
    for i, s in enumerate(analysis.cold_sectors, 1):
        print(f"  {i}. {s.sector_name}: {s.change_pct:+.2f}% 净流入: {s.net_inflow:.2f}亿")

    print("\n资金流入板块 TOP5:")
    for i, s in enumerate(analysis.inflow_sectors, 1):
        print(f"  {i}. {s.sector_name}: 净流入 {s.net_inflow:.2f}亿")

    print("\n资金流出板块 TOP5:")
    for i, s in enumerate(analysis.outflow_sectors, 1):
        print(f"  {i}. {s.sector_name}: 净流出 {abs(s.net_inflow):.2f}亿")

    print("\n推荐关注板块:")
    for sector in analysis.recommended_sectors:
        print(f"  - {sector}")

    print("=" * 60)


if __name__ == "__main__":
    # 测试数据
    test_sectors = [
        {"name": "新能源电池", "change_pct": 3.5, "net_inflow": 1500000000},
        {"name": "新能源汽车", "change_pct": 2.8, "net_inflow": 1200000000},
        {"name": "白酒", "change_pct": 1.2, "net_inflow": 500000000},
        {"name": "银行", "change_pct": -0.5, "net_inflow": -300000000},
        {"name": "房地产", "change_pct": -2.1, "net_inflow": -800000000},
        {"name": "光伏", "change_pct": 2.1, "net_inflow": 600000000},
        {"name": "医疗器械", "change_pct": 1.8, "net_inflow": 400000000},
        {"name": "芯片", "change_pct": 2.5, "net_inflow": 900000000},
        {"name": "电力", "change_pct": 0.8, "net_inflow": 200000000},
        {"name": "化工", "change_pct": -1.2, "net_inflow": -400000000},
    ]

    analysis = analyze_sector_rotation(test_sectors)
    print_rotation_analysis(analysis)
