# Feature2Testcases

基于 FastAPI + React 的需求驱动测试管理平台

## 主要功能

- AI智能分析需求和测试用例生成
- 项目管理
- 需求管理
- 测试用例管理
- 测试运行管理

## 技术栈

### 环境要求
 |技术      |版本      |说明             |
 |---------|---------|----------------|
 |Python|3.11.7|后端运行环境|
 |Node.js|v26.13.0|前端构建|
 |npm|11.20.0|包管理|
 |SQLite|3.41.2|单文件数据库|

### 后端 backend/

|技术      |版本      |说明             |
 |---------|---------|----------------|
 |FastAPI|>=0.110.0|Web 框架：REST路由、依赖注入、OpenAPI文档、CORS|
 |uvicorn[standard]|>=0.29.0|ASGI服务器|
 |Pydantic|2.13.4|请求体模型校验|
 |python-multipart|0.0.31|解析上传文件|
 |openai|1.109.1|LLM客户端|
 |PyPDF2|3.0.0|提取PDF文档里的文本需求|
 |openpyxl|3.1.0|生成Excel|

### 前端 frontend/

|技术      |版本      |说明             |
 |---------|---------|----------------|
 |React|18.3.1|组件库|
 |react-router-dom|6.30.6|路由|
 |react-markdown|9.1.0|在页面渲染markdown内容|
 |Vite|5.4.21|开发服务器与生产构建|
 |axios|1.19.0|HTTP客户端|

### 测试

|技术      |版本      |说明             |
 |---------|---------|----------------|
 |pytest|7.4.0|测试框架|
 |httpx|0.28.1|-|


## 项目结构目录

