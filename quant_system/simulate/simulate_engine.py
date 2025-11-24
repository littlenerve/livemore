"""
模拟交易引擎
提供接近实盘的模拟交易环境
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import time
from datetime import datetime, timedelta

from quant_system.utils.livermore_strategy import LivermoreStrategy, TradeSignal
from quant_system.config.settings import SIMULATION_CONFIG


@dataclass
class SimulationAccount:
    """模拟账户数据类"""
    cash: float
    positions: Dict[str, int]  # 股票代码: 股数
    position_values: Dict[str, float]  # 股票代码: 持仓价值
    total_value: float
    trade_log: List[Dict]
    initial_capital: float


class SimulationEngine:
    """
    模拟交易引擎
    提供实时模拟交易功能
    """
    
    def __init__(self, initial_capital: float = SIMULATION_CONFIG['initial_capital']):
        self.initial_capital = initial_capital
        self.account = SimulationAccount(
            cash=initial_capital,
            positions={},
            position_values={},
            total_value=initial_capital,
            trade_log=[],
            initial_capital=initial_capital
        )
        self.strategy = LivermoreStrategy()
        self.is_running = False
        
    def update_account_value(self, market_data: Dict[str, pd.DataFrame]):
        """
        更新账户价值
        :param market_data: 最新市场数据
        """
        # 更新持仓价值
        position_values = {}
        total_position_value = 0
        
        for symbol, quantity in self.account.positions.items():
            if symbol in market_data and not market_data[symbol].empty:
                current_price = market_data[symbol].iloc[-1]['close']
                position_value = quantity * current_price
                position_values[symbol] = position_value
                total_position_value += position_value
        
        self.account.position_values = position_values
        self.account.total_value = self.account.cash + total_position_value
    
    def execute_trade(self, signal: TradeSignal, current_price: float) -> bool:
        """
        执行模拟交易
        :param signal: 交易信号
        :param current_price: 当前价格
        :return: 交易是否成功
        """
        symbol = signal.symbol
        action = signal.action
        quantity = signal.volume  # 这里volume实际上是股数
        
        # 计算交易成本
        cost = quantity * current_price
        commission = max(cost * 0.0003, 5)  # 模拟佣金，最低5元
        
        if action == 'BUY':
            total_cost = cost + commission
            if total_cost > self.account.cash:
                print(f"资金不足，无法买入 {symbol}")
                return False
            
            # 执行买入
            if symbol in self.account.positions:
                self.account.positions[symbol] += quantity
            else:
                self.account.positions[symbol] = quantity
            
            self.account.cash -= total_cost
            
        elif action == 'SELL':
            if symbol not in self.account.positions or self.account.positions[symbol] < quantity:
                print(f"持仓不足，无法卖出 {symbol}")
                return False
            
            # 执行卖出
            revenue = quantity * current_price
            tax = revenue * 0.001  # 印花税
            total_revenue = revenue - commission - tax
            
            self.account.positions[symbol] -= quantity
            if self.account.positions[symbol] == 0:
                del self.account.positions[symbol]
            
            self.account.cash += total_revenue
        
        # 记录交易
        self.account.trade_log.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'action': action,
            'price': current_price,
            'quantity': quantity,
            'commission': commission,
            'reason': signal.reason,
            'account_value': self.account.total_value
        })
        
        print(f"模拟交易执行: {action} {symbol} {quantity}股 @ {current_price:.2f}, 原因: {signal.reason}")
        return True
    
    def get_account_summary(self) -> Dict:
        """
        获取账户摘要
        :return: 账户摘要信息
        """
        return {
            'cash': self.account.cash,
            'positions': self.account.positions,
            'position_values': self.account.position_values,
            'total_value': self.account.total_value,
            'total_return': (self.account.total_value - self.account.initial_capital) / self.account.initial_capital,
            'trade_count': len(self.account.trade_log)
        }
    
    def run_simulation(self, symbols: List[str], data_handler, start_date: str, end_date: str):
        """
        运行模拟交易
        :param symbols: 股票代码列表
        :param data_handler: 数据处理器
        :param start_date: 开始日期
        :param end_date: 结束日期
        """
        print("开始模拟交易...")
        self.is_running = True
        
        # 使用data_handler获取交易日历，将非交易日调整为最近的交易日
        adjusted_start_date = data_handler.get_previous_trading_date(start_date)
        adjusted_end_date = data_handler.get_previous_trading_date(end_date)
        
        # 获取历史数据以计算技术指标
        all_market_data = data_handler.get_market_data(symbols, adjusted_start_date, adjusted_end_date)
        
        # 模拟实时数据流
        # 这里简化处理，按日循环
        # 在实际应用中，这里会接收实时数据流
        
        # 获取所有交易日
        all_dates = set()
        for symbol in symbols:
            if symbol in all_market_data:
                dates = set(all_market_data[symbol]['date'])
                all_dates.update(dates)
        all_dates = sorted(list(all_dates))
        
        for current_date in all_dates:
            current_date_str = current_date.strftime('%Y-%m-%d')
            
            if not self.is_running:
                break
                
            # 为每只股票生成信号
            for symbol in symbols:
                if symbol not in all_market_data:
                    continue
                
                # 获取该股票到当前日期的数据
                stock_data = all_market_data[symbol][
                    all_market_data[symbol]['date'] <= current_date
                ].copy()
                
                if len(stock_data) < 50:  # 需要足够的数据来计算指标
                    continue
                
                # 计算技术指标
                stock_data = self.strategy.calculate_technical_indicators(stock_data)
                
                # 生成信号
                signals = self.strategy.generate_signals(stock_data, symbol)
                
                # 执行符合条件的信号
                for signal in signals:
                    if signal.date == current_date_str:
                        # 获取当前价格
                        current_data = all_market_data[symbol][
                            all_market_data[symbol]['date'] == current_date
                        ]
                        if not current_data.empty:
                            current_price = current_data.iloc[0]['close']
                            
                            # 根据信号置信度调整交易量
                            adjusted_volume = self.strategy.calculate_position_size(
                                current_price, 
                                self.account.total_value
                            )
                            signal.volume = min(signal.volume, adjusted_volume)
                            
                            self.execute_trade(signal, current_price)
            
            # 更新账户价值
            self.update_account_value(all_market_data)
            
            # 每日输出账户状态
            if len(all_dates) > 0 and all_dates.index(current_date) % 22 == 0:  # 每月输出一次
                summary = self.get_account_summary()
                print(f"日期: {current_date_str}, 账户总值: ¥{summary['total_value']:,.2f}, "
                      f"收益率: {summary['total_return']:.2%}")
            
            # 模拟时间延迟
            if SIMULATION_CONFIG['delay'] > 0:
                time.sleep(SIMULATION_CONFIG['delay'])
        
        print("模拟交易结束")
        self.print_simulation_report()
    
    def print_simulation_report(self):
        """
        打印模拟交易报告
        """
        summary = self.get_account_summary()
        print("\n" + "="*50)
        print("模拟交易报告")
        print("="*50)
        print(f"初始资金: ¥{self.account.initial_capital:,.2f}")
        print(f"最终资金: ¥{summary['total_value']:,.2f}")
        print(f"总收益率: {(summary['total_value'] - self.account.initial_capital) / self.account.initial_capital:.2%}")
        print(f"现金余额: ¥{summary['cash']:,.2f}")
        print(f"持仓数量: {len(summary['positions'])}")
        print(f"总交易次数: {summary['trade_count']}")
        print("\n当前持仓:")
        for symbol, quantity in summary['positions'].items():
            value = summary['position_values'].get(symbol, 0)
            print(f"  {symbol}: {quantity}股, 价值: ¥{value:,.2f}")
        print("="*50)
    
    def stop_simulation(self):
        """
        停止模拟交易
        """
        self.is_running = False
        print("已停止模拟交易")


class PaperTradingAPI:
    """
    模拟交易API接口
    用于连接模拟交易系统和策略
    """
    
    def __init__(self, simulation_engine: SimulationEngine):
        self.simulation_engine = simulation_engine
    
    def buy(self, symbol: str, quantity: int, price: float, reason: str = ""):
        """
        模拟买入
        """
        signal = TradeSignal(
            date=datetime.now().strftime('%Y-%m-%d'),
            symbol=symbol,
            action='BUY',
            price=price,
            volume=quantity,
            reason=reason,
            confidence=0.8
        )
        return self.simulation_engine.execute_trade(signal, price)
    
    def sell(self, symbol: str, quantity: int, price: float, reason: str = ""):
        """
        模拟卖出
        """
        signal = TradeSignal(
            date=datetime.now().strftime('%Y-%m-%d'),
            symbol=symbol,
            action='SELL',
            price=price,
            volume=quantity,
            reason=reason,
            confidence=0.8
        )
        return self.simulation_engine.execute_trade(signal, price)
    
    def get_portfolio(self):
        """
        获取投资组合
        """
        return self.simulation_engine.get_account_summary()
    
    def get_position(self, symbol: str):
        """
        获取特定股票持仓
        """
        if symbol in self.simulation_engine.account.positions:
            quantity = self.simulation_engine.account.positions[symbol]
            value = self.simulation_engine.account.position_values.get(symbol, 0)
            return {'symbol': symbol, 'quantity': quantity, 'value': value}
        return None