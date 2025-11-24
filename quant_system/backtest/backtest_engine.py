"""
回测引擎
实现完整的回测功能
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

from quant_system.utils.livermore_strategy import LivermoreStrategy, TradeSignal
from quant_system.config.settings import BACKTEST_CONFIG
from quant_system.data.data_handler import DataHandler


@dataclass
class Position:
    """持仓数据类"""
    symbol: str
    quantity: int
    avg_price: float
    entry_date: str
    current_price: float = 0.0
    unrealized_pnl: float = 0.0


@dataclass
class BacktestResult:
    """回测结果数据类"""
    total_return: float
    annual_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    final_equity: float
    trade_log: List[Dict]


class BacktestEngine:
    """
    回测引擎
    支持多股票、多策略的回测
    """
    
    def __init__(self, initial_capital: float = BACKTEST_CONFIG['initial_capital']):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_log: List[Dict] = []
        self.equity_curve: List[Tuple[str, float]] = []  # (date, equity)
        self.strategy = LivermoreStrategy()
        self.data_handler = DataHandler(cache_dir='cache/backtest_cache')
        
    def reset(self):
        """重置回测状态"""
        self.current_capital = self.initial_capital
        self.positions = {}
        self.trade_log = []
        self.equity_curve = []
    
    def calculate_equity(self, market_data: Dict[str, pd.DataFrame], current_date: str) -> float:
        """
        计算当前权益
        :param market_data: 市场数据
        :param current_date: 当前日期
        :return: 当前权益
        """
        equity = self.current_capital  # 现金部分
        
        # 加上持仓部分
        for symbol, position in self.positions.items():
            if symbol in market_data:
                # 获取当前价格
                current_data = market_data[symbol][
                    market_data[symbol]['date'] == pd.to_datetime(current_date)
                ]
                if not current_data.empty:
                    current_price = current_data.iloc[0]['close']
                    equity += position.quantity * current_price
        
        return equity
    
    def execute_trade(self, signal: TradeSignal, market_data: Dict[str, pd.DataFrame]) -> bool:
        """
        执行交易
        :param signal: 交易信号
        :param market_data: 市场数据
        :return: 交易是否成功
        """
        symbol = signal.symbol
        action = signal.action
        price = signal.price
        volume = signal.volume  # 这里volume实际上是股数
        
        # 获取实际可用的股数（确保是100的倍数且不超过持仓）
        if action == 'BUY':
            # 计算实际可购买股数
            max_affordable = int(self.current_capital / (price * (1 + BACKTEST_CONFIG['commission_rate'])))
            actual_volume = min(volume, max_affordable // 100 * 100)  # 确保是100的倍数
            
            if actual_volume <= 0:
                print(f"[DEBUG] {signal.date} - {symbol}: 资金不足，无法买入")
                return False  # 资金不足
            
            cost = actual_volume * price
            commission = max(cost * BACKTEST_CONFIG['commission_rate'], 5)  # 最低5元佣金
            total_cost = cost + commission
            
            if total_cost > self.current_capital:
                print(f"[DEBUG] {signal.date} - {symbol}: 资金不足，所需成本 ¥{total_cost:,.2f}，当前资金 ¥{self.current_capital:,.2f}")
                return False  # 资金不足
            
            # 执行买入
            if symbol in self.positions:
                # 加仓
                old_position = self.positions[symbol]
                new_quantity = old_position.quantity + actual_volume
                new_avg_price = (old_position.avg_price * old_position.quantity + price * actual_volume) / new_quantity
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=new_quantity,
                    avg_price=new_avg_price,
                    entry_date=old_position.entry_date  # 保持原有入场日期
                )
                print(f"[BUY] {signal.date} - {symbol}: 加仓 {actual_volume} 股，价格 ¥{price:.2f}，理由: {signal.reason}")
                print(f"      持仓变化: {old_position.quantity} → {new_quantity} 股，平均成本 ¥{new_avg_price:.2f}")
            else:
                # 新建仓位
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=actual_volume,
                    avg_price=price,
                    entry_date=signal.date
                )
                print(f"[BUY] {signal.date} - {symbol}: 新建仓位 {actual_volume} 股，价格 ¥{price:.2f}，理由: {signal.reason}")
            
            self.current_capital -= total_cost
            print(f"      成本: ¥{cost:.2f}, 佣金: ¥{commission:.2f}, 总支出: ¥{total_cost:.2f}")
            print(f"      交易后资金: ¥{self.current_capital:.2f}")
            
        elif action == 'SELL':
            if symbol not in self.positions or self.positions[symbol].quantity == 0:
                print(f"[DEBUG] {signal.date} - {symbol}: 无持仓可卖")
                return False  # 无持仓可卖
            
            # 确保卖出股数不超过持仓
            actual_volume = min(volume, self.positions[symbol].quantity)
            revenue = actual_volume * price
            commission = max(revenue * BACKTEST_CONFIG['commission_rate'], 5)  # 买入时佣金
            tax = revenue * 0.001  # 卖出时印花税
            total_revenue = revenue - commission - tax
            
            # 执行卖出
            remaining_quantity = self.positions[symbol].quantity - actual_volume
            if remaining_quantity == 0:
                old_position = self.positions[symbol]
                profit = (price - old_position.avg_price) * actual_volume
                print(f"[SELL] {signal.date} - {symbol}: 清仓 {actual_volume} 股，价格 ¥{price:.2f}，理由: {signal.reason}")
                print(f"      入场价: ¥{old_position.avg_price:.2f}, 盈亏: ¥{profit:.2f} ({profit/actual_volume:.2f}/股)")
                del self.positions[symbol]
            else:
                # 减少仓位
                old_position = self.positions[symbol]
                profit = (price - old_position.avg_price) * actual_volume
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=remaining_quantity,
                    avg_price=old_position.avg_price,
                    entry_date=old_position.entry_date
                )
                print(f"[SELL] {signal.date} - {symbol}: 减仓 {actual_volume} 股，价格 ¥{price:.2f}，理由: {signal.reason}")
                print(f"      入场价: ¥{old_position.avg_price:.2f}, 盈亏: ¥{profit:.2f} ({profit/actual_volume:.2f}/股)")
                print(f"      持仓变化: {old_position.quantity} → {remaining_quantity} 股")
            
            self.current_capital += total_revenue
            print(f"      收入: ¥{revenue:.2f}, 佣金: ¥{commission:.2f}, 印花税: ¥{tax:.2f}，总收入: ¥{total_revenue:.2f}")
            print(f"      交易后资金: ¥{self.current_capital:.2f}")
        
        # 记录交易日志
        trade_record = {
            'date': signal.date,
            'symbol': symbol,
            'action': action,
            'price': price,
            'quantity': actual_volume,
            'commission': commission,
            'reason': signal.reason,
            'capital_after': self.current_capital,
            'equity': self.calculate_equity(market_data, signal.date)
        }
        self.trade_log.append(trade_record)
        
        # 打印交易后的持仓和资金情况
        current_equity = self.calculate_equity(market_data, signal.date)
        print(f"      当前权益: ¥{current_equity:.2f}")
        print(f"      持仓股票: {list(self.positions.keys()) if self.positions else '无'}")
        print("-" * 80)
        
        return True
    
    def run_backtest(self, 
                    symbols: List[str], 
                    market_data: Dict[str, pd.DataFrame],
                    start_date: str,
                    end_date: str) -> BacktestResult:
        """
        运行回测
        :param symbols: 股票代码列表
        :param market_data: 市场数据
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 回测结果
        """
        self.reset()
        
        # 将日期字符串转换为datetime
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # 获取所有交易日
        all_dates = set()
        for symbol in symbols:
            if symbol in market_data:
                dates = set(market_data[symbol]['date'])
                all_dates.update(dates)
        all_dates = sorted([d for d in all_dates if start_dt <= d <= end_dt])
        
        # 按日期顺序回测
        for current_date in all_dates:
            current_date_str = current_date.strftime('%Y-%m-%d')
            
            daily_trades = 0  # 记录当日交易数
            
            # 为每只股票生成信号
            for symbol in symbols:
                if symbol not in market_data:
                    continue
                
                # 获取该股票到当前日期的数据
                stock_data = market_data[symbol][
                    market_data[symbol]['date'] <= current_date
                ].copy()
                
                if len(stock_data) < 50:  # 需要足够的数据来计算指标
                    continue
                
                # 计算技术指标
                stock_data = self.data_handler.calculate_technical_indicators(stock_data)
                
                # 生成信号
                signals = self.strategy.generate_signals(stock_data, symbol)
                
                # 执行符合条件的信号
                for signal in signals:
                    if signal.date == current_date_str:
                        # 根据信号置信度调整交易量
                        adjusted_volume = self.strategy.calculate_position_size(
                            signal.price, 
                            self.current_capital
                        )
                        signal.volume = min(signal.volume, adjusted_volume)
                        
                        success = self.execute_trade(signal, market_data)
                        if success:
                            daily_trades += 1
            
            # 只在有交易发生时打印当日汇总
            if daily_trades > 0:
                current_equity = self.calculate_equity(market_data, current_date_str)
                print(f"\n{current_date_str} 交易日汇总: 完成 {daily_trades} 笔交易, 当前权益: ¥{current_equity:,.2f}")
            
            # 记录权益曲线
            current_equity = self.calculate_equity(market_data, current_date_str)
            self.equity_curve.append((current_date_str, current_equity))
        
        # 计算回测结果
        return self.calculate_backtest_metrics()
    
    def calculate_backtest_metrics(self) -> BacktestResult:
        """
        计算回测指标
        """
        if not self.equity_curve:
            return BacktestResult(
                total_return=0.0, annual_return=0.0, volatility=0.0, 
                sharpe_ratio=0.0, max_drawdown=0.0, win_rate=0.0, 
                profit_factor=0.0, total_trades=0, winning_trades=0, 
                losing_trades=0, final_equity=self.initial_capital, 
                trade_log=[]
            )
        
        # 转换权益曲线为收益率序列
        equity_df = pd.DataFrame(self.equity_curve, columns=['date', 'equity'])
        equity_df['return'] = equity_df['equity'].pct_change().fillna(0)
        
        # 总收益率
        total_return = (equity_df['equity'].iloc[-1] - self.initial_capital) / self.initial_capital
        
        # 年化收益率
        days = len(equity_df)
        annual_return = ((1 + total_return) ** (365.25 / days)) - 1 if days > 0 else 0
        
        # 波动率
        volatility = equity_df['return'].std() * np.sqrt(252)  # 年化波动率
        
        # 夏普比率
        risk_free_rate = 0.03  # 假设无风险利率3%
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility != 0 else 0
        
        # 最大回撤
        equity_df['cummax'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['cummax']) / equity_df['cummax']
        max_drawdown = abs(equity_df['drawdown'].min())
        
        # 交易统计
        trade_df = pd.DataFrame(self.trade_log)
        total_trades = len(trade_df)
        winning_trades = 0
        losing_trades = 0
        total_profit = 0
        total_loss = 0
        
        if not trade_df.empty and 'action' in trade_df.columns:
            # 分析卖出交易的盈亏
            sell_trades = trade_df[trade_df['action'] == 'SELL']
            for _, trade in sell_trades.iterrows():
                # 找到对应的买入交易
                symbol = trade['symbol']
                sell_price = trade['price']
                
                # 简化处理：查找最近的买入交易
                buy_trades = trade_df[
                    (trade_df['action'] == 'BUY') & 
                    (trade_df['symbol'] == symbol) &
                    (pd.to_datetime(trade_df['date']) <= pd.to_datetime(trade['date']))
                ]
                
                if not buy_trades.empty:
                    buy_price = buy_trades.iloc[-1]['price']
                    profit = (sell_price - buy_price) * trade['quantity']
                    
                    if profit > 0:
                        winning_trades += 1
                        total_profit += profit
                    else:
                        losing_trades += 1
                        total_loss += abs(profit)
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            final_equity=equity_df['equity'].iloc[-1],
            trade_log=self.trade_log
        )
    
    def plot_equity_curve(self, figsize=(12, 6)):
        """
        绘制权益曲线
        """
        if not self.equity_curve:
            print("没有回测数据可供绘图")
            return
        
        equity_df = pd.DataFrame(self.equity_curve, columns=['date', 'equity'])
        equity_df['date'] = pd.to_datetime(equity_df['date'])
        
        plt.figure(figsize=figsize)
        plt.plot(equity_df['date'], equity_df['equity'], label='Equity Curve', linewidth=2)
        plt.axhline(y=self.initial_capital, color='r', linestyle='--', label='Initial Capital')
        plt.title('Equity Curve')
        plt.xlabel('Date')
        plt.ylabel('Equity (¥)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    def print_backtest_report(self, result: BacktestResult):
        """
        打印回测报告
        """
        print("="*50)
        print("回测报告")
        print("="*50)
        print(f"初始资金: ¥{self.initial_capital:,.2f}")
        print(f"最终资金: ¥{result.final_equity:,.2f}")
        print(f"总收益率: {result.total_return:.2%}")
        print(f"年化收益率: {result.annual_return:.2%}")
        print(f"波动率: {result.volatility:.2%}")
        print(f"夏普比率: {result.sharpe_ratio:.2f}")
        print(f"最大回撤: {result.max_drawdown:.2%}")
        print(f"胜率: {result.win_rate:.2%}")
        print(f"盈利因子: {result.profit_factor:.2f}")
        print(f"总交易次数: {result.total_trades}")
        print(f"盈利交易: {result.winning_trades}")
        print(f"亏损交易: {result.losing_trades}")
        print("="*50)