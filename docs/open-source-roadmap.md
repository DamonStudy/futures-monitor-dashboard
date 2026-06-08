# 开源路线图与协作指南

> 记录时间：2026-06-06  
> 目的：项目计划发布到 GitHub，邀请更多人试用，并从社区获得多维度指导与贡献。

本文档汇总**当前可改进点**、**希望社区帮助的维度**、**贡献方式**。与 [期货决策系统开发交接.md](./期货决策系统开发交接.md)、[research-playbooks.md](./research-playbooks.md)、[product-preferences.md](./product-preferences.md) 互补：交接文档讲「现在是什么」，本文讲「还缺什么、你可以怎么帮」。

---

## 1. 项目一句话

**期货主动决策研究员**：用确定性数据模块算盘面事实，用分层 Playbook 知识库做研究 SOP，在 UI 上主动给出「状态 + 原因 + 待验证点」——不是行情终端，也不是自动下单系统。

核心壁垒：`多维数据 → 专家知识库 → 精简呈现`。

---

## 2. 当前完成度快照

| 维度 | 已有 | 缺口 / 待打磨 |
|------|------|----------------|
| 行情数据 | 天勤实时/历史 K 线；AkShare 合约规格 | EDB 非价量需付费账号；部分外部源不稳定 |
| 数据模块 | 8 个 analyzer（量价、技术、形态、关键位、期限结构、仓单、持仓排名、宏观 regime） | 基本面指标模块尚未设计；analyzer 与 Playbook 挂接仍不全 |
| 知识库 | 宏观/技术框架 + 4 板块 + 12 品种 Playbook + 1 个 persona（培风客-铜） | 合约池约 61 个，Playbook 覆盖率 ~20%；宏观多 persona 仅设计共识 |
| 功能 | 品种决策页、商品大盘首页、手动刷新与当日缓存、决策解读（insight） | 历史复盘、板块热力图、换月标记、UI 规范落地等 |
| 工程 | Flask 单服务、`validate_playbooks.py` | 无 LICENSE、无 CI、无自动化测试、无 Issue/PR 模板 |

---

## 3. 希望社区帮助的维度

以下按**贡献类型**划分。欢迎在 GitHub Issue 中标注对应标签（见文末建议标签）。

### 3.1 数据源

**现状**

- **核心**：天勤 `tqsdk`（账号密码见 `.env.example`）
- **补充**：AkShare（合约规格、仓单、持仓排名等）；TuShare（宏观快照、全球商品/股指部分变量）
- **已评估暂缓**：天勤 EDB（401 无权限）、金十/SHMET/东财/Mysteel 等公开消息面（噪声、稳定性、版权）

**希望得到的指导**

| 主题 | 具体问题 | 理想贡献形式 |
|------|----------|--------------|
| 替代/补充数据源 | 哪些基本面、宏观、持仓、仓单源**稳定、可结构化、许可清晰**？ | Issue 讨论 + 可选 PoC 脚本（放 `scripts/`） |
| 天勤 EDB | 有权限的用户能否验证指标清单与接入成本？ | 文档 + 可选 `macro_regime` / 新品种 analyzer 扩展 |
| 消息面 | 若接入，应做「事件日历」还是「品种关联过滤」？哪些源值得维护？ | 方案文档，不要求首版就写爬虫 |
| 数据许可 | 券商 PDF、大 V 文章、抓取数据的版权边界 | 在 Playbook / 素材引用规范上给建议 |
| 刷新策略 | 全量刷新慢；哪些模块适合增量/异步？ | 架构建议或 PR |

**边界（维护者偏好）**

- 先把**量价 + 技术面决策体验**做扎实，再扩基本面/消息面。
- 不默认接入需要登录、风控复杂或噪声过大的源。

---

### 3.2 底层 Skill 知识库（Playbook）

**架构**（详见 [research-playbooks.md](./research-playbooks.md)）

```text
L1 宏观层      layers/macro.yaml       → macro_framework
L2 技术面层    layers/technical.yaml   → technical_framework
L3 板块层      boards/{板块}.yaml      → board_framework
L4 品种层      products/{代码}.yaml    → product_framework
L5 外部视角    personas/{id}.yaml      → persona_{id}
编排           insight                   → 命中 / 缺项 / 待验
```

**事实**来自 `src/analyzers/`；**思维**来自 YAML Playbook；运行时由 `playbook_runner` + `insight` 编排。

