# 期货决策系统

基于天勤行情 API 的期货量价/技术面决策系统，并提供商品大盘首页。

当前品种决策页以量价和技术面分析为主；大盘首页接入中证商品指数、宏观利率/汇率、外盘商品和股票风险偏好变量。暂不接入消息面、基本面和 EDB 数据。

产品方向上，本项目不只是静态数据看板，而是要逐步演进成「期货主动决策研究员」：由系统稳定呈现市场状态、异常和证据，由知识型 Skill 主动给出思考路径、结论和后续验证点。

**寻找贡献者**：欢迎从 [数据源、Playbook 知识库、功能模块、UI、工程](docs/open-source-roadmap.md) 等维度提 Issue——不必写代码，思路与踩坑同样有价值。见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 运行

复制配置模板：

```bash
cp .env.example .env
```

在 `.env` 中填写本地天勤账号密码：

```bash
TQ_ACCOUNT=你的天勤账号
TQ_PASSWORD=你的天勤密码
ENABLE_TERM_STRUCTURE=1
TUSHARE_TOKEN=你的 TuShare Token
```

启动服务：

```bash
PORT=8011 python3 server.py
```

浏览器打开 `http://127.0.0.1:8011`

## 分析架构（两类能力）

后端把「算数据」和「做研究 SOP」明确分开：

### 1. 数据模块（Analyzers）— `src/analyzers/`

**职责**：从行情/K 线**确定性计算**数字、信号、阈值。不是 SOP，是事实工厂。

| 模块 | 说明 |
|------|------|
| `price_volume` | 多周期量价、涨跌幅、成交量/波动分位 |
| `technical_signals` | TA-Lib 技术指标与阈值信号 |
| `candlestick_patterns` | K 线形态识别 |
| `key_levels` | 支撑、压力、确认/失效位 |
| `term_structure` | 合约链期限结构与跨期价差 |
| `warehouse_receipts` | 仓单（外部数据，可选） |
| `basis` | 期现基差（AkShare 期现价格表） |
| `macro_regime` | 利率、美元、关键宏观发布、7 日经济日历 |
| `position_rank` | 持仓排名（外部数据，可选） |

输出字段带 `"kind": "analyzer"`，API 中位于 `item.analyzers`。

### 2. 知识型 Skill — `src/skills/`

**职责**：按 Playbook / 视角 **SOP** 选用分析步骤、串联解读。不重复算指标，引用数据模块的证据。

| Skill | 说明 |
|-------|------|
| `macro_framework` | 宏观层思维框架 |
| `technical_framework` | 技术面框架 |
| `board_framework` | 板块基本面框架 |
| `product_framework` | 品种框架 |
| `persona_*` | 大 V / 外部视角（按 scope 匹配） |
| `insight` | 编排层：选用 + 命中/缺项/待验 → 「决策解读」 |

输出字段带 `"kind": "skill"`，API 中位于 `item.skills`。

流水线：

```text
数据 analyzers → 知识 skills（framework / persona）→ insight
```

## 研报 Playbook

`期货研报/` PDF → 蒸馏为 YAML，存放在 `src/research/playbooks/`。Playbook 步骤通过 `analyzer_links`（兼容旧字段 `skill_links`）挂接数据模块。

```bash
python3 scripts/research/parse_reports.py
python3 scripts/research/validate_playbooks.py
```

维护说明见 [docs/research-playbooks.md](docs/research-playbooks.md)、[docs/knowledge-distillation.md](docs/knowledge-distillation.md)。

**知识库原则**：材料人工更新、研报数字过期 → **只蒸馏方法论进 Playbook**，当前数字由 Analyzer 实时计算；**不以 RAG 为主库**。

## 文件结构

```text
server.py
src/domain/            # 静态领域模型（指数成分映射等）
src/schemas/           # analyzers / skills 共用输出结构
src/sources/           # 外部数据抓取（market / macro / …）+ BatchContext
src/services/          # refresh 编排、缓存读写
src/macro/             # 宏观 context 聚合（快照 + 经济日历）
src/analyzers/         # 数据模块（含 macro_regime）
src/skills/            # 知识型 Skill（SOP / 编排）
src/research/          # Playbook 加载、选用、编排引擎
src/global_market/     # 大盘首页 payload 组装
src/analysis.py        # 单品种诊断 pipeline（待迁 pipeline/）
static/index.html
docs/module-architecture.md
```

## 开源与协作

项目计划发布到 GitHub，欢迎从**数据源、Playbook 知识库、数据模块、功能与 UI、工程基础设施**等维度参与讨论与贡献。

- 改进项与希望社区帮助的维度：[docs/open-source-roadmap.md](docs/open-source-roadmap.md)
- 贡献流程：[CONTRIBUTING.md](CONTRIBUTING.md)

## 安全说明

`.env`、`data/` 已加入 `.gitignore`，勿提交账号密码或本地缓存。研报 PDF 等原始素材请仅本地使用，向仓库贡献时请提交蒸馏后的 Playbook YAML 并注明 `sources`。
