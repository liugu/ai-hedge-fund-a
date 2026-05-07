# AI 对冲基金

这是一个基于AI的对冲基金概念验证项目。项目目标是探索使用AI进行交易决策。**本项目仅供教育目的，不适用于实际交易或投资。**

本系统采用多个智能代理协同工作：

1. **阿斯沃斯·达莫达兰代理** - 估值大师，专注于故事、数字和严谨的估值
2. **本杰明·格雷厄姆代理** - 价值投资鼻祖，只买入具有安全边际的隐藏宝石
3. **比尔·阿克曼代理** - 激进投资者，大胆建仓并推动变革
4. **凯瑟琳·伍德代理** - 成长投资女王，相信创新和颠覆的力量
5. **查理·芒格代理** - 沃伦·巴菲特的搭档，只以合理价格买入优秀企业
6. **迈克尔·布瑞代理** - 《大空头》逆向投资者，寻找深度价值
7. **莫尼什·帕布莱代理** - Dhandho投资者，寻找低风险的翻倍机会
8. **纳西姆·塔勒布代理** - 黑天鹅风险分析师，专注于尾部风险、反脆弱和非对称收益
9. **彼得·林奇代理** - 实战投资者，在日常生活中寻找"十倍股"
10. **菲利普·费舍代理** - 严谨的成长投资者，使用深度"闲聊"调研
11. **拉凯什·詹朱恩瓦拉代理** - 印度大牛
12. **斯坦利·德鲁肯米勒代理** - 宏观传奇，寻找具有成长潜力的非对称机会
13. **沃伦·巴菲特代理** - 奥马哈先知，以合理价格寻找优秀公司
14. **估值代理** - 计算股票内在价值并生成交易信号
15. **情绪代理** - 分析市场情绪并生成交易信号
16. **基本面代理** - 分析基本面数据并生成交易信号
17. **技术面代理** - 分析技术指标并生成交易信号
18. **风险管理代理** - 计算风险指标并设定仓位限制
19. **组合管理代理** - 做出最终交易决策并生成订单

<img width="1042" alt="系统截图" src="https://github.com/user-attachments/assets/cbae3dcf-b571-490d-b0ad-3f0f035ac0d4" />

注意：本系统不会实际执行任何交易。

[![Twitter关注](https://img.shields.io/twitter/follow/virattt?style=social)](https://twitter.com/virattt)

## 免责声明

本项目**仅供教育和研究目的**。

- 不适用于实际交易或投资
- 不提供投资建议或保证
- 创作者不对财务损失承担责任
- 投资决策请咨询财务顾问
- 过往业绩不代表未来表现

使用本软件即表示您同意仅将其用于学习目的。

## 目录
- [安装指南](#安装指南)
- [运行方式](#运行方式)
  - [⌨️ 命令行界面](#️-命令行界面)
  - [🖥️ Web应用程序](#️-web应用程序)
- [如何贡献](#如何贡献)
- [功能请求](#功能请求)
- [许可证](#许可证)

## 安装指南

在运行AI对冲基金之前，您需要安装并设置API密钥。这些步骤适用于全栈Web应用程序和命令行界面。

### 1. 克隆仓库

```bash
git clone https://github.com/virattt/ai-hedge-fund.git
cd ai-hedge-fund
```

### 2. 设置API密钥

创建`.env`文件存放您的API密钥：
```bash
# 在根目录创建.env文件
cp .env.example .env
```

打开并编辑`.env`文件添加您的API密钥：
```bash
# 用于运行OpenAI托管的LLM（gpt-4o、gpt-4o-mini等）
OPENAI_API_KEY=your-openai-api-key

# 用于获取财务数据驱动对冲基金
FINANCIAL_DATASETS_API_KEY=your-financial-datasets-api-key
```

**重要**：您必须至少设置一个LLM API密钥（如`OPENAI_API_KEY`、`GROQ_API_KEY`、`ANTHROPIC_API_KEY`或`DEEPSEEK_API_KEY`）才能使对冲基金正常工作。

## 运行方式

### ⌨️ 命令行界面

您可以通过终端直接运行AI对冲基金。这种方式提供更精细的控制，适合自动化、脚本编写和集成目的。

<img width="992" alt="命令行截图" src="https://github.com/user-attachments/assets/e8ca04bf-9989-4a7d-a8b4-34e04666663b" />

#### 快速开始

1. 安装Poetry（如尚未安装）：
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. 安装依赖：
```bash
poetry install
```

#### 运行AI对冲基金
```bash
poetry run python src/main.py --ticker AAPL,MSFT,NVDA
```

您也可以使用`--ollama`标志在本地LLM上运行AI对冲基金。

```bash
poetry run python src/main.py --ticker AAPL,MSFT,NVDA --ollama
```

您可以可选地指定开始和结束日期，在特定时间段内做出决策。

```bash
poetry run python src/main.py --ticker AAPL,MSFT,NVDA --start-date 2024-01-01 --end-date 2024-03-01
```

#### 运行回测器
```bash
poetry run python src/backtester.py --ticker AAPL,MSFT,NVDA
```

**示例输出：**
<img width="941" alt="回测截图" src="https://github.com/user-attachments/assets/00e794ea-8628-44e6-9a84-8f8a31ad3b47" />

注意：`--ollama`、`--start-date`和`--end-date`标志同样适用于回测器！

### 🖥️ Web应用程序

运行AI对冲基金的新方式是通过我们的Web应用程序，它提供友好的用户界面。推荐给偏好可视化界面的用户。

详细的Web应用程序安装和运行说明请参见[此处](https://github.com/virattt/ai-hedge-fund/tree/main/app)。

<img width="1721" alt="Web应用截图" src="https://github.com/user-attachments/assets/b95ab696-c9f4-416c-9ad1-51feb1f5374b" />

## 如何贡献

1. Fork本仓库
2. 创建功能分支
3. 提交您的更改
4. 推送到分支
5. 创建Pull Request

**重要**：请保持您的Pull Request小而专注，这将使审查和合并更容易。

## 功能请求

如果您有功能请求，请提交一个[issue](https://github.com/virattt/ai-hedge-fund/issues)，并确保标记为`enhancement`。

## 许可证

本项目采用MIT许可证 - 详情请参见LICENSE文件。
