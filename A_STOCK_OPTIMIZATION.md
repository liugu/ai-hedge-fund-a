# A股优化说明

本文档说明AI对冲基金项目针对A股市场的优化调整。

## 已完成的优化

### 1. 文档和注释中文化

所有主要文档和代码注释已翻译为中文：

- `README.md` - 项目主文档
- `app/README.md` - Web应用文档
- `v2/README.md` - V2量化框架文档
- `src/utils/analysts.py` - 分析师配置
- `src/utils/display.py` - 输出显示
- `src/cli/input.py` - 命令行输入
- `src/data/models.py` - 数据模型
- `src/tools/api.py` - API接口
- `src/main.py` - 主程序
- `src/backtester.py` - 回测器
- `src/agents/*.py` - 各代理文件

### 2. A股数据源适配

新增文件：`src/tools/a_stock_api.py`

支持多种A股数据源：

| 数据源 | 说明 | API密钥 |
|--------|------|---------|
| AKShare | 免费开源 | 无需 |
| Tushare Pro | 专业数据 | 需要 |
| 东方财富 | 免费开源 | 可选 |

使用方法：
```python
from src.tools.a_stock_api import AStockAPI

api = AStockAPI()  # 自动选择可用数据源

# 获取A股价格数据
prices = api.get_prices("600519", "2024-01-01", "2024-03-01")

# 获取财务指标
metrics = api.get_financial_metrics("600519", "2024-03-01")

# 获取公司信息
facts = api.get_company_facts("600519")
```

### 3. A股交易规则

新增文件：`src/tools/a_stock_rules.py`

包含A股特有的交易规则：

- **涨跌停限制**：普通股票10%，ST股票5%，创业板/科创板20%
- **T+1规则**：当天买入的股票不能当天卖出
- **交易时间**：上午9:30-11:30，下午13:00-15:00
- **最小交易单位**：100股（1手）
- **停牌检测**
- **ST股票处理**

使用方法：
```python
from src.tools.a_stock_rules import (
    calculate_price_limits,
    is_trading_time,
    can_sell_today,
    AStockTradingConstraints
)

# 计算涨跌停价格
upper, lower = calculate_price_limits("600519", 1800.0)
# 结果：(1980.0, 1620.0)

# 检查是否在交易时间
is_trading = is_trading_time()

# T+1检查
can_sell = can_sell_today(buy_date, sell_date)
```

### 4. 投资策略A股优化

新增文件：`src/config/a_stock_strategy.py`

针对A股市场特点对各投资大师策略进行调整：

| 策略 | 主要调整 |
|------|----------|
| 沃伦·巴菲特 | 增加分红权重，关注国企背景和政策支持 |
| 彼得·林奇 | 关注题材炒作和散户情绪 |
| 迈克尔·布瑞 | 关注ST股扭亏和重组机会 |
| 凯瑟琳·伍德 | 关注国家战略方向和科技自主可控 |
| 斯坦利·德鲁肯米勒 | 关注货币政策和经济周期 |
| 技术分析 | 增加涨跌停、资金流向、换手率分析 |
| 基本面分析 | 增加业绩预告和分红政策分析 |
| 情绪分析 | 增加社交媒体和论坛讨论分析 |

### 5. 环境变量配置

更新文件：`.env.example`

新增A股相关配置：
```bash
# A股数据源选择
A_STOCK_DATA_SOURCE=akshare

# A股交易时间配置
A_STOCK_TRADING_HOURS_START=09:30
A_STOCK_TRADING_HOURS_END=15:00

# A股涨跌停限制
A_STOCK_PRICE_LIMIT_PCT=10.0
A_STOCK_ST_PRICE_LIMIT_PCT=5.0
A_STOCK_GEM_PRICE_LIMIT_PCT=20.0
```

## A股市场特点

本项目针对以下A股市场特点进行了优化：

1. **涨跌停限制**：A股有涨跌停板制度，影响交易策略执行
2. **T+1交易**：当天买入的股票不能当天卖出
3. **散户占比高**：散户交易占比约70%，情绪影响大
4. **政策敏感性强**：政策对市场影响显著
5. **行业轮动明显**：板块轮动频繁
6. **题材炒作盛行**：概念股炒作现象普遍
7. **北向资金影响**：外资流入流出对市场影响大

## 使用A股功能

### 安装依赖

```bash
# 安装AKShare（免费A股数据源）
pip install akshare

# 或安装Tushare（专业数据源，需要API密钥）
pip install tushare
```

### 运行A股分析

```bash
# 分析A股股票（贵州茅台）
poetry run python src/main.py --ticker 600519

# 分析多只A股
poetry run python src/main.py --ticker 600519,000001,300750

# 运行回测
poetry run python src/backtester.py --ticker 600519
```

### 股票代码格式

支持多种格式：
- `600519` - 纯代码
- `600519.SH` - 带交易所后缀
- `sh600519` - 带交易所前缀

## 后续优化建议

1. **数据源增强**
   - 添加更多A股数据源（如Wind、同花顺）
   - 实现港股通数据接入
   - 添加期权数据

2. **策略优化**
   - 添加A股特有的量化因子
   - 实现板块轮动策略
   - 添加北向资金跟踪策略

3. **风险控制**
   - 实现涨跌停预警
   - 添加停牌检测
   - 实现ST股票风险控制

4. **性能优化**
   - 添加数据缓存
   - 优化回测速度
   - 支持并行处理

## 免责声明

本项目仅供教育和研究目的，不适用于实际交易或投资。使用本软件即表示您同意仅将其用于学习目的。
