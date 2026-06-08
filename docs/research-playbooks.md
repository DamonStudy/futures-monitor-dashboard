# 研报 Playbook 维护说明

完整 **知识蒸馏标签与提炼规范** 见 [knowledge-distillation.md](./knowledge-distillation.md)。

## 定位

Playbook 是一套**分层结构化知识库**：存研究方法论（SOP，怎么想），不存会过期的行情数字。

**事实**来自数据模块（`src/analyzers/`）；**思维**来自知识型 Skill（`src/skills/`）。

## 两类后端能力

| 类型 | 目录 | 职责 | 输出 |
|------|------|------|------|
| **数据模块 Analyzer** | `src/analyzers/` | 算数字、信号、阈值 | `kind: analyzer`，API 字段 `analyzers` |
| **知识型 Skill** | `src/skills/` | 按 SOP 选用步骤、串联解读 | `kind: skill`，API 字段 `skills` |

数据模块清单：`price_volume`、`technical_signals`、`candlestick_patterns`、`key_levels`、`term_structure`、`warehouse_receipts`、`position_rank`。

知识型 Skill：`macro_framework`、`technical_framework`、`board_framework`、`product_framework`、`persona_{id}`、`insight`。

## 五层知识 + 编排

```text
L1 宏观层      layers/macro.yaml       → macro_framework
L2 技术面层    layers/technical.yaml   → technical_framework
L3 板块层      boards/{板块}.yaml      → board_framework
L4 品种层      products/{代码}.yaml    → product_framework
L5 外部视角    personas/{id}.yaml      → persona_{id}
编排           compose + insight.py      → insight（决策解读）
```

运行时流水线：

```text
数据 analyzers → framework / persona skills → insight
```

## 目录结构

```text
src/analyzers/                    # 数据模块
src/skills/                       # 知识型 Skill
src/research/playbooks/
  manifest.yaml
  layers/
  boards/
  products/
  personas/                       # _example.yaml 为模板，不参与加载
```

执行器：`src/research/playbook_runner.py`；编排：`src/research/compose.py` → `src/skills/insight.py`。

## 维护方式

**蒸馏规范（必读）**：[knowledge-distillation.md](./knowledge-distillation.md) — 人工更新、报告数字过期 → **只蒸馏方法论，不做 RAG 主库**。