**覆盖率缺口**（2026-06）

| 层级 | 文件数 | 说明 |
|------|--------|------|
| layers | 2 | macro 计划「瘦身」；technical 可继续补 SOP 步骤 |
| boards | 4 | 黑色 / 能化 / 农产品 / 贵金属；缺有色、金融、航运等 |
| products | 12 | manifest 中列出的 rb/hc/i/jm/j/ur/ma/bu/lh/au/ag/si |
| personas | 1 | `peifengke_cu`；宏观多 persona **名单待定** |

**希望得到的指导**

| 主题 | 说明 |
|------|------|
| 品种 Playbook | 为未覆盖主力合约补充 `products/{code}.yaml`（方法论/SOP，非喊单） |
| 板块 Playbook | 有色、软商品等板块的共性研究链条 |
| Persona 蒸馏 | 如何从大 V / 首席**框架**蒸馏为 YAML（见 `personas/_example.yaml`） |
| 宏观多视角 | 选定 2–3 位分析员 → `personas/macro_{id}.yaml` + insight **一致点/分歧点** |
| analyzer_links | 哪些 Playbook 步骤应挂接哪个 analyzer id；缺数据时的 fallback 文案 |
| 校验与质量 | 扩展 `validate_playbooks.py` 规则；Playbook 评审 checklist |

**贡献 Playbook 的推荐流程**

```bash
# 1. 编辑 YAML（参考 _example 与现有 rb.yaml）
# 2. 校验
python3 scripts/research/validate_playbooks.py
# 3. PR 说明：知识来源、适用品种、不存过期价格/具体仓位
```

**素材与版权**

- 本地 `期货原始资料/`、`期货研报/` 用于蒸馏，**不建议将 PDF 原文提交到 Git**。
- Playbook 中通过 `sources` 字段追溯出处；贡献时请说明是否为你自有总结或已获授权的结构化提炼。

**已记录的设计共识（待实现）**

- `layers/macro.yaml` 只保留方法论薄层；带时效观点迁入具体 `persona/macro_*`。
- `insight` 对多个 persona 输出 **agreements / disagreements**，映射到品种敏感度而非和稀泥。

---

### 3.3 数据模块（Analyzers）

**现有模块**

| id | 职责 | 外部依赖 |
|----|------|----------|
| `price_volume` | 多周期量价、分位 | 天勤 K 线 |
| `technical_signals` | TA-Lib 指标与阈值 | 天勤 K 线 |
| `candlestick_patterns` | K 线形态 | 天勤 K 线 |
| `key_levels` | 支撑/压力/失效位 | 天勤 K 线 |
| `term_structure` | 跨期价差（`ENABLE_TERM_STRUCTURE=1`） | 天勤合约链 |
| `warehouse_receipts` | 仓单 | AkShare 等 |
| `position_rank` | 会员持仓排名 | 新浪等 |
| `macro_regime` | 利率、日历、宏观发布 | TuShare + `src/macro/` |
| `directional_matrix` | 方向矩阵（多维度单元格） | 天勤 K 线 |

**希望得到的指导**

| 主题 | 说明 |
|------|------|
| 新 analyzer | 基差、库存、利润、价差链等——需先定义**输入源 + 输出 schema**（`src/analyzers/schema.py`） |
| 阈值校准 | 各状态/信号的历史命中率；是否需要可配置阈值文件 |
| 性能 | 全品种刷新耗时；哪些 analyzer 可懒加载或按关注分跳过 |
| 与 Playbook 对齐 | manifest 中 `runtime.analyzers` 与 YAML `analyzer_links` 保持一致 |

---

### 3.4 功能模块与产品体验

**短期产品优先级**（与交接文档一致，欢迎 reorder 讨论）

1. 活跃品种筛选门槛优化（`MIN_AVG_VOLUME_20` / `MIN_AVG_OI_20`）
2. 板块热力图 + 板块共振解释
3. 历史刷新结果留存与复盘
4. 「昨日关注榜 → 今日表现」
5. 主力换月标记与解释
6. 各市场状态的复盘统计，用于调阈值

**UI / 信息架构**（详见 [ui-design-spec.md](./ui-design-spec.md)）