```
Feature2Testcases/
├── backend/                              # 后端（FastAPI）
│   ├── app/
│   │   ├── main.py                       # 后端入口：注册路由、CORS、托管 static/
│   │   ├── config.py                     # 全局配置：输出根目录、SQLite 数据路径
│   │   ├── api/
│   │   │   └── routes/                   # 接口定义（按业务域分类）
│   │   │       ├── __init__.py           # 总路由：聚合所有业务域子路由
│   │   │       ├── health.py             # 健康检查
│   │   │       ├── agent.py              # Agent 相关：提交任务、查状态、下载
│   │   │       ├── agent_settings.py     # 模型设置：查询 / 更新（写 .env 即时生效）
│   │   │       ├── history.py            # 任务历史：列表 / 保存联动 / 详情 / 删除（含目录清理）
│   │   │       ├── projects.py           # 项目管理：列表 / 新建 / 详情 / 更新 / 删除（级联）
│   │   │       ├── features.py           # 需求管理：列表 / 新建 / 更新 / 删除 / 单需求生成用例
│   │   │       ├── testcases.py          # 用例管理：筛选分页 / 新建 / 更新 / 删除 / Agent 入库
│   │   │       └── testruns.py           # 测试运行：批次创建 / 列表 / 详情 / 记录结果 / 结束 / 统计
│   │   ├── services/
│   │   │   ├── pipeline.py               # 流水线：串联需求分析 → 测试用例生成
│   │   │   ├── db_conn.py                # 数据库连接入口：统一 DB 路径 + 开启外键约束
│   │   │   ├── project_store.py          # 项目存储：SQLite CRUD + 需求数统计 + 级联删除
│   │   │   ├── feature_store.py          # 需求存储：SQLite CRUD + Agent 批量入库（upsert）
│   │   │   ├── testcases_store.py        # 用例存储：SQLite CRUD + 筛选分页 + Agent 批量入库
│   │   │   ├── testruns_store.py         # 运行存储：批次 + 用例快照/结果 + 统计口径 + 状态回写
│   │   │   └── history_store.py          # 历史存储：task_history CRUD + 保存联动标记 + 磁盘产物重建 + 启动回填
│   │   ├── tasks/
│   │   │   └── manager.py                # 任务管理：内存任务表 + 后台线程池
│   │   └── agents/                       # Agent 目录（标准 Python 包，可直接 import）
│   │       └── unified_agent/            # 统一 Agent
│   │           ├── __init__.py           # 包入口：导出 UnifiedAgent
│   │           ├── main.py               # CLI 入口（--stage analyze / testcases / all）
│   │           ├── agent.py              # 主控类：阶段1分析 → 阶段2生成用例
│   │           ├── config.py             # Agent 配置（API Key、超时、默认输出目录等）
│   │           └── src/
│   │               ├── file_parser.py    # 文件解析（txt / md / pdf）
│   │               ├── analyzer.py       # 阶段1：一次调用产出「文档章节 + 需求点」
│   │               ├── doc_generator.py  # 需求文档生成器（md）
│   │               ├── testcases_generator.py # 阶段2：需求点 → 测试用例（LLM）
│   │               └── file_generator.py # Excel 生成
│   ├── static/                           # 前端构建产物
│   ├── output/                           # 生成文件（按任务 ID 分目录）
│   ├── data/                             # SQLite 数据
│   ├── requirements.txt                  # 后端 Python 依赖
│   ├── .env                              # API Key 配置
│   └── .env.example                      # 配置模板
├── frontend/                             # 前端（React + Vite）
│   ├── index.html                        # 页面入口
│   ├── package.json                      # 前端依赖与脚本
│   ├── vite.config.js                    # 端口、代理、构建输出配置
│   └── src/
│       ├── main.jsx                      # React 入口（包 HashRouter）
│       ├── App.jsx                       # 路由配置
│       ├── index.css                     # 全局基础 + 通用组件样式
│       ├── css/                          # 页面级样式（与 views/ 一一对应）
│       │   ├── AgentPipelineView.css     # Agent 页面样式（按组件分节）
│       │   ├── ProjectsView.css          # 项目页面样式（卡片网格 / 弹窗 / 分页）
│       │   ├── FeaturesView.css          # 需求页样式（左右分栏 / 需求卡片）
│       │   └── TestcasesView.css         # 用例页样式（筛选栏 / 表格 / 行展开）
│       ├── apis/                         # 接口调用（按页面分类）
│       │   ├── index.js                  # 汇总入口：统一导出各页面接口
│       │   ├── http.js                   # 公共 axios 实例（baseURL /api）
│       │   ├── agent.js                  # Agent 页面：任务 + 模型设置接口
│       │   ├── projects.js               # 项目页面：列表 / 新建 / 更新 / 删除
│       │   ├── features.js               # 需求页面：列表 / 新建 / 更新 / 删除 / 生成用例
│       │   └── testcases.js              # 用例页面：筛选分页 / 新建 / 更新 / 删除
│       ├── hooks/
│       │   └── usePipeline.js            # 业务逻辑 Hook（状态 + 提交 + 轮询）
│       ├── layouts/
│       │   ├── MainLayout.jsx            # 主布局：左侧菜单 + 右侧内容
│       │   └── MainLayout.css            # 布局样式
│       ├── components/
│       │   ├── agents/
│       │   │   ├── InputCard.jsx         # 第一步：输入需求卡片
│       │   │   ├── ProgressCard.jsx      # 第二步：分析进度卡片
│       │   │   ├── ErrorCard.jsx         # 错误提示卡片
│       │   │   ├── ResultCard.jsx        # 第三步：查看下载结果卡片
│       │   │   ├── MarkdownView.jsx      # Markdown 文档渲染组件
│       │   │   ├── SettingsModal.jsx     # 设置弹窗（模型 / API Key）
│       │   │   ├── HistoryDrawer.jsx     # 历史记录抽屉（全部/未保存/已保存分组、搜索 / 查看还原 / 删除）
│       │   │   └── SaveProjectModal.jsx  # 分析完成后「保存为项目」弹窗（项目+需求+用例三步入库）
│       │   ├── projects/
│       │   │   ├── ProjectCard.jsx       # 项目卡片（名称/修改日期/来源/状态 + 编辑/删除）
│       │   │   └── ProjectEditModal.jsx  # 新建 / 编辑项目弹窗
│       │   ├── features/
│       │   │   ├── ProjectListSidebar.jsx # 需求页左侧项目列表（搜索过滤）
│       │   │   ├── FeatureCard.jsx       # 需求卡片（展开/收起 + 编辑/生成用例/删除）
│       │   │   └── FeatureEditModal.jsx  # 新建 / 编辑需求弹窗
│       │   └── testcases/
│       │       ├── FilterBar.jsx         # 用例筛选栏（七维度 + 关键字 + 新建）
│       │       ├── TestcaseTable.jsx     # 用例表格
│       │       ├── TestcaseRow.jsx       # 用例行（状态徽标点击切换 + 行展开详情）
│       │       └── TestcaseEditModal.jsx # 新建 / 编辑用例弹窗（项目-需求联动下拉）
│       └── views/
│           ├── AgentPipelineView.jsx     # Agent 页面：编排卡片 + 历史/设置/保存项目入口
│           ├── ProjectsView.jsx          # 项目页面：卡片列表 + 弹窗编排 + 分页
│           ├── FeaturesView.jsx          # 需求页面：左项目列表 + 右需求卡片
│           └── TestcasesView.jsx         # 用例页面：筛选 + 表格 + 分页
├── start.sh                              # 一键启动脚本
├── .gitignore                            # Git 忽略规则
└── README.md                             
```

