"""
A股分析回测模块
验证分析策略的历史表现
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


@dataclass
class BacktestPosition:
    """回测持仓"""
    ticker: str
    shares: int
    cost_price: float
    current_price: float
    market_value: float
    profit_loss: float
    profit_loss_pct: float


@dataclass
class BacktestTrade:
    """回测交易记录"""
    date: str
    ticker: str
    action: str  # buy/sell
    shares: int
    price: float
    amount: float
    commission: float
    reason: str


@dataclass
class BacktestResult:
    """回测结果"""
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    sharpe_ratio: Optional[float] = None
    positions: List[BacktestPosition] = field(default_factory=list)
    trades: List[BacktestTrade] = field(default_factory=list)
    daily_values: List[Dict] = field(default_factory=list)


class AStockBacktester:
    """A股分析回测器"""

    def __init__(self, initial_capital: float = 1000000, commission_rate: float = 0.0003,
                 stamp_duty: float = 0.001, slippage: float = 0.001):
        """
        初始化回测器

        参数:
            initial_capital: 初始资金
            commission_rate: 佣金费率
            stamp_duty: 印花税（仅卖出）
            slippage: 滑点
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_duty = stamp_duty
        self.slippage = slippage

        # 回测状态
        self.cash = initial_capital
        self.positions: Dict[str, BacktestPosition] = {}
        self.trades: List[BacktestTrade] = []
        self.daily_values: List[Dict] = []

    def run_backtest(self, signals: List[Dict], price_data: Dict[str, List[Dict]],
                     start_date: str, end_date: str) -> BacktestResult:
        """
        运行回测

        参数:
            signals: 交易信号列表 [{date, ticker, action, shares, reason}]
            price_data: 价格数据 {ticker: [{date, open, close, high, low, volume}]}
            start_date: 开始日期
            end_date: 结束日期
        """
        # 重置状态
        self.cash = self.initial_capital
        self.positions = {}
        self.trades = []
        self.daily_values = []

        # 构建日期序列
        dates = self._get_trading_dates(price_data, start_date, end_date)

        # 按日期处理
        for date in dates:
            # 执行当天的交易信号
            daily_signals = [s for s in signals if s['date'] == date]
            for signal in daily_signals:
                self._execute_signal(signal, price_data, date)

            # 更新持仓市值
            self._update_positions(price_data, date)

            # 记录每日净值
            self._record_daily_value(date)

        # 计算结果
        return self._calculate_result(start_date, end_date)

    def _get_trading_dates(self, price_data: Dict[str, List[Dict]], start_date: str, end_date: str) -> List[str]:
        """获取交易日期序列"""
        dates = set()
        for ticker, prices in price_data.items():
            for p in prices:
                if start_date <= p['date'] <= end_date:
                    dates.add(p['date'])
        return sorted(list(dates))

    def _execute_signal(self, signal: Dict, price_data: Dict[str, List[Dict]], date: str):
        """执行交易信号"""
        ticker = signal['ticker']
        action = signal['action']
        shares = signal.get('shares', 100)  # 默认100股
        reason = signal.get('reason', '')

        # 获取当日价格
        price = self._get_price(price_data, ticker, date)
        if price is None:
            return

        if action == 'buy':
            self._buy(ticker, shares, price, date, reason)
        elif action == 'sell':
            self._sell(ticker, shares, price, date, reason)

    def _buy(self, ticker: str, shares: int, price: float, date: str, reason: str):
        """买入"""
        # 计算实际成交价（含滑点）
        actual_price = price * (1 + self.slippage)
        amount = shares * actual_price
        commission = max(amount * self.commission_rate, 5)  # 最低5元

        total_cost = amount + commission

        if total_cost > self.cash:
            # 资金不足，调整股数
            shares = int((self.cash - 5) / (actual_price * (1 + self.commission_rate)))
            shares = (shares // 100) * 100  # A股一手100股
            if shares < 100:
                return
            amount = shares * actual_price
            commission = max(amount * self.commission_rate, 5)
            total_cost = amount + commission

        # 更新现金
        self.cash -= total_cost

        # 更新持仓
        if ticker in self.positions:
            pos = self.positions[ticker]
            total_shares = pos.shares + shares
            total_cost_basis = pos.cost_price * pos.shares + amount
            pos.shares = total_shares
            pos.cost_price = total_cost_basis / total_shares
        else:
            self.positions[ticker] = BacktestPosition(
                ticker=ticker,
                shares=shares,
                cost_price=actual_price,
                current_price=actual_price,
                market_value=amount,
                profit_loss=0,
                profit_loss_pct=0
            )

        # 记录交易
        self.trades.append(BacktestTrade(
            date=date,
            ticker=ticker,
            action='buy',
            shares=shares,
            price=actual_price,
            amount=amount,
            commission=commission,
            reason=reason
        ))

    def _sell(self, ticker: str, shares: int, price: float, date: str, reason: str):
        """卖出"""
        if ticker not in self.positions:
            return

        pos = self.positions[ticker]
        shares = min(shares, pos.shares)

        # 计算实际成交价（含滑点）
        actual_price = price * (1 - self.slippage)
        amount = shares * actual_price
        commission = max(amount * self.commission_rate, 5)
        stamp_duty = amount * self.stamp_duty

        total_cost = commission + stamp_duty
        net_amount = amount - total_cost

        # 更新现金
        self.cash += net_amount

        # 更新持仓
        pos.shares -= shares
        if pos.shares == 0:
            del self.positions[ticker]

        # 记录交易
        self.trades.append(BacktestTrade(
            date=date,
            ticker=ticker,
            action='sell',
            shares=shares,
            price=actual_price,
            amount=amount,
            commission=total_cost,
            reason=reason
        ))

    def _get_price(self, price_data: Dict[str, List[Dict]], ticker: str, date: str) -> Optional[float]:
        """获取指定日期的价格"""
        if ticker not in price_data:
            return None

        for p in price_data[ticker]:
            if p['date'] == date:
                return p.get('close', p.get('price'))

        return None

    def _update_positions(self, price_data: Dict[str, List[Dict]], date: str):
        """更新持仓市值"""
        for ticker, pos in self.positions.items():
            price = self._get_price(price_data, ticker, date)
            if price:
                pos.current_price = price
                pos.market_value = pos.shares * price
                pos.profit_loss = pos.market_value - pos.shares * pos.cost_price
                pos.profit_loss_pct = pos.profit_loss / (pos.shares * pos.cost_price)

    def _record_daily_value(self, date: str):
        """记录每日净值"""
        total_value = self.cash + sum(p.market_value for p in self.positions.values())

        self.daily_values.append({
            'date': date,
            'cash': self.cash,
            'position_value': sum(p.market_value for p in self.positions.values()),
            'total_value': total_value,
            'positions': len(self.positions)
        })

    def _calculate_result(self, start_date: str, end_date: str) -> BacktestResult:
        """计算回测结果"""
        if not self.daily_values:
            return BacktestResult(
                start_date=start_date,
                end_date=end_date,
                initial_capital=self.initial_capital,
                final_capital=self.initial_capital,
                total_return=0,
                annual_return=0,
                max_drawdown=0,
                win_rate=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0
            )

        final_value = self.daily_values[-1]['total_value']
        total_return = (final_value - self.initial_capital) / self.initial_capital

        # 计算年化收益
        days = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days
        annual_return = (1 + total_return) ** (365 / max(days, 1)) - 1 if days > 0 else 0

        # 计算最大回撤
        max_drawdown = self._calculate_max_drawdown()

        # 计算胜率
        winning_trades, losing_trades = self._calculate_win_rate()

        # 计算夏普比率
        sharpe_ratio = self._calculate_sharpe_ratio()

        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=final_value,
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            win_rate=winning_trades / (winning_trades + losing_trades) if (winning_trades + losing_trades) > 0 else 0,
            total_trades=len(self.trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            sharpe_ratio=sharpe_ratio,
            positions=list(self.positions.values()),
            trades=self.trades,
            daily_values=self.daily_values
        )

    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self.daily_values:
            return 0

        values = [v['total_value'] for v in self.daily_values]
        peak = values[0]
        max_dd = 0

        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            max_dd = max(max_dd, dd)

        return max_dd

    def _calculate_win_rate(self) -> Tuple[int, int]:
        """计算胜率"""
        winning = 0
        losing = 0

        # 配对买卖交易
        buy_trades = {}
        for trade in self.trades:
            if trade.action == 'buy':
                if trade.ticker not in buy_trades:
                    buy_trades[trade.ticker] = []
                buy_trades[trade.ticker].append(trade)
            elif trade.action == 'sell' and trade.ticker in buy_trades:
                buys = buy_trades[trade.ticker]
                if buys:
                    buy = buys.pop(0)
                    profit = (trade.price - buy.price) * trade.shares
                    if profit > 0:
                        winning += 1
                    else:
                        losing += 1

        return winning, losing

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.03) -> Optional[float]:
        """计算夏普比率"""
        if len(self.daily_values) < 2:
            return None

        values = [v['total_value'] for v in self.daily_values]
        returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]

        if not returns:
            return None

        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_return = variance ** 0.5

        if std_return == 0:
            return None

        # 年化
        annual_avg_return = avg_return * 252
        annual_std = std_return * (252 ** 0.5)

        return (annual_avg_return - risk_free_rate) / annual_std


