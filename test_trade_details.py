#!/usr/bin/env python
"""
测试交易详情打印功能
"""
import sys
import os
sys.path.append('/workspace')

import pandas as pd
from quant_system.backtest.backtest_engine import BacktestEngine
from quant_system.utils.livermore_strategy import LivermoreStrategy, TradeSignal

def test_trade_details():
    """测试交易详情打印功能"""
    print("开始测试交易详情打印功能...")
    
    # 创建回测引擎
    engine = BacktestEngine(initial_capital=100000)
    
    # 模拟一个买入交易
    print("\n--- 测试买入交易 ---")
    buy_signal = TradeSignal(
        date='2024-01-01',
        symbol='000001.SZ',
        action='BUY',
        price=10.0,
        volume=1000,
        reason='Test buy signal',
        confidence=0.8
    )
    
    # 模拟市场数据（用于计算权益）
    market_data = {
        '000001.SZ': pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01']),
            'close': [10.0]
        })
    }
    
    success = engine.execute_trade(buy_signal, market_data)
    print(f"买入交易执行结果: {success}")
    
    # 模拟一个卖出交易
    print("\n--- 测试卖出交易 ---")
    sell_signal = TradeSignal(
        date='2024-01-02',
        symbol='000001.SZ',
        action='SELL',
        price=12.0,
        volume=1000,
        reason='Test sell signal',
        confidence=0.8
    )
    
    # 更新市场数据
    market_data['000001.SZ'] = pd.DataFrame({
        'date': pd.to_datetime(['2024-01-01', '2024-01-02']),
        'close': [10.0, 12.0]
    })
    
    success = engine.execute_trade(sell_signal, market_data)
    print(f"卖出交易执行结果: {success}")
    
    print("\n交易详情打印功能测试完成！")

if __name__ == "__main__":
    test_trade_details()