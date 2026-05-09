"""
风险管理模块

支持：
1. 风险指标计算
2. 止损止盈管理
3. 仓位控制
4. 风险预警
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """风险指标"""
    volatility: float  # 波动率
    max_drawdown: float  # 最大回撤
    var_95: float  # 95% VaR
    sharpe_ratio: float  # 夏普比率
    sortino_ratio: float  # 索提诺比率
    beta: Optional[float] = None
    alpha: Optional[float] = None


@dataclass
class Position:
    """持仓"""
    ticker: str
    shares: int
    cost_price: float
    current_price: float
    stop_loss: float  # 止损价
    take_profit: float  # 止盈价
    position_value: float
    profit_loss: float
    profit_loss_pct: float


@dataclass
class RiskAlert:
    """风险预警"""
    level: str  # info/warning/danger
    message: str
    ticker: str
    current_value: float
    threshold: float
    timestamp: str


class RiskManager:
    """风险管理器"""

    def __init__(self, max_position_pct: float = 0.1, max_total_risk: float = 0.02,
                 default_stop_loss_pct: float = 0.08, default_take_profit_pct: float = 0.15):
        """
        初始化风险管理器

        参数:
            max_position_pct: 单只股票最大仓位比例
            max_total_risk: 总风险敞口上限
            default_stop_loss_pct: 默认止损比例
            default_take_profit_pct: 默认止盈比例
        """
        self.max_position_pct = max_position_pct
        self.max_total_risk = max_total_risk
        self.default_stop_loss_pct = default_stop_loss_pct
        self.default_take_profit_pct = default_take_profit_pct

    def calculate_risk_metrics(self, returns: List[float], benchmark_returns: List[float] = None,
                               risk_free_rate: float = 0.03) -> RiskMetrics:
        """
        计算风险指标

        参数:
            returns: 收益率序列
            benchmark_returns: 基准收益率序列
            risk_free_rate: 无风险利率
        """
        if not returns:
            return RiskMetrics(0, 0, 0, 0, 0)

        returns = np.array(returns)

        # 波动率（年化）
        volatility = np.std(returns) * np.sqrt(252)

        # 最大回撤
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdowns)

        # VaR (95%)
        var_95 = np.percentile(returns, 5)

        # 夏普比率
        avg_return = np.mean(returns) * 252
        sharpe_ratio = (avg_return - risk_free_rate) / volatility if volatility > 0 else 0

        # 索提诺比率
        downside_returns = returns[returns < 0]
        downside_std = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = (avg_return - risk_free_rate) / downside_std if downside_std > 0 else 0

        # Beta和Alpha
        beta = None
        alpha = None
        if benchmark_returns is not None and len(benchmark_returns) == len(returns):
            benchmark_returns = np.array(benchmark_returns)
            covariance = np.cov(returns, benchmark_returns)[0, 1]
            benchmark_variance = np.var(benchmark_returns)
            beta = covariance / benchmark_variance if benchmark_variance > 0 else 0

            # Alpha = 年化超额收益
            alpha = (avg_return - risk_free_rate) - beta * (np.mean(benchmark_returns) * 252 - risk_free_rate)

        return RiskMetrics(
            volatility=volatility,
            max_drawdown=max_drawdown,
            var_95=var_95,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            beta=beta,
            alpha=alpha
        )

    def calculate_position_size(self, total_capital: float, stock_price: float,
                                volatility: float = None, confidence: float = 0.5) -> int:
        """
        计算建议仓位

        参数:
            total_capital: 总资金
            stock_price: 股票价格
            volatility: 波动率（可选）
            confidence: 信号置信度
        """
        # 基础仓位
        base_position_value = total_capital * self.max_position_pct

        # 根据置信度调整
        adjusted_position_value = base_position_value * confidence

        # 根据波动率调整
        if volatility is not None and volatility > 0:
            # 波动率越高，仓位越小
            volatility_adjustment = min(1.0, 0.2 / volatility)  # 目标波动率20%
            adjusted_position_value *= volatility_adjustment

        # 计算股数
        shares = int(adjusted_position_value / stock_price)

        return max(0, shares)

    def set_stop_loss_take_profit(self, buy_price: float, atr: float = None,
                                   support_level: float = None) -> Tuple[float, float]:
        """
        设置止损止盈

        参数:
            buy_price: 买入价格
            atr: 平均真实波幅（可选）
            support_level: 支撑位（可选）
        """
        # 止损设置
        if support_level and support_level < buy_price:
            stop_loss = support_level * 0.98  # 支撑位下方2%
        elif atr:
            stop_loss = buy_price - 2 * atr  # 2倍ATR止损
        else:
            stop_loss = buy_price * (1 - self.default_stop_loss_pct)

        # 止盈设置
        take_profit = buy_price * (1 + self.default_take_profit_pct)

        return stop_loss, take_profit

    def check_stop_loss_take_profit(self, position: Position) -> Optional[RiskAlert]:
        """检查止损止盈"""
        alerts = []

        # 检查止损
        if position.current_price <= position.stop_loss:
            return RiskAlert(
                level="danger",
                message=f"触发止损：当前价{position.current_price:.2f} <= 止损价{position.stop_loss:.2f}",
                ticker=position.ticker,
                current_value=position.current_price,
                threshold=position.stop_loss,
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )

        # 检查止盈
        if position.current_price >= position.take_profit:
            return RiskAlert(
                level="info",
                message=f"触发止盈：当前价{position.current_price:.2f} >= 止盈价{position.take_profit:.2f}",
                ticker=position.ticker,
                current_value=position.current_price,
                threshold=position.take_profit,
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )

        return None

    def calculate_portfolio_risk(self, positions: List[Position], total_capital: float) -> Dict:
        """
        计算组合风险

        参数:
            positions: 持仓列表
            total_capital: 总资金
        """
        if not positions:
            return {"total_risk": 0, "position_count": 0, "concentration": 0}

        # 计算总仓位
        total_position_value = sum(p.position_value for p in positions)

        # 计算仓位集中度
        position_weights = [p.position_value / total_position_value for p in positions] if total_position_value > 0 else []
        concentration = sum(w ** 2 for w in position_weights)  # Herfindahl指数

        # 计算总风险敞口
        total_risk = sum(
            abs(p.profit_loss_pct) * (p.position_value / total_capital)
            for p in positions
        )

        # 检查是否超过限制
        warnings = []
        if total_position_value / total_capital > 0.8:
            warnings.append("总仓位超过80%")

        if concentration > 0.5:
            warnings.append("持仓集中度过高")

        # 检查单只股票仓位
        for p in positions:
            if p.position_value / total_capital > self.max_position_pct:
                warnings.append(f"{p.ticker}仓位超过{self.max_position_pct*100}%限制")

        return {
            "total_risk": total_risk,
            "position_count": len(positions),
            "concentration": concentration,
            "total_position_value": total_position_value,
            "cash_ratio": 1 - total_position_value / total_capital,
            "warnings": warnings
        }


class PositionManager:
    """仓位管理器"""

    def __init__(self, total_capital: float, risk_manager: RiskManager = None):
        self.total_capital = total_capital
        self.risk_manager = risk_manager or RiskManager()
        self.positions: Dict[str, Position] = {}

    def open_position(self, ticker: str, shares: int, price: float,
                      stop_loss: float = None, take_profit: float = None) -> Position:
        """开仓"""
        # 计算止损止盈
        if stop_loss is None or take_profit is None:
            stop_loss, take_profit = self.risk_manager.set_stop_loss_take_profit(price)

        position = Position(
            ticker=ticker,
            shares=shares,
            cost_price=price,
            current_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_value=shares * price,
            profit_loss=0,
            profit_loss_pct=0
        )

        self.positions[ticker] = position
        logger.info(f"开仓: {ticker} {shares}股 @ {price:.2f}, 止损={stop_loss:.2f}, 止盈={take_profit:.2f}")

        return position

    def close_position(self, ticker: str, price: float) -> Dict:
        """平仓"""
        if ticker not in self.positions:
            return {"success": False, "message": "无此持仓"}

        position = self.positions[ticker]
        profit_loss = (price - position.cost_price) * position.shares
        profit_loss_pct = (price - position.cost_price) / position.cost_price

        result = {
            "success": True,
            "ticker": ticker,
            "shares": position.shares,
            "cost_price": position.cost_price,
            "sell_price": price,
            "profit_loss": profit_loss,
            "profit_loss_pct": profit_loss_pct
        }

        del self.positions[ticker]
        logger.info(f"平仓: {ticker} {position.shares}股 @ {price:.2f}, 盈亏={profit_loss:.2f} ({profit_loss_pct*100:.2f}%)")

        return result

    def update_prices(self, price_dict: Dict[str, float]):
        """更新持仓价格"""
        for ticker, price in price_dict.items():
            if ticker in self.positions:
                position = self.positions[ticker]
                position.current_price = price
                position.position_value = position.shares * price
                position.profit_loss = (price - position.cost_price) * position.shares
                position.profit_loss_pct = (price - position.cost_price) / position.cost_price

    def check_alerts(self) -> List[RiskAlert]:
        """检查风险预警"""
        alerts = []
        for position in self.positions.values():
            alert = self.risk_manager.check_stop_loss_take_profit(position)
            if alert:
                alerts.append(alert)
        return alerts

    def get_portfolio_summary(self) -> Dict:
        """获取组合摘要"""
        total_position_value = sum(p.position_value for p in self.positions.values())
        total_profit_loss = sum(p.profit_loss for p in self.positions.values())

        return {
            "total_capital": self.total_capital,
            "total_position_value": total_position_value,
            "cash": self.total_capital - total_position_value,
            "position_count": len(self.positions),
            "total_profit_loss": total_profit_loss,
            "positions": [
                {
                    "ticker": p.ticker,
                    "shares": p.shares,
                    "cost_price": p.cost_price,
                    "current_price": p.current_price,
                    "profit_loss_pct": p.profit_loss_pct * 100,
                    "stop_loss": p.stop_loss,
                    "take_profit": p.take_profit
                }
                for p in self.positions.values()
            ]
        }


if __name__ == "__main__":
    # 测试风险管理
    rm = RiskManager()

    # 计算风险指标
    test_returns = [0.01, -0.02, 0.03, -0.01, 0.02, 0.01, -0.03, 0.02, 0.01, -0.01]
    metrics = rm.calculate_risk_metrics(test_returns)
    print("风险指标:")
    print(f"  波动率: {metrics.volatility*100:.2f}%")
    print(f"  最大回撤: {metrics.max_drawdown*100:.2f}%")
    print(f"  夏普比率: {metrics.sharpe_ratio:.2f}")

    # 测试仓位管理
    pm = PositionManager(total_capital=1000000)

    # 开仓
    pm.open_position("600519", 100, 1700)
    pm.open_position("300750", 200, 200)

    # 更新价格
    pm.update_prices({"600519": 1750, "300750": 190})

    # 获取摘要
    summary = pm.get_portfolio_summary()
    print(f"\n组合摘要:")
    print(f"  总资产: {summary['total_capital']}")
    print(f"  持仓市值: {summary['total_position_value']}")
    print(f"  总盈亏: {summary['total_profit_loss']}")