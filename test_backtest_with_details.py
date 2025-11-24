#!/usr/bin/env python
"""
测试回测引擎中的交易详情打印功能
"""
import sys
import os
sys.path.append('/workspace')

import pandas as pd
from quant_system.backtest.backtest_engine import BacktestEngine
from quant_system.utils.livermore_strategy import LivermoreStrategy

def test_backtest_with_details():
    """测试回测引擎中的交易详情打印功能"""
    print("开始测试回测引擎中的交易详情打印功能...")
    
    # 创建回测引擎
    engine = BacktestEngine(initial_capital=100000)
    
    # 创建模拟数据 - 有明显趋势的数据
    dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='D')
    # 过滤掉周末，只保留工作日
    dates = dates[dates.weekday < 5]  # 0-4 代表周一到周五
    
    # 创建有趋势的数据，确保长度一致
    n_days = len(dates)
    prices = [10.0, 10.2, 10.5, 10.8, 11.2, 11.5, 12.0, 12.5, 13.0, 13.5][:n_days]
    volumes = [1000000] * n_days  # 成交量
    
    df = pd.DataFrame({
        'date': dates,
        'open': [p*0.99 for p in prices],
        'high': [p*1.02 for p in prices],
        'low': [p*0.98 for p in prices],
        'close': prices,
        'volume': volumes,
        'code': '000001.SZ'
    })
    
    # 添加一些基本的技术指标来满足策略要求
    df['ma_10'] = df['close'].rolling(window=3).mean()  # 简化版
    df['ma_20'] = df['close'].rolling(window=5).mean()  # 简化版
    df['volatility_20'] = df['close'].rolling(window=5).std() / df['close'].shift(1)
    df['pct_change'] = df['close'].pct_change()
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(window=10).mean()
    df['support'] = df['close'].rolling(window=5).min()
    df['resistance'] = df['close'].rolling(window=5).max()
    df['trend_strength'] = (df['ma_10'] - df['ma_20']) / df['close']
    
    # 用数据填充缺失值
    df = df.fillna(method='bfill').fillna(method='ffill')
    
    market_data = {
        '000001.SZ': df
    }
    
    print(f"模拟数据创建完成，共 {len(dates)} 个交易日")
    print("数据预览:")
    print(df[['date', 'close']].head(10))
    
    # 运行回测
    print("\n开始运行回测...")
    result = engine.run_backtest(
        symbols=['000001.SZ'],
        market_data=market_data,
        start_date='2024-01-01',
        end_date='2024-01-10'
    )
    
    print(f"\n回测完成！")
    print(f"初始资金: ¥{engine.initial_capital:,.2f}")
    print(f"最终资金: ¥{result.final_equity:,.2f}")
    print(f"总收益率: {result.total_return:.2%}")
    print(f"总交易次数: {result.total_trades}")
    
    # 打印交易日志
    if engine.trade_log:
        print(f"\n交易日志 ({len(engine.trade_log)} 条记录):")
        for i, trade in enumerate(engine.trade_log):
            print(f"  {i+1}. {trade['date']} - {trade['action']} {trade['symbol']} {trade['quantity']}股 "
                  f"@ ¥{trade['price']:.2f}, 理由: {trade['reason']}")
    else:
        print("\n没有交易记录")
    
    print("\n回测引擎交易详情打印功能测试完成！")

if __name__ == "__main__":
    test_backtest_with_details()