def print_backtest_result(result: BacktestResult):
    """打印回测结果"""
    print("\n" + "=" * 60)
    print("回测结果报告")
    print("=" * 60)

    print(f"\n回测区间: {result.start_date} ~ {result.end_date}")
    print(f"初始资金: {result.initial_capital:,.2f}")
    print(f"最终资金: {result.final_capital:,.2f}")

    print("\n收益指标:")
    print(f"  总收益率: {result.total_return * 100:.2f}%")
    print(f"  年化收益: {result.annual_return * 100:.2f}%")
    print(f"  最大回撤: {result.max_drawdown * 100:.2f}%")

    print("\n交易统计:")
    print(f"  总交易次数: {result.total_trades}")
    print(f"  盈利次数: {result.winning_trades}")
    print(f"  亏损次数: {result.losing_trades}")
    print(f"  胜率: {result.win_rate * 100:.2f}%")

    if result.sharpe_ratio:
        print(f"  夏普比率: {result.sharpe_ratio:.2f}")

    print("\n当前持仓:")
    for pos in result.positions:
        print(f"  {pos.ticker}: {pos.shares}股, 成本{pos.cost_price:.2f}, "
              f"现价{pos.current_price:.2f}, 盈亏{pos.profit_loss_pct * 100:.2f}%")

    print("=" * 60)


if __name__ == "__main__":
    # 测试回测
    backtester = AStockBacktester(initial_capital=1000000)

    # 模拟数据
    signals = [
        {'date': '2024-01-02', 'ticker': '600519', 'action': 'buy', 'shares': 100, 'reason': '看涨信号'},
        {'date': '2024-01-10', 'ticker': '600519', 'action': 'sell', 'shares': 100, 'reason': '止盈'},
    ]

    price_data = {
        '600519': [
            {'date': '2024-01-02', 'close': 1700},
            {'date': '2024-01-03', 'close': 1710},
            {'date': '2024-01-04', 'close': 1720},
            {'date': '2024-01-05', 'close': 1715},
            {'date': '2024-01-08', 'close': 1730},
            {'date': '2024-01-09', 'close': 1740},
            {'date': '2024-01-10', 'close': 1750},
        ]
    }

    result = backtester.run_backtest(signals, price_data, '2024-01-02', '2024-01-10')
    print_backtest_result(result)
