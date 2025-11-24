"""
利弗莫尔交易策略实现
基于杰西·利弗莫尔的交易理念
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TradeSignal:
    """交易信号数据类"""
    date: str
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    price: float
    volume: int
    reason: str
    confidence: float  # 置信度 0-1


class LivermoreStrategy:
    """
    利弗莫尔交易策略
    核心理念：
    1. 顺势而为 - 识别并跟随市场趋势
    2. 关键点位突破 - 在重要价位突破时入场
    3. 量价配合 - 成交量确认价格变动
    4. 市场情绪 - 判断市场整体氛围
    5. 风险控制 - 严格的资金管理
    """
    
    def __init__(self, params: Dict = None):
        """
        初始化策略
        :param params: 策略参数
        """
        self.params = params or {
            'trend_confirmation_period': 20,
            'breakout_threshold': 0.02,
            'market_timing_threshold': 0.015,
            'volume_confirmation': True,
            'pivot_point_period': 50,
            'market_mood_sensitivity': 0.8
        }
    
    def detect_trend(self, df: pd.DataFrame) -> pd.Series:
        """
        检测市场趋势
        :param df: 包含价格数据的DataFrame
        :return: 趋势方向序列 (1: 上升, -1: 下降, 0: 震荡)
        """
        # 使用移动平均线判断趋势
        ma_fast = df['ma_10']
        ma_slow = df['ma_20']
        
        # 趋势方向
        trend = pd.Series(0, index=df.index)
        trend[(ma_fast > ma_slow) & (ma_fast > ma_fast.shift(1))] = 1  # 上升趋势
        trend[(ma_fast < ma_slow) & (ma_fast < ma_fast.shift(1))] = -1  # 下降趋势
        
        # 趋势强度
        trend_strength = df['trend_strength']
        strong_trend = abs(trend_strength) > 0.05  # 趋势强度阈值
        
        return trend * strong_trend.astype(int)
    
    def identify_pivot_points(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        识别枢轴点（支撑位和阻力位）
        :param df: 包含价格数据的DataFrame
        :return: 支撑位和阻力位序列
        """
        period = self.params['pivot_point_period']
        
        # 使用滚动窗口找局部最高最低点
        pivot_highs = df['high'].rolling(window=period, center=True).max()
        pivot_lows = df['low'].rolling(window=period, center=True).min()
        
        # 只保留真正的局部极值点
        high_mask = (df['high'] == pivot_highs)
        low_mask = (df['low'] == pivot_lows)
        
        pivot_highs = pivot_highs.where(high_mask)
        pivot_lows = pivot_lows.where(low_mask)
        
        return pivot_lows, pivot_highs
    
    def detect_breakout(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        检测价格突破信号
        :param df: 包含价格和指标的DataFrame
        :return: 突破信号DataFrame
        """
        signals = pd.DataFrame(index=df.index)
        
        # 使用数据处理模块计算的支撑位和阻力位
        support = df['support']
        resistance = df['resistance']
        
        # 突破检测
        price = df['close']
        
        # 向上突破阻力位
        breakout_up = (price > resistance.shift(1)) & (price > price.shift(1))
        # 向下突破支撑位
        breakout_down = (price < support.shift(1)) & (price < price.shift(1))
        
        # 成交量确认
        volume_confirmation = df['volume_ratio'] > 1.2 if self.params['volume_confirmation'] else True
        
        signals['breakout_up'] = breakout_up & volume_confirmation
        signals['breakout_down'] = breakout_down & volume_confirmation
        
        return signals
    
    def assess_market_mood(self, df: pd.DataFrame) -> pd.Series:
        """
        评估市场情绪
        :param df: 包含市场数据的DataFrame
        :return: 市场情绪指标
        """
        # 计算市场整体情绪指标
        # 1. 价格变化率
        pct_change = df['pct_change']
        
        # 2. 成交量变化
        volume_change = df['volume'].pct_change()
        
        # 3. 波动率水平
        volatility = df['volatility_20']
        
        # 综合情绪指标
        mood = pd.Series(0.5, index=df.index)  # 默认中性
        
        # 基于价格变化调整情绪
        mood += pct_change * 0.3
        # 基于成交量调整情绪
        mood += volume_change * 0.2
        # 基于波动率调整（高波动可能表示不确定性）
        mood -= volatility * 0.1
        
        # 限制范围在0-1之间
        mood = mood.clip(0, 1)
        
        return mood
    
    def generate_signals(self, df: pd.DataFrame, symbol: str) -> List[TradeSignal]:
        """
        生成交易信号
        :param df: 包含完整指标的DataFrame
        :param symbol: 股票代码
        :return: 交易信号列表
        """
        signals = []
        
        # 检测趋势
        trend = self.detect_trend(df)
        
        # 检测突破
        breakout_signals = self.detect_breakout(df)
        
        # 评估市场情绪
        market_mood = self.assess_market_mood(df)
        
        for i in range(1, len(df)):  # 从第二个数据点开始
            current_date = df.iloc[i]['date'].strftime('%Y-%m-%d')
            current_price = df.iloc[i]['close']
            
            # 买入信号条件
            buy_signal = (
                trend.iloc[i] == 1 and  # 上升趋势
                breakout_signals['breakout_up'].iloc[i] and  # 向上突破
                market_mood.iloc[i] > self.params['market_mood_sensitivity']  # 市场情绪积极
            )
            
            # 卖出信号条件
            sell_signal = (
                trend.iloc[i] == -1 and  # 下降趋势
                breakout_signals['breakout_down'].iloc[i] and  # 向下突破
                market_mood.iloc[i] < (1 - self.params['market_mood_sensitivity'])  # 市场情绪消极
            )
            
            if buy_signal:
                signal = TradeSignal(
                    date=current_date,
                    symbol=symbol,
                    action='BUY',
                    price=current_price,
                    volume=1000,  # 默认买入1000股
                    reason='Trend up + Breakout up + Positive mood',
                    confidence=min(1.0, trend.iloc[i] * market_mood.iloc[i])
                )
                signals.append(signal)
                
            elif sell_signal:
                signal = TradeSignal(
                    date=current_date,
                    symbol=symbol,
                    action='SELL',
                    price=current_price,
                    volume=1000,  # 默认卖出1000股
                    reason='Trend down + Breakout down + Negative mood',
                    confidence=min(1.0, abs(trend.iloc[i]) * (1 - market_mood.iloc[i]))
                )
                signals.append(signal)
        
        return signals
    
    def calculate_position_size(self, price: float, account_balance: float, risk_per_trade: float = 0.02) -> int:
        """
        计算仓位大小（基于风险控制）
        :param price: 当前价格
        :param account_balance: 账户余额
        :param risk_per_trade: 单次交易风险比例
        :return: 建议交易股数
        """
        # 基于账户资金和风险控制计算仓位
        risk_amount = account_balance * risk_per_trade
        position_size = int(risk_amount / price)
        
        # 确保是100的倍数（A股交易单位）
        position_size = (position_size // 100) * 100
        
        return max(position_size, 100)  # 最少100股


class MarketTiming:
    """
    市场时机选择模块
    基于利弗莫尔的理念选择最佳入场和出场时机
    """
    
    def __init__(self, params: Dict = None):
        self.params = params or {
            'timing_threshold': 0.015,
            'confirmation_bars': 3
        }
    
    def is_good_entry_timing(self, df: pd.DataFrame, idx: int) -> bool:
        """
        判断是否为好的入场时机
        """
        if idx < self.params['confirmation_bars']:
            return False
            
        # 检查最近几根K线的走势
        recent_data = df.iloc[idx-self.params['confirmation_bars']:idx+1]
        
        # 检查是否有持续的上涨趋势
        price_increasing = all(
            recent_data.iloc[i]['close'] > recent_data.iloc[i-1]['close'] 
            for i in range(1, len(recent_data))
        ) if len(recent_data) > 1 else False
        
        # 检查成交量是否配合上涨
        volume_increasing = True
        if len(recent_data) > 1:
            avg_vol_recent = recent_data['volume'].iloc[-3:].mean()
            avg_vol_prev = recent_data['volume'].iloc[:-3].mean() if len(recent_data) > 3 else avg_vol_recent
            volume_increasing = avg_vol_recent > avg_vol_prev
        
        return price_increasing and volume_increasing
    
    def is_good_exit_timing(self, df: pd.DataFrame, idx: int) -> bool:
        """
        判断是否为好的出场时机
        """
        if idx < self.params['confirmation_bars']:
            return False
            
        # 检查最近几根K线的走势
        recent_data = df.iloc[idx-self.params['confirmation_bars']:idx+1]
        
        # 检查是否有持续的下跌趋势
        price_decreasing = all(
            recent_data.iloc[i]['close'] < recent_data.iloc[i-1]['close'] 
            for i in range(1, len(recent_data))
        ) if len(recent_data) > 1 else False
        
        return price_decreasing