"""
数据处理模块
处理A股股票数据的获取、清洗和存储
"""
import pandas as pd
import numpy as np
import baostock as bs
from datetime import datetime, timedelta
import sqlite3
import os
from typing import List, Dict, Optional


class DataHandler:
    """
    A股数据处理类
    """
    def __init__(self, token: str = None):
        """
        初始化数据处理器
        :param token: 保留接口，当前使用baostock
        """
        # 登录baostock
        bs.login()
        self.db_path = 'trading_data.db'
        
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股股票列表（沪深主板）
        """
        # 使用baostock获取股票信息
        rs = bs.query_stock_basic()
        stock_list = []
        while (rs.error_code == '0') & rs.next():
            stock_list.append(rs.get_row_data())
        
        result = pd.DataFrame(stock_list, columns=rs.fields)
        
        # 过滤沪深主板（排除科创板和创业板）
        result = result[
            (result['code'].str.endswith('.SH')) | 
            (result['code'].str.endswith('.SZ')) &
            (~result['code'].str.startswith('688')) &  # 排除科创板
            (~result['code'].str.startswith('300'))    # 排除创业板
        ]
        
        # 过滤ST股票
        result = result[~result['code_name'].str.contains('ST')]
        
        # 重命名列以匹配系统需求
        result = result.rename(columns={
            'code': 'ts_code',
            'code_name': 'name'
        })
        result['symbol'] = result['ts_code']
        
        return result

    def get_daily_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取单只股票的日线数据
        :param symbol: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 包含OHLCV数据的DataFrame
        """
        # 使用baostock获取数据
        rs = bs.query_history_k_data_plus(symbol, 
                                          "date,open,high,low,close,volume",
                                          start_date=start_date, 
                                          end_date=end_date, 
                                          frequency="d", 
                                          adjustflag="3")
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        
        if df.empty:
            return df
        
        # 数据类型转换
        df['date'] = pd.to_datetime(df['date'])
        df['open'] = pd.to_numeric(df['open'], errors='coerce')
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        
        # 删除包含NaN的行
        df = df.dropna()
        
        # 按日期排序
        df = df.sort_values('date').reset_index(drop=True)
        
        return df

    def get_market_data(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        获取多只股票的市场数据
        :param symbols: 股票代码列表
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 股票数据字典
        """
        market_data = {}
        for symbol in symbols:
            try:
                data = self.get_daily_data(symbol, start_date, end_date)
                if not data.empty:
                    market_data[symbol] = data
            except Exception as e:
                print(f"获取 {symbol} 数据失败: {e}")
        
        return market_data

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标（基于利弗莫尔理念）
        """
        # 确保数据按日期排序
        df = df.sort_values('date').reset_index(drop=True)
        
        # 移动平均线
        df['ma_5'] = df['close'].rolling(window=5).mean()
        df['ma_10'] = df['close'].rolling(window=10).mean()
        df['ma_20'] = df['close'].rolling(window=20).mean()
        df['ma_50'] = df['close'].rolling(window=50).mean()
        df['ma_200'] = df['close'].rolling(window=200).mean()
        
        # 价格变化率
        df['pct_change'] = df['close'].pct_change()
        
        # 成交量移动平均
        df['volume_ma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma_20']
        
        # 波动率
        df['volatility_20'] = df['pct_change'].rolling(window=20).std()
        
        # 最高价和最低价的移动平均
        df['high_ma_20'] = df['high'].rolling(window=20).max()
        df['low_ma_20'] = df['low'].rolling(window=20).min()
        
        # 利弗莫尔的关键点位
        # 枢轴点（pivot point）
        df['pivot_high'] = df['high'].rolling(window=50, center=True).max().shift(25)
        df['pivot_low'] = df['low'].rolling(window=50, center=True).min().shift(25)
        
        # 价格相对于枢轴点的位置
        df['price_above_pivot'] = df['close'] > df['pivot_high']
        df['price_below_pivot'] = df['close'] < df['pivot_low']
        
        # 趋势强度
        df['trend_strength'] = (df['close'] - df['ma_20']) / df['ma_20']
        
        # 支撑位和阻力位
        df['support'] = df['low'].rolling(window=20).min()
        df['resistance'] = df['high'].rolling(window=20).max()
        
        # 价格突破上下轨
        df['breakout_up'] = df['close'] > df['resistance'].shift(1)
        df['breakout_down'] = df['close'] < df['support'].shift(1)
        
        # 价格与成交量的配合
        df['price_volume_swing'] = (df['pct_change'] * df['volume_ratio'] > 1.5)
        
        return df

    def save_to_db(self, data: pd.DataFrame, table_name: str):
        """
        保存数据到数据库
        """
        conn = sqlite3.connect(self.db_path)
        data.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()

    def load_from_db(self, table_name: str) -> pd.DataFrame:
        """
        从数据库加载数据
        """
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        df['date'] = pd.to_datetime(df['date'])
        return df

    def __del__(self):
        """
        析构函数，登出baostock
        """
        try:
            bs.logout()
        except:
            pass