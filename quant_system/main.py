"""
量化交易系统主入口
支持回测、模拟和实盘交易
"""
import pandas as pd
import numpy as np
from typing import List
import argparse
import os
import yaml

from quant_system.data.data_handler import DataHandler
from quant_system.backtest.backtest_engine import BacktestEngine
from quant_system.simulate.simulate_engine import SimulationEngine
from quant_system.trade.live_trading import LiveTradingEngine, LIVE_TRADING_CONFIG
from quant_system.config.settings import BACKTEST_CONFIG

def load_config(config_path: str = None):
    """加载配置文件"""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    else:
        print(f"配置文件 {config_path} 不存在，使用默认配置")
        return None

def run_backtest(symbols: List[str], start_date: str, end_date: str, initial_capital: float):
    """
    运行回测
    """
    print("开始回测...")
    
    # 初始化组件
    data_handler = DataHandler()
    backtest_engine = BacktestEngine(initial_capital=initial_capital)
    
    # 获取数据
    print("正在获取市场数据...")
    market_data = data_handler.get_market_data(symbols, start_date, end_date)
    
    # 计算技术指标
    print("正在计算技术指标...")
    for symbol in symbols:
        if symbol in market_data and not market_data[symbol].empty:
            market_data[symbol] = data_handler.calculate_technical_indicators(market_data[symbol])
    
    # 运行回测
    print("正在运行回测...")
    result = backtest_engine.run_backtest(symbols, market_data, start_date, end_date)
    
    # 输出结果
    backtest_engine.print_backtest_report(result)
    backtest_engine.plot_equity_curve()
    
    return result


def run_simulation(symbols: List[str], start_date: str, end_date: str, initial_capital: float):
    """
    运行模拟交易
    """
    print("开始模拟交易...")
    
    # 初始化组件
    data_handler = DataHandler()
    simulation_engine = SimulationEngine(initial_capital=initial_capital)
    
    # 运行模拟
    simulation_engine.run_simulation(symbols, data_handler, start_date, end_date)
    
    return simulation_engine


def run_live_trading(symbols: List[str]):
    """
    运行实盘交易
    """
    if not LIVE_TRADING_CONFIG['enable_real_trading']:
        print("实盘交易未启用！请在配置中设置 enable_real_trading=True")
        print("出于安全考虑，实盘交易默认是关闭的")
        return
    
    print("开始实盘交易...")
    print("警告：您正在运行实盘交易，这将使用真实资金进行交易！")
    confirm = input("请输入 'YES' 确认继续: ")
    if confirm != 'YES':
        print("已取消实盘交易")
        return
    
    # 初始化组件
    data_handler = DataHandler()
    live_trading_engine = LiveTradingEngine()
    
    # 运行实盘交易
    try:
        live_trading_engine.run_live_trading(symbols, data_handler)
    except Exception as e:
        print(f"实盘交易出现错误: {e}")
    
    return live_trading_engine


def main():
    # 尝试加载配置文件
    config = load_config()
    
    if config:
        # 从配置文件读取参数
        mode = config.get('mode', 'backtest')
        symbols = config.get('symbols', [])
        
        # 如果symbols为空，则获取所有沪深主板非ST股票
        if not symbols:
            print("正在获取所有沪深主板非ST股票...")
            data_handler = DataHandler()
            all_stocks = data_handler.get_stock_list()
            symbols = all_stocks['ts_code'].tolist()
            print(f"获取到 {len(symbols)} 只股票")
        
        if mode == 'backtest':
            backtest_config = config.get('backtest', {})
            start_date = backtest_config.get('start_date', '2024-01-01')
            end_date = backtest_config.get('end_date', '2024-11-24')
            capital = backtest_config.get('initial_capital', 100000)
            
            run_backtest(symbols, start_date, end_date, capital)
        elif mode == 'simulate':
            simulate_config = config.get('simulate', {})
            start_date = simulate_config.get('start_date', '2024-01-01')
            end_date = simulate_config.get('end_date', '2024-11-24')
            capital = simulate_config.get('initial_capital', 100000)
            
            run_simulation(symbols, start_date, end_date, capital)
        elif mode == 'live':
            live_config = config.get('live', {})
            capital = live_config.get('initial_capital', 100000)
            
            run_live_trading(symbols)
    else:
        # 使用命令行参数
        parser = argparse.ArgumentParser(description='A股低频量化交易系统')
        parser.add_argument('mode', choices=['backtest', 'simulate', 'live'], 
                           help='运行模式: backtest(回测), simulate(模拟), live(实盘)')
        parser.add_argument('--symbols', nargs='+', default=['000001.SZ', '600000.SH'], 
                           help='股票代码列表，默认为平安银行和浦发银行')
        parser.add_argument('--start_date', type=str, default=BACKTEST_CONFIG['start_date'],
                           help='开始日期，格式: YYYY-MM-DD')
        parser.add_argument('--end_date', type=str, default=BACKTEST_CONFIG['end_date'],
                           help='结束日期，格式: YYYY-MM-DD')
        parser.add_argument('--capital', type=float, default=BACKTEST_CONFIG['initial_capital'],
                           help='初始资金')
        
        args = parser.parse_args()
        
        if args.mode == 'backtest':
            run_backtest(args.symbols, args.start_date, args.end_date, args.capital)
        elif args.mode == 'simulate':
            run_simulation(args.symbols, args.start_date, args.end_date, args.capital)
        elif args.mode == 'live':
            run_live_trading(args.symbols)


if __name__ == "__main__":
    # 如果直接运行此脚本且没有命令行参数，则运行示例
    import sys
    if len(sys.argv) == 1:
        print("A股低频量化交易系统")
        print("="*50)
        print("运行示例:")
        print("1. 回测模式: python main.py backtest --symbols 000001.SZ 600000.SH --start_date 2023-01-01 --end_date 2023-12-31")
        print("2. 模拟模式: python main.py simulate --symbols 000001.SZ 600000.SH --start_date 2023-01-01 --end_date 2023-12-31")
        print("3. 实盘模式: python main.py live --symbols 000001.SZ 600000.SH")
        print()
        print("系统特性:")
        print("- 基于利弗莫尔交易理念")
        print("- 支持沪深主板股票")
        print("- 包含回测、模拟、实盘三种模式")
        print("- 集成风险控制机制")
        print()
        
        # 从配置文件运行
        print("从配置文件运行...")
        try:
            main()
        except Exception as e:
            print(f"运行出现错误: {e}")
            print("请确保已安装所需依赖包: pip install akshare tushare pandas numpy matplotlib")
    else:
        main()