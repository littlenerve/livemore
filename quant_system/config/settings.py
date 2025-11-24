"""
系统配置文件
"""
import os

# 数据库配置
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///trading.db')

# 交易配置
INITIAL_CAPITAL = 100000  # 初始资金
COMMISSION_RATE = 0.0003  # 佣金费率
TAX_RATE = 0.001          # 印花税率（仅卖出）
MIN_COMMISSION = 5        # 最低佣金

# A股交易时间
TRADING_HOURS = {
    'morning': ('09:30', '11:30'),
    'afternoon': ('13:00', '15:00')
}

# 利弗莫尔策略参数
LIVERMORE_PARAMS = {
    'trend_confirmation_period': 20,      # 趋势确认周期
    'breakout_threshold': 0.02,           # 突破阈值(2%)
    'market_timing_threshold': 0.015,     # 市场时机阈值(1.5%)
    'volume_confirmation': True,          # 是否需要成交量确认
    'pivot_point_period': 50,             # 枢轴点计算周期
    'market_mood_sensitivity': 0.8        # 市场情绪敏感度
}

# 回测配置
BACKTEST_CONFIG = {
    'start_date': '2024-01-01',
    'end_date': '2024-11-24',
    'initial_capital': INITIAL_CAPITAL,
    'commission_rate': COMMISSION_RATE,
    'slippage': 0.001  # 滑点
}

# 模拟交易配置
SIMULATION_CONFIG = {
    'initial_capital': INITIAL_CAPITAL,
    'delay': 1,  # 模拟延迟（秒）
    'use_real_time_data': True
}

# 实盘交易配置
LIVE_TRADING_CONFIG = {
    'enable_real_trading': False,  # 默认关闭实盘交易
    'max_position_size': 0.2,      # 单股最大仓位比例
    'stop_loss_threshold': -0.08,  # 止损阈值(-8%)
    'take_profit_threshold': 0.20, # 止盈阈值(20%)
    'initial_capital': INITIAL_CAPITAL  # 初始资金
}