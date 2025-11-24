#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试数据获取效率优化
"""
import time
from quant_system.data.data_handler import DataHandler

def test_cache_efficiency():
    """测试缓存效率"""
    print("测试缓存效率...")
    data_handler = DataHandler(cache_dir='cache/test_cache')
    
    # 测试股票列表
    symbols = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']
    
    start_time = time.time()
    # 第一次获取数据（无缓存）
    market_data1 = data_handler.get_market_data(symbols, '2024-01-01', '2024-11-24', max_workers=4)
    first_call_time = time.time() - start_time
    print(f"首次获取数据耗时: {first_call_time:.2f}秒")
    
    # 检查获取到的数据
    for symbol, data in market_data1.items():
        if not data.empty:
            print(f"{symbol}: {len(data)} 条记录")
    
    start_time = time.time()
    # 第二次获取相同数据（有缓存）
    market_data2 = data_handler.get_market_data(symbols, '2024-01-01', '2024-11-24', max_workers=4)
    second_call_time = time.time() - start_time
    print(f"缓存获取数据耗时: {second_call_time:.2f}秒")
    
    print(f"缓存效率提升: {first_call_time/second_call_time:.2f}倍" if second_call_time > 0 else "几乎瞬间完成")
    
    data_handler.__del__()  # 清理资源
    print()

def test_parallel_efficiency():
    """测试并行处理效率"""
    print("测试并行处理效率...")
    data_handler = DataHandler(cache_dir='cache/test_cache')
    
    # 测试股票列表
    symbols = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000858.SZ', '002594.SZ']
    
    # 串行获取数据
    start_time = time.time()
    market_data_serial = {}
    for symbol in symbols:
        market_data_serial[symbol] = data_handler.get_daily_data(symbol, '2024-01-01', '2024-02-01')
    serial_time = time.time() - start_time
    print(f"串行获取数据耗时: {serial_time:.2f}秒")
    
    # 并行获取数据
    start_time = time.time()
    market_data_parallel = data_handler.get_market_data(symbols, '2024-01-01', '2024-02-01', max_workers=6)
    parallel_time = time.time() - start_time
    print(f"并行获取数据耗时: {parallel_time:.2f}秒")
    
    print(f"并行效率提升: {serial_time/parallel_time:.2f}倍" if parallel_time > 0 else "无法计算")
    
    data_handler.__del__()  # 清理资源
    print()

def test_rate_limiting():
    """测试频率限制"""
    print("测试频率限制...")
    data_handler = DataHandler(cache_dir='cache/test_cache')
    
    start_time = time.time()
    # 快速连续请求同一支股票的数据
    for i in range(3):
        data = data_handler.get_daily_data('000001.SZ', '2024-01-01', '2024-01-31')
        print(f"第{i+1}次请求完成")
    end_time = time.time()
    
    total_time = end_time - start_time
    print(f"3次请求总耗时: {total_time:.2f}秒")
    print(f"平均每次请求耗时: {total_time/3:.2f}秒")
    
    data_handler.__del__()  # 清理资源
    print()

if __name__ == "__main__":
    print("开始测试数据获取效率优化...")
    print("="*50)
    
    test_cache_efficiency()
    test_parallel_efficiency()
    test_rate_limiting()
    
    print("测试完成！")