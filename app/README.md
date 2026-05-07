# Web应用程序

AI对冲基金应用是一个完整的系统，包含前端和后端组件，让您可以通过Web界面在自己的电脑上运行AI驱动的对冲基金交易系统。

<img width="1721" alt="Web应用截图" src="https://github.com/user-attachments/assets/b95ab696-c9f4-416c-9ad1-51feb1f5374b" />

## 概述

AI对冲基金包含：

- **后端**：FastAPI应用程序，提供REST API来运行对冲基金交易系统和回测器
- **前端**：React/Vite应用程序，提供友好的用户界面来可视化和管理对冲基金操作

## 目录

- [🚀 快速开始（非技术用户）](#-快速开始非技术用户)
  - [选项1：使用一键脚本（推荐）](#选项1使用一键脚本推荐)
  - [选项2：使用npm（替代方案）](#选项2使用npm替代方案)
- [🛠️ 手动设置（开发者）](#️-手动设置开发者)
  - [前置条件](#前置条件)
  - [安装](#安装)
  - [运行应用](#运行应用)
- [详细文档](#详细文档)
- [免责声明](#免责声明)
- [故障排除](#故障排除)

## 🚀 快速开始（非技术用户）

**一键设置和运行命令：**

### 选项1：使用一键脚本（推荐）

#### Mac/Linux：
```bash
./run.sh
```

如果遇到"权限被拒绝"错误，先运行：
```bash
chmod +x run.sh && ./run.sh
```

或者可以运行：
```bash
bash run.sh
```

#### Windows：
```cmd
run.bat
```

### 选项2：使用npm（替代方案）
```bash
cd app && npm install && npm run setup
```

**就是这样！** 这些脚本会：
1. 检查所需依赖（Node.js、Python、Poetry）
2. 自动安装所有依赖
3. 启动前端和后端服务
4. **自动打开浏览器**访问应用程序

**要求：**
- [Node.js](https://nodejs.org/)（包含npm）
- [Python 3](https://python.org/)
- [Poetry](https://python-poetry.org/)

**运行后可访问：**
- 前端（Web界面）：http://localhost:5173
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

---

## 🛠️ 手动设置（开发者）

如果您希望手动设置每个组件或需要更多控制：

### 前置条件

- Node.js和npm用于前端
- Python 3.8+和Poetry用于后端

### 安装

1. 克隆仓库：
```bash
git clone https://github.com/virattt/ai-hedge-fund.git
cd ai-hedge-fund
```

2. 设置环境变量：
```bash
# 在根目录创建.env文件
cp .env.example .env
```

3. 编辑.env文件添加API密钥：
```bash
# 用于运行OpenAI托管的LLM（gpt-4o、gpt-4o-mini等）
OPENAI_API_KEY=your-openai-api-key

# 用于运行Groq托管的LLM（deepseek、llama3等）
GROQ_API_KEY=your-groq-api-key

# 用于获取财务数据驱动对冲基金
FINANCIAL_DATASETS_API_KEY=your-financial-datasets-api-key
```

4. 安装Poetry（如尚未安装）：
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

5. 安装根项目依赖：
```bash
# 在根目录
poetry install
```

6. 安装后端应用依赖：
```bash
# 进入后端目录
cd app/backend
pip install -r requirements.txt  # 如果有requirements.txt文件
# 或者
poetry install  # 如果后端目录有pyproject.toml
```

7. 安装前端应用依赖：
```bash
cd app/frontend
npm install  # 或 pnpm install 或 yarn install
```

### 运行应用

1. 启动后端服务器：
```bash
# 在一个终端，从后端目录
cd app/backend
poetry run uvicorn main:app --reload
```

2. 启动前端应用：
```bash
# 在另一个终端，从前端目录
cd app/frontend
npm run dev
```

现在可以访问：
- 前端应用：http://localhost:5173
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

## 详细文档

更多详细信息：
- [后端文档](./backend/README.md)
- [前端文档](./frontend/README.md)

## 免责声明

本项目**仅供教育和研究目的**。

- 不适用于实际交易或投资
- 不提供任何保证或担保
- 创作者不对财务损失承担责任
- 投资决策请咨询财务顾问

使用本软件即表示您同意仅将其用于学习目的。

## 故障排除

### 常见问题

#### "命令未找到：uvicorn"错误
如果运行设置脚本时出现此错误：

```bash
[错误] 后端启动失败。请检查日志：
命令未找到：uvicorn
```

**解决方案：**
1. **清理Poetry环境：**
   ```bash
   cd app/backend
   poetry env remove --all
   poetry install
   ```

2. **或强制重新安装：**
   ```bash
   cd app/backend
   poetry install --sync
   ```

3. **验证安装：**
   ```bash
   cd app/backend
   poetry run python -c "import uvicorn; import fastapi"
   ```

#### Python版本问题
- **使用Python 3.11**：Python 3.13+可能有兼容性问题
- **检查Python版本：** `python --version`
- **如需切换Python版本**（使用pyenv、conda等）

#### 环境变量问题
- **确保.env文件存在**于项目根目录
- **从模板复制：** `cp .env.example .env`
- **添加您的API密钥**到.env文件

#### 权限问题（Mac/Linux）
如果遇到"权限被拒绝"：
```bash
chmod +x run.sh
./run.sh
```

#### 端口已被占用
如果端口8000或5173被占用：
- **终止现有进程：** `pkill -f "uvicorn\|vite"`
- **或使用不同端口**修改脚本

### 获取帮助
- 查看[GitHub Issues](https://github.com/virattt/ai-hedge-fund/issues)
- 关注[Twitter](https://x.com/virattt)更新