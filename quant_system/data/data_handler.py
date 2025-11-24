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
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib


class DataHandler:
    """
    A股数据处理类
    """
    def __init__(self, token: str = None, cache_dir: str = 'cache'):
        """
        初始化数据处理器
        :param token: 保留接口，当前使用baostock
        :param cache_dir: 缓存目录
        """
        # 登录baostock
        bs.login()
        self.db_path = 'trading_data.db'
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # 添加请求频率限制
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 最小请求间隔0.5秒
        
        # 添加缓存字典
        self.data_cache = {}
        
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

    def _enforce_rate_limit(self):
        """
        强制执行请求频率限制
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    def _get_cache_key(self, symbol: str, start_date: str, end_date: str) -> str:
        """
        生成缓存键
        """
        cache_key = f"{symbol}_{start_date}_{end_date}"
        return hashlib.md5(cache_key.encode()).hexdigest()

    def _load_from_cache(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        从缓存加载数据
        """
        cache_key = self._get_cache_key(symbol, start_date, end_date)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        # 首先检查内存缓存
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        # 然后检查文件缓存
        if os.path.exists(cache_file):
            try:
                df = pd.read_pickle(cache_file)
                # 将数据存入内存缓存
                self.data_cache[cache_key] = df
                return df
            except Exception as e:
                print(f"从缓存加载数据失败: {e}")
                return None
        return None

    def _save_to_cache(self, symbol: str, start_date: str, end_date: str, df: pd.DataFrame):
        """
        保存数据到缓存
        """
        cache_key = self._get_cache_key(symbol, start_date, end_date)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        # 保存到内存缓存
        self.data_cache[cache_key] = df
        
        # 保存到文件缓存
        try:
            df.to_pickle(cache_file)
        except Exception as e:
            print(f"保存缓存失败: {e}")

    def get_daily_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取单只股票的日线数据
        :param symbol: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 包含OHLCV数据的DataFrame
        """
        # 将非交易日调整为最近的交易日
        adjusted_start_date = self.get_previous_trading_date(start_date)
        adjusted_end_date = self.get_previous_trading_date(end_date)
        
        # 首先尝试从缓存加载
        cached_data = self._load_from_cache(symbol, adjusted_start_date, adjusted_end_date)
        if cached_data is not None:
            print(f"从缓存加载 {symbol} 数据")
            return cached_data.copy()
        
        # 执行请求频率限制
        self._enforce_rate_limit()
        
        # 使用baostock获取数据
        try:
            rs = bs.query_history_k_data_plus(symbol, 
                                              "date,open,high,low,close,volume",
                                              start_date=adjusted_start_date, 
                                              end_date=adjusted_end_date, 
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
            
            # 保存到缓存
            self._save_to_cache(symbol, adjusted_start_date, adjusted_end_date, df)
            
            return df
        except Exception as e:
            print(f"获取 {symbol} 数据失败: {e}")
            return pd.DataFrame()

    def get_market_data(self, symbols: List[str], start_date: str, end_date: str, max_workers: int = 5) -> Dict[str, pd.DataFrame]:
        """
        获取多只股票的市场数据（并行处理）
        :param symbols: 股票代码列表
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param max_workers: 最大并行线程数
        :return: 股票数据字典
        """
        market_data = {}
        
        # 使用ThreadPoolExecutor进行并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_symbol = {
                executor.submit(self.get_daily_data, symbol, start_date, end_date): symbol 
                for symbol in symbols
            }
            
            # 收集结果
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    data = future.result()
                    if not data.empty:
                        market_data[symbol] = data
                        print(f"成功获取 {symbol} 数据，共 {len(data)} 条记录")
                    else:
                        print(f"获取 {symbol} 数据为空")
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

    def get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        使用baostock获取交易日历
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 交易日期列表
        """
        # 使用股票数据来判断交易日（使用上证指数作为参考）
        rs = bs.query_history_k_data_plus("sh.000001", 
                                          "date",
                                          start_date=start_date, 
                                          end_date=end_date, 
                                          frequency="d", 
                                          adjustflag="3")
        
        trading_dates = []
        while (rs.error_code == '0') & rs.next():
            date = rs.get_row_data()[0]
            trading_dates.append(date)
        
        return trading_dates

    def get_previous_trading_date(self, date_str: str) -> str:
        """
        获取指定日期之前的最近一个交易日
        :param date_str: 输入日期字符串 (YYYY-MM-DD)
        :return: 最近的交易日日期字符串
        """
        # 解析输入日期
        input_date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # 获取一个较长时间范围的交易日历
        start_date = (input_date - timedelta(days=365)).strftime('%Y-%m-%d')
        end_date = input_date.strftime('%Y-%m-%d')
        
        trading_dates = self.get_trading_dates(start_date, end_date)
        
        # 将交易日期转换为datetime对象并排序
        trading_datetime_list = [datetime.strptime(d, '%Y-%m-%d') for d in trading_dates]
        trading_datetime_list.sort(reverse=True)  # 降序排列
        
        # 找到小于等于输入日期的最近交易日
        for trade_date in trading_datetime_list:
            if trade_date <= input_date:
                return trade_date.strftime('%Y-%m-%d')
        
        # 如果没找到，返回输入日期（理论上不应该发生）
        return date_str

    def __del__(self):
        """
        析构函数，登出baostock并清理资源
        """
        try:
            bs.logout()
        except:
            pass
        # 清理内存缓存
        self.data_cache.clear()