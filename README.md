# A股低频量化交易系统

基于杰西·利弗莫尔交易理念的A股量化交易系统，支持回测、模拟和实盘交易。

## 系统特性

- **基于利弗莫尔理念**：顺势而为、关键点位突破、量价配合、市场情绪判断
- **多模式支持**：回测、模拟、实盘三种交易模式
- **沪深主板**：专门针对A股沪深主板股票
- **风险控制**：集成仓位管理、止损止盈机制
- **技术指标**：多种技术分析指标支持

## 系统架构

```
quant_system/
├── __init__.py
├── config/
│   └── settings.py          # 系统配置
├── data/
│   └── data_handler.py      # 数据处理模块
├── utils/
│   └── livermore_strategy.py # 利弗莫尔策略
├── backtest/
│   └── backtest_engine.py   # 回测引擎
├── simulate/
│   └── simulate_engine.py   # 模拟交易引擎
├── trade/
│   └── live_trading.py      # 实盘交易引擎
└── main.py                  # 主入口
```

## 安装依赖

```bash
pip install -r requirements.txt
```

或者单独安装：

```bash
pip install pandas numpy matplotlib seaborn akshare tushare requests
```

## 使用方法

### 1. 回测模式

```bash
python -m quant_system.main backtest --symbols 000001.SZ 600000.SH --start_date 2023-01-01 --end_date 2023-12-31 --capital 100000
```

### 2. 模拟交易

```bash
python -m quant_system.main simulate --symbols 000001.SZ 600000.SH --start_date 2023-01-01 --end_date 2023-12-31 --capital 100000
```

### 3. 实盘交易

> ⚠️ **警告**：实盘交易会使用真实资金，请谨慎操作！

```bash
python -m quant_system.main live --symbols 000001.SZ 600000.SH
```

> 注意：实盘交易默认是关闭的，需要在配置中启用。

## 利弗莫尔策略核心

### 1. 趋势跟随
- 使用移动平均线识别趋势方向
- 只在趋势明确时交易

### 2. 关键点位突破
- 识别支撑位和阻力位
- 在突破时入场

### 3. 量价配合
- 成交量确认价格变动
- 无量上涨或下跌不可靠

### 4. 市场情绪
- 综合市场情绪指标
- 避免在市场情绪过热或过冷时交易

### 5. 风险控制
- 严格的资金管理
- 止损止盈机制

## 配置说明

系统配置位于 `quant_system/config/settings.py`：

```python
# 初始资金
INITIAL_CAPITAL = 100000

# 交易费用
COMMISSION_RATE = 0.0003  # 佣金费率
TAX_RATE = 0.001          # 印花税率

# 利弗莫尔策略参数
LIVERMORE_PARAMS = {
    'trend_confirmation_period': 20,      # 趋势确认周期
    'breakout_threshold': 0.02,           # 突破阈值(2%)
    'market_timing_threshold': 0.015,     # 市场时机阈值(1.5%)
    'volume_confirmation': True,          # 是否需要成交量确认
    'pivot_point_period': 50,             # 枢轴点计算周期
    'market_mood_sensitivity': 0.8        # 市场情绪敏感度
}
```

## 数据源

系统使用以下数据源：
- `akshare`: 免费的A股数据源
- `tushare`: 需要注册获取token的专业数据源（可选）

## 风险提示

1. **投资有风险**：股票市场存在波动，可能导致本金损失
2. **策略不保证盈利**：过往业绩不代表未来表现
3. **实盘交易谨慎**：使用真实资金前请充分测试
4. **系统故障风险**：技术故障可能导致交易失败

## 开发计划

- [ ] 增加更多技术指标
- [ ] 优化回测引擎性能
- [ ] 集成更多券商API
- [ ] 增加机器学习策略
- [ ] 完善风险管理模块

## 贡献

欢迎提交Issue和Pull Request来改进系统。

## 许可证

本项目仅供学习和研究使用，不构成投资建议。