| 层级 | 推荐来源 |
|------|----------|
| macro / technical | 教材、CME 课程；`期货宏观/` 仅索引进 catalog，立场进 persona |
| board / product | 券商品种研报 → 蒸馏 framework/checklist |
| persona | `期货原始资料/{机构或作者}/` → catalog + personas/*.yaml |

```bash
python3 scripts/research/parse_reports.py --source 期货原始资料/中信期货研究所 --output data/research/parsed/citic
python3 scripts/research/enrich_playbooks.py   # 同步 catalog 索引与 distill 状态
python3 scripts/research/validate_playbooks.py
```

蒸馏进 Playbook 的 `title`、`focus`、`fallback` 及最终 `insight` 话术，对齐 [product-preferences.md §解读话术风格](./product-preferences.md#解读话术风格)：**平静、明确、务实**（交班记录体，非股评摘抄）。

## Persona 逻辑链标签（中信期货示例）

同一券商/作者挂 **一个 persona**，步骤用标签区分逻辑链与适用范围：

| 字段 | 含义 | 示例 |
|------|------|------|
| `chain` | 逻辑链类型 | `macro` / `board` / `product` / `cross_asset` / `strategy` / `arbitrage` / `event` |
| `tags` | 人类可读标签 | `[黑色, 冬储, 库存]` |
| `boards` | 步骤适用板块（可选） | `[黑色]` |
| `products` | 步骤适用品种（可选） | `[i, rb]` |
| `scope.all_commodities` | persona 匹配全部商品 | 中信 `citic` |

资料索引：`src/research/playbooks/catalogs/citic.yaml`（52 篇 PDF 的 chain/tags 标注）。

```bash
python3 scripts/research/parse_reports.py \
  --source 期货原始资料/中信期货研究所 \
  --output data/research/parsed/citic
```

## Playbook 字段

| 字段 | 含义 |
|------|------|
| `reasoning_chain` | SOP 步骤：`title`、`focus`、`questions`、`fallback` |
| `analyzer_links` | 挂接的数据模块 id（旧字段 `skill_links` 仍兼容） |
| `confirmation` / `invalidation` | 逻辑成立 / 证伪条件 |
| `sources` | 知识来源追溯 |

品种代码：`KQ.m@SHFE.rb` → `rb`

## 运行时

- **选用**：根据 state、方向、关注分、analyzer 信号，从 Playbook（含 persona）挑选相关 SOP 步骤
- **编排**：`insight` skill 输出 `brief` / `core_hits` / `gaps`
- 有 `analyzer_links` 且命中：拼接数据模块信号
- 无数据：展示该层关注项与关键问题
- 旧缓存若只有合并的 `skills` 数组，前端仍兼容

## 待办：宏观多 Persona（设计共识，尚未选人）

> 记录于 2026-06：用户确认的方向，分析员名单待定后再落地。

### 问题

`期货原始资料/期货宏观/` 等资料**数量有限、质量参差**，且不同来源**立场与结论常冲突。全部蒸馏进一个 `layers/macro.yaml` 会导致框架杂糅、步骤自相矛盾，`insight` 无法判断「听谁的」。

### 目标结构

```text
layers/macro.yaml     ← 极薄：regime 怎么读、日历/利率怎么用、宏观→品种过滤（方法论，少观点）
personas/
  macro_{分析员}.yaml ← 每位宏观分析员一个 persona（完整世界观 / 思维链）
  peifengke_cu.yaml   ← 已有：品种向培风客（可未来拆出 macro 向）
insight               ← 选用 + 对比分歧，而非和稀泥合成一条线
```

| 层级 | 存什么 | 不存什么 |
|------|--------|----------|
| `macro.yaml` | 读数据的方法、挂 `macro_regime` | 具体多空、过期叙事 |
| `persona/macro_*` | 该分析员的论证顺序、关注变量、证伪条件 | 单次研报结论、具体价位 |
| `macro_regime` analyzer | 10Y、日历、最新非农/CPI 等 | — |

### insight 对比（计划行为）

1. 同一盘面下，多个 `persona_*` 各自选用步骤并输出 signals/gaps  
2. `insight` 增加 **一致点 / 分歧点**（例如都盯利率路径；分歧在 AI capex vs 油价二阶效应）  
3. 分歧映射到**品种敏感度**（有色 vs 黑色等），而非抽象多空口号  

### 人选原则（落地时再定）

- 先 **2–3 个** 世界观稳定、资料可持续更新的分析员  
- 优先：你已长期跟踪的独立大 V、或固定首席的**框架**（非周报喊单合集）  
- 现有 `macro.yaml` v2 中带时效的内容（K 型、AI 独引擎等）**后续迁入**具体 persona，框架层**瘦身**  

### 资料目录约定（建议）

```text
期货原始资料/
  培风客-铜/           → persona peifengke_cu（已有）
  宏观-{分析员A}/      → persona macro_{A}（待建）
  宏观-{分析员B}/      → persona macro_{B}（待建）
  期货宏观/            → 临时合集；蒸馏完成后按分析员拆目录，避免继续杂糅
```

### 落地 checklist（有名单后执行）

- [ ] 选定 2–3 个宏观分析员，各建 `personas/macro_*.yaml`  
- [ ] 瘦身 `layers/macro.yaml`（保留通用 4–5 步）  
- [ ] 扩展 `insight` / `compose`：输出 `agreements` / `disagreements`  
- [ ] 前端「盯控解读」展示宏观视角对比（可选折叠）  
- [ ] `manifest.yaml` 登记各分析员资料路径  

