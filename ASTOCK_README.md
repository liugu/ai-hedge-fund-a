# A股智能分析系统

基于AI的A股市场分析系统，整合多种数据源和分析方法，提供全面的股票分析能力。

## 功能特性

### 数据源支持
- **AKShare**: 免费开源A股数据源
- **Tushare Pro**: 专业金融数据（需API密钥）
- **腾讯财经**: 实时行情数据
- **东方财富**: K线、资金流向、板块数据
- **港股通**: 港股通资金流向、AH溢价

### 分析模块
- **技术分析**: MACD、KDJ、RSI、BOLL、MA等指标
- **资金流向**: 主力资金、散户资金、北向资金分析
- **板块轮动**: 板块热度、资金流向、轮动信号
- **综合评分**: 多因子综合评分系统

### 分析师代理
- A股技术分析师
- A股资金流向分析师
- 北向资金分析师
- 以及19+其他分析师代理

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基础使用

```python
# 运行综合分析
python comprehensive_analyze.py

# 运行批量分析
python analyze_a_stock_enhanced.py

# 使用腾讯API分析
python analyze_with_tencent.py
```

### API服务

```bash
# 启动API服务
python -m src.api.a_stock_api_routes
```

API端点:
- `GET /api/v1/quote/<ticker>` - 获取实时行情
- `POST /api/v1/quotes` - 批量获取行情
- `GET /api/v1/kline/<ticker>` - 获取K线数据
- `GET /api/v1/fundflow/<ticker>` - 获取资金流向
- `GET /api/v1/technical/<ticker>` - 获取技术指标
- `GET /api/v1/northbound` - 获取北向资金
- `GET /api/v1/sectors` - 获取板块数据
- `GET /api/v1/analyze/<ticker>` - 综合分析

## 项目结构

```
ai-hedge-fund-a/
├── src/
│   ├── agents/           # 分析师代理
│   │   ├── a_stock_technical.py
│   │   ├── a_stock_fund_flow.py
│   │   └── northbound_flow.py
│   ├── tools/            # 数据工具
│   │   └── a_stock_api.py
│   ├── utils/            # 工具模块
│   │   ├── tencent_api.py
│   │   ├── eastmoney_api.py
│   │   ├── technical_indicators.py
│   │   ├── sector_rotation.py
│   │   ├── cache_enhanced.py
│   │   ├── backtest_a_stock.py
│   │   ├── scheduler.py
│   │   ├── config.py
│   │   └── visualization.py
│   └── api/              # API接口
│       └── a_stock_api_routes.py
├── comprehensive_analyze.py    # 综合分析脚本
├── analyze_a_stock_enhanced.py # 增强分析脚本
└── analyze_with_tencent.py     # 腾讯API分析
```

## 配置说明

环境变量配置:

```bash
# 数据源
A_STOCK_DATA_SOURCE=akshare
TUSHARE_API_KEY=your_api_key

# 缓存
CACHE_ENABLED=true
CACHE_TTL=3600
REDIS_ENABLED=false
REDIS_HOST=localhost
REDIS_PORT=6379

# API
API_HOST=0.0.0.0
API_PORT=5001

# 调度器
SCHEDULER_ENABLED=false
```

## 分析示例

```python
from src.tools.a_stock_api import AStockAPI
from src.utils.technical_indicators import analyze_technical

# 获取股票数据
api = AStockAPI()
prices = api.get_prices("600519", "2024-01-01", "2024-12-31")

# 技术分析
closes = [p.close for p in prices]
indicators = analyze_technical(closes)

print(f"趋势: {indicators.trend}")
print(f"强度: {indicators.signal_strength}%")
print(f"MACD: {indicators.macd}")
```

## 免责声明

本系统仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。

## 许可证

MIT License