## 使用方式

### 准备工作

1. 安装 [Python 3](https://www.python.org/downloads/) 和 [Node.js](https://nodejs.org/)
2. 配置 API Key：

   ```bash
   cp backend/.env.example backend/.env
   ```

   然后编辑 `backend/.env`，填入要使用的模型和 Key：

   ```env
   OPENAI_API_KEY=sk-key
   OPENAI_BASE_URL=https://api.openai.com/v1
   OPENAI_MODEL=gpt-4o-mini
   ```

### 一键启动（推荐）

```bash
./start.sh
```

### 手动启动（可选）

```bash
# 终端 1：启动后端（在 backend 目录下）
cd backend
python3 -m uvicorn app.main:app --port 8000

# 终端 2：启动前端（在 frontend 目录下）
cd frontend
npm run dev
```

访问 http://localhost:5173 使用。

### 页面操作

1. **输入需求**：直接输入文字描述，或切换到"上传需求文档"上传 `.txt` / `.md` / `.pdf` 文件。
2. **开始分析**：点击按钮后依次执行需求分析（约 30~90 秒）和测试用例生成（约 1~5 分钟），页面实时显示进度。
3. **查看下载**：页面直接展示需求分析文档内容，并可下载：
   - 需求分析文档（`.md`）
   - 测试用例（`.xlsx`）
4. **设置模型**：点击右上角"设置"按钮，可修改模型、Base URL 与 API Key，保存后立即生效（写入 `backend/.env`）。
5. **保存为项目**：分析完成后，点击对应按钮保存为项目，确认后项目、需求、测试用例一并入库，来源标记为"Agent 生成"。
6. **管理项目**：左侧菜单进入"项目"页，卡片展示项目名称、修改日期、来源、状态；点击卡片或"编辑"按钮修改，支持新建、删除（带确认，级联删除其下需求与用例；已关联该项目的历史记录自动恢复为"未保存"）与分页。
7. **管理需求**：左侧菜单进入"需求"页，左侧项目列表可搜索过滤，右侧需求卡片支持展开/收起、新建、编辑、删除；点击「生成测试用例」可针对单个需求调 LLM 生成用例并直接入库。
8. **管理用例**：左侧菜单进入"测试用例"页，支持七维度组合筛选与关键字搜索，点击状态徽标切换执行状态，点击行展开查看前置条件/步骤/预期结果，支持新建（项目-需求联动下拉）、编辑与删除。
9. **查看历史**：点击右上角「历史记录」打开右侧抽屉，可在「全部 / 未保存 / 已保存」分组间切换，每条记录标注是否已保存为项目；支持搜索、查看历次分析结果（点击「查看」还原结果卡片，支持下载；未保存的可继续「保存为项目」，保存成功后状态自动回写、按钮置灰防重复）。删除历史会连同 `backend/output/<任务ID>/` 目录一并清理，已保存到项目库的数据不受影响。
10. **测试运行**：支持创建运行批次、按需求分组执行并记录结果、结束后锁定、执行率/通过率统计。

### 后端接口测试

```bash
cd backend
pip install -r requirements-dev.txt   # 首次需安装 pytest / httpx
python3 -m pytest
```

在临时目录中运行、不触碰真实数据：测试通过环境变量 `OUTPUT_ROOT` 指向临时目录、并把 `db_conn.DB_PATH` 替换为临时 SQLite 文件实现全隔离；每个用例前自动清空表，测试结果与 `data/management.db`、`output/` 的真实数据完全无关。