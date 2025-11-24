#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据获取效率优化的单元测试
测试代码逻辑和结构，不实际调用网络
"""
import os
import sys
import tempfile
import pandas as pd
from unittest.mock import patch, MagicMock
from quant_system.data.data_handler import DataHandler

def test_datahandler_initialization():
    """测试DataHandler初始化"""
    print("测试DataHandler初始化...")
    
    # 创建临时目录作为缓存目录
    with tempfile.TemporaryDirectory() as temp_dir:
        data_handler = DataHandler(cache_dir=temp_dir)
        
        # 验证初始化参数
        assert data_handler.cache_dir == temp_dir
        assert hasattr(data_handler, 'data_cache')
        assert hasattr(data_handler, 'last_request_time')
        assert hasattr(data_handler, 'min_request_interval')
        assert data_handler.min_request_interval == 0.5
        
        print("✓ DataHandler初始化测试通过")
        data_handler.__del__()  # 清理资源

def test_cache_methods():
    """测试缓存相关方法"""
    print("测试缓存相关方法...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_handler = DataHandler(cache_dir=temp_dir)
        
        # 测试缓存键生成
        cache_key = data_handler._get_cache_key('000001.SZ', '2024-01-01', '2024-12-31')
        assert isinstance(cache_key, str)
        assert len(cache_key) == 32  # MD5哈希长度
        print("✓ 缓存键生成测试通过")
        
        # 测试内存缓存
        test_data = pd.DataFrame({'date': pd.date_range('2024-01-01', periods=5), 'close': [1, 2, 3, 4, 5]})
        data_handler._save_to_cache('000001.SZ', '2024-01-01', '2024-12-31', test_data)
        
        # 验证数据已保存到内存缓存
        cached = data_handler._load_from_cache('000001.SZ', '2024-01-01', '2024-12-31')
        assert cached is not None
        assert len(cached) == 5
        print("✓ 内存缓存测试通过")
        
        data_handler.__del__()  # 清理资源

def test_parallel_method_signature():
    """测试并行方法的签名"""
    print("测试并行方法的签名...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_handler = DataHandler(cache_dir=temp_dir)
        
        # 检查get_market_data方法的参数
        import inspect
        sig = inspect.signature(data_handler.get_market_data)
        params = list(sig.parameters.keys())
        
        assert 'max_workers' in params
        assert sig.parameters['max_workers'].default == 5
        print("✓ 并行方法签名测试通过")
        
        data_handler.__del__()  # 清理资源

def test_rate_limiting():
    """测试频率限制功能"""
    print("测试频率限制功能...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_handler = DataHandler(cache_dir=temp_dir)
        
        # 测试频率限制方法
        import time
        data_handler._enforce_rate_limit()  # 第一次调用
        time_before = data_handler.last_request_time
        
        # 立即再次调用，应该等待
        data_handler._enforce_rate_limit()
        time_after = data_handler.last_request_time
        
        # 验证时间间隔
        assert time_after >= time_before + data_handler.min_request_interval - 0.1  # 允许一点误差
        print("✓ 频率限制功能测试通过")
        
        data_handler.__del__()  # 清理资源

def test_backward_compatibility():
    """测试向后兼容性"""
    print("测试向后兼容性...")
    
    # 测试旧的初始化方式是否仍然工作
    data_handler = DataHandler()
    assert hasattr(data_handler, 'cache_dir')
    assert data_handler.cache_dir == 'cache'
    print("✓ 向后兼容性测试通过")
    
    data_handler.__del__()  # 清理资源

def test_get_daily_data_method():
    """测试get_daily_data方法结构"""
    print("测试get_daily_data方法结构...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_handler = DataHandler(cache_dir=temp_dir)
        
        # 使用mock来模拟网络请求，避免实际调用
        with patch.object(data_handler, '_load_from_cache', return_value=None):
            with patch.object(data_handler, '_enforce_rate_limit') as mock_rate_limit:
                with patch('baostock.query_history_k_data_plus') as mock_bs:
                    # 模拟baostock返回空数据
                    mock_result = MagicMock()
                    mock_result.error_code = '0'
                    mock_result.next.return_value = False
                    mock_result.fields = ['date', 'open', 'high', 'low', 'close', 'volume']
                    mock_bs.return_value = mock_result
                    
                    # 调用方法
                    result = data_handler.get_daily_data('000001.SZ', '2024-01-01', '2024-12-31')
                    
                    # 验证频率限制被调用
                    assert mock_rate_limit.called
                    print("✓ get_daily_data方法结构测试通过")
        
        data_handler.__del__()  # 清理资源

if __name__ == "__main__":
    print("开始数据获取效率优化的单元测试...")
    print("="*50)
    
    test_datahandler_initialization()
    test_cache_methods()
    test_parallel_method_signature()
    test_rate_limiting()
    test_backward_compatibility()
    test_get_daily_data_method()
    
    print("="*50)
    print("所有单元测试通过！")
    print("\n优化总结：")
    print("1. 添加了内存和文件双重缓存机制")
    print("2. 实现了并行数据获取功能")
    print("3. 增加了请求频率限制")
    print("4. 保持了向后兼容性")
    print("5. 优化了数据处理流程")