| 待落地项 | 说明 |
|----------|------|
| Template A 视觉 | 决策带 padding、侧栏去实心圆点、选中态去亮蓝、核心变量网格 |
| 同一结论只说一次 | 综合提炼为唯一主叙事出口 |
| K 线默认折叠 | 避免做成行情终端 |
| 预览稿 | `docs/ui-mockups/theme-briefing.html` 为参考 |

**主动解读（insight）演进**

- 当前：规则选用 Playbook 步骤 + 拼接 analyzer 信号
- 方向：异常触发时主动卡片；多 persona 分歧对比；后续可选 LLM 辅助**外显推理**（需严格引用 evidence，不替代规则层）

**明确不做（除非讨论后改边界）**

- 自动交易建议、实盘下单
- 首版强依赖社区舆情爬虫
- 默认定时全量刷天勤（成本与账号限制）

---

### 3.5 工程与开源基础设施

发布 GitHub 前建议补齐：

| 项 | 状态 | 建议 |
|----|------|------|
| LICENSE | 缺失 | 选定 OSI 许可证（如 MIT / Apache-2.0） |
| CONTRIBUTING.md | 见仓库根目录 | 指向本文与 PR 规范 |
| CI | 缺失 | `validate_playbooks.py` + `python -m compileall src` + 可选 lint |
| 测试 | 缺失 | analyzer 纯函数单测；Playbook schema 快照测试 |
| Issue / PR 模板 | 缺失 | 按下方维度分类 |
| 敏感数据 | `.env` 已 ignore | 勿提交 PDF 原文、账号、本地 `data/` 缓存 |
| 依赖 | `requirements.txt` 无版本 pin | 可考虑下限版本或 lock 文件 |
| TA-Lib | 系统级依赖 | README 补充 macOS / Linux 安装说明 |

**本地运行**（贡献者必读）

```bash
cp .env.example .env   # 填写天勤账号；宏观/全球页需要 TUSHARE_TOKEN
pip install -r requirements.txt
PORT=8011 python3 server.py
```

---

## 4. 如何参与（给未来贡献者）

1. **先试用**：配好 `.env`，刷新几个品种，看决策页与大盘首页是否符合 [product-preferences.md](./product-preferences.md) 的定位。
2. **选维度**：从上文 3.1–3.5 选一个你最熟悉的（数据 / Playbook / analyzer / 功能 / 工程）。
3. **开 Issue**：描述问题或方案，贴上维度标签；大改动请先讨论再 PR。
4. **提 PR**：小步可 review；Playbook 变更请附 `validate_playbooks.py` 通过截图或 CI 绿勾。

**Issue 分类建议（GitHub labels）**

| Label | 用途 |
|-------|------|
| `data-source` | 数据源调研、接入、许可 |
| `playbook` | YAML 知识库、persona、蒸馏流程 |
| `analyzer` | 计算模块、schema、阈值 |
| `feature` | 产品功能、复盘、板块视图 |
| `ui/ux` | 界面与信息架构 |
| `infra` | CI、测试、文档、许可证 |
| `discussion` | 方向讨论，暂无代码 |
| `good first issue` | 小范围、文档或单个 Playbook |

---

## 5. 维护者当前最缺的「非代码」帮助

若你暂时不写代码，以下同样宝贵：

- **期货研究方法论**：某板块「先看什么、再验证什么」的 SOP 是否靠谱
- **数据源踩坑**：哪些 API 免费额度够用、哪些字段不可信
- **Persona 人选**：宏观/品种维度值得长期跟踪的 2–3 位分析员及其**框架**（非喊单）
- **产品反馈**：10 秒能否扫完首屏？哪些重复信息最烦？
- **合规与版权**：开源仓库里 Playbook 引用券商报告摘要的合理写法

---

## 6. 文档索引

| 文档 | 内容 |
|------|------|
| [README.md](../README.md) | 快速启动与架构概览 |
| [期货决策系统开发交接.md](./期货决策系统开发交接.md) | 状态机、评分、缓存、暂缓项 |
| [research-playbooks.md](./research-playbooks.md) | Playbook 维护与宏观多 persona 设计 |
| [product-preferences.md](./product-preferences.md) | 产品四条原则 |
| [ui-design-spec.md](./ui-design-spec.md) | 视觉与组件规范 |
| [detail-information-architecture.md](./detail-information-architecture.md) | 详情页模块映射 |

---

## 7. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-06 | 初版：开源前改进项与社区协作维度 |
