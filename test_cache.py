import os
import sys
import asyncio
import pandas as pd
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append('/workspace')

from quant_system.data.data_handler import DataHandler

def test_cache_functionality():
    """测试缓存功能"""
    print("开始测试缓存功能...")
    
    # 创建DataHandler实例
    handler = DataHandler()
    
    # 测试数据获取和缓存
    symbols = ['sz.000001', 'sz.000002']  # 平安银行、万科A
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"获取 {symbols} 从 {start_date} 到 {end_date} 的数据...")
    
    # 第一次获取数据（会从网络获取并缓存）
    print("第一次获取数据（从网络）...")
    data1 = handler.get_market_data(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"获取到 {len(data1)} 只股票的数据")
    for symbol, df in data1.items():
        if not df.empty:
            print(f"  {symbol}: {len(df)} 条记录, 日期范围: {df.index[0]} 到 {df.index[-1]}")
    
    # 检查缓存目录是否已创建
    cache_dir = os.path.expanduser('~/.quant_cache/daily_data/')
    print(f"\n检查缓存目录: {cache_dir}")
    if os.path.exists(cache_dir):
        cached_files = os.listdir(cache_dir)
        print(f"缓存文件: {cached_files}")
    else:
        print("缓存目录尚未创建，可能还未执行数据保存操作")
    
    # 第二次获取相同数据（应该从缓存加载）
    print("\n第二次获取相同数据（应该从缓存加载）...")
    import time
    start_time = time.time()
    data2 = handler.get_market_data(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date
    )
    end_time = time.time()
    
    print(f"第二次获取耗时: {end_time - start_time:.2f} 秒")
    print(f"数据是否相同: {all(data1[s].equals(data2[s]) for s in symbols if s in data1 and s in data2)}")
    
    # 验证缓存文件
    if os.path.exists(cache_dir):
        cached_files = os.listdir(cache_dir)
        print(f"\n缓存目录中的文件: {cached_files}")
        
        # 检查是否有缓存文件
        for file in cached_files:
            file_path = os.path.join(cache_dir, file)
            file_size = os.path.getsize(file_path)
            print(f"  {file}: {file_size} bytes")

if __name__ == "__main__":
    test_cache_functionality()