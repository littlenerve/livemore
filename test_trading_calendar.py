#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试baostock交易日历功能
"""
import sys
import os
sys.path.append('/workspace')

from quant_system.data.data_handler import DataHandler

def test_trading_calendar():
    """测试交易日历功能"""
    print("正在测试baostock交易日历功能...")
    
    # 创建DataHandler实例
    data_handler = DataHandler()
    
    # 测试获取交易日历
    print("\n1. 测试获取交易日历:")
    trading_dates = data_handler.get_trading_dates('2023-01-01', '2023-01-10')
    print(f"2023-01-01到2023-01-10的交易日: {trading_dates}")
    
    # 测试获取前一个交易日（输入非交易日）
    print("\n2. 测试非交易日调整功能:")
    weekend_date = '2023-01-01'  # 周日
    previous_trading_date = data_handler.get_previous_trading_date(weekend_date)
    print(f"输入日期: {weekend_date} (周日)")
    print(f"最近的交易日: {previous_trading_date}")
    
    # 测试获取股票数据（使用非交易日）
    print("\n3. 测试股票数据获取（使用非交易日）:")
    stock_data = data_handler.get_daily_data('sh.000001', '2023-01-01', '2023-01-10')
    print(f"获取到上证指数数据，共{len(stock_data)}条记录")
    if not stock_data.empty:
        print(f"数据日期范围: {stock_data['date'].min()} 到 {stock_data['date'].max()}")
    
    # 清理资源
    data_handler.__del__()
    
    print("\n交易日历功能测试完成！")

if __name__ == "__main__":
    test_trading_calendar()