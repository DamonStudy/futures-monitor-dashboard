# 知识蒸馏体系

> 目标：从研报 / 公众号 / 大 V 长文中，**只把「怎么想」蒸馏进 Playbook**；数字、阈值、当下多空由 **Analyzer + 实时数据** 承担。  
> 同一作者对不同板块可以有不同逻辑链——靠 **标签 + 步骤级 scope** 区分，而不是再建十个 persona。

## 设计决策：为何不以 RAG / 研报数字为主库

本项目的材料有两个硬约束，决定了 **方法论蒸馏** 是唯一可持续的路径：

| 约束 | 含义 | 对系统的要求 |
|------|------|----------------|
| **人工更新** | PDF/公众号不会自动、高频同步；进一批、蒸馏一批 | 知识库必须是 **可 diff 的 YAML 框架**，不是「扔进去就能问」的向量堆 |
| **报告数字过期** | 库存、价格、开工率在报告印刷时即已滞后 | **永不把研报里的具体数值写进 Playbook**；当前值只来自 Analyzer + 行情/外部 API |

因此：

- **RAG 答问**适合「材料新、数字仍有效、问一句答一句」的场景；不适合作为本项目的 **runtime 主路径**。
- **借鉴研报** = 借鉴 **变量名、检查顺序、因果链、证伪条件**（方法论），不是借鉴 **123 万吨、看至 3800**。
- `parsed/*.md` 与 catalog 的角色是 **蒸馏与溯源的阅读原文**，不是每品种 insight 的实时检索源。

若未来材料量极大，RAG 仅可作为 **蒸馏阶段辅助**（帮 agent 找「这段在讲什么框架」），产出仍必须落入 Playbook schema；**运行时数字一律 analyzer 填**。

## 一条铁律

```text
Playbook 存思维（变量名、顺序、证伪）
Analyzer 存事实（当前取值、信号、阈值）
Catalog 存溯源（哪篇 PDF、何时、蒸馏到哪一步）
```

| 来源材料里的内容 | 怎么处理 |
|------------------|----------|
| 「先看库存再看开工，最后看利润」 | ✅ 蒸馏进 `questions` / `focus` |
| 「港口库存 123 万吨、同比 -8%」 | ❌ 不写入 YAML；运行时由 `warehouse_receipts` 等提供 |
| 「我们认为尿素震荡偏弱」 | ❌ 不存当周观点；可提炼为「淡储/复合肥/出口」需求栈检查顺序 |
| 「若累库 + 铁水见顶 → 关注逢高做空窗口」 | ✅ 蒸馏为 `strategy` 链 + `confirmation`/`invalidation` |
| 2023 年报告里的具体价位、目标价 | ❌ 永不入库 |
| 多年有效的「铜 = 结构性 + 周期性」 | ✅ `knowledge_type: framework`，`freshness: evergreen` |

**旧报告的数字**：只证明作者**当时**这么论证；对系统**无取值意义**，最多参考「当时用了哪些变量」。

---

## 三层资产

```text
L0 原始资料     期货原始资料/{作者或机构}/*.pdf
       ↓ parse
L1 解析缓存     data/research/parsed/{作者}/*.md     ← 人工/agent 阅读用，不直接进 runtime
       ↓ distill
L2 蒸馏知识     playbooks/personas|boards|products/*.yaml
       ↓ index
L1.5 资料索引   playbooks/catalogs/{作者}.yaml       ← 每篇报告打标、追踪蒸馏进度
       ↓ runtime
              analyzers → skills → insight
```

---

## 标签体系（四维 + 可选两维）

每个 **persona 步骤**（`reasoning_chain` 里的一条）建议具备以下维度。

### 1. 作者维 `author` / persona

| 字段 | 说明 |
|------|------|
| Playbook 顶层 `id` | 运行时 `persona_{id}`，如 `citic`、`peifengke_cu` |
| `author` | 展示名：中信期货研究所、培风客 |
| `scope` | 匹配哪些品种：`all_commodities` / `boards` / `products` |

**原则**：同一研究所 / 同一大 V **一个 persona**，板块差异用步骤级标签表达，避免「中信宏观 persona + 中信黑色 persona」碎片化。

### 2. 逻辑链维 `chain`

| 取值 | 含义 | 典型内容 |
|------|------|----------|
| `macro` | 宏观→大类映射 | 流动性、联储、国内政策、油价地缘 |
| `cross_asset` | 大类配置顺序 | 超配贵金属/有色、低配黑色 |
| `board` | 板块共性框架 | 黑色「铁水-库存-利润」、能化「利润链」 |
| `product` | 单品种深度链 | 甲醇内地-沿海、尿素需求栈 |
| `strategy` | 策略形态（非永久多空） | 累库逢高做空、期权替代 |
| `event` | 事件驱动模板 | 伊朗冲击→进口→MTO |
| `arbitrage` | 价差/跨境结构 | 内外价差、进口窗口 |
| `technical` | 若作者有独立技术哲学 | 少用；默认走 `layers/technical.yaml` |

### 3. 适用范围维 `boards` / `products` / `tags`

| 字段 | 说明 |
|------|------|
| `boards` | `[黑色]`、`[能化]`… 空 = 全板块可用（常配合 `macro`） |
| `products` | `[i, rb]`、`[MA]`… 空 = 不限定单品种 |
| `tags` | 自由标签，便于检索与维护，如 `[冬储, 港口库存, MTO]` |

**同一作者、不同板块不同看法** → 写 **多条步骤**，各自带不同 `boards`/`products`/`tags`，而非改 persona 名字。

示例（中信）：

- `chain: macro` + 无 scope → 全品种背景
- `chain: board` + `boards: [黑色]` → 黑色供需四件套
- `chain: product` + `products: [MA]` → 甲醇专用链
- `chain: strategy` + `products: [i]` → 铁矿策略形态（与宏观步骤可并存、由 insight 选用）

### 4. 知识类型维 `knowledge_type`

| 取值 | 蒸馏什么 | 示例 |
|------|----------|------|
| `framework` | 长期有效的分析框架 | 铜 = 结构性 + 周期性 |
| `checklist` | 必问问题列表 | 开工/到港/库存/利润四表 |
| `variable` | 关注哪些变量（**名称**） | 「港口库存」「MTO 利润」 |
| `causal` | 因果链 / 传导顺序 | 地缘→进口→港口去库→MTO 降负 |
| `seasonal` | 季节性规律 | 冬储、发运旺季 |
| `risk` | 风险与尾部 | 地缘、政策、低波动突变 |

一条步骤可只选一种主类型；复杂步骤在 `focus` 里混合，但 `knowledge_type` 取最主要的那类。

### 5. 数据策略维 `data_policy`（关键）

| 取值 | 含义 |
|------|------|
| `no_numbers` | 步骤内禁止出现任何具体数值 |
| `mind_only` | 仅来自过期材料，只保留思维，不挂 analyzer |
| `reference_structure` | 可引用「表结构」（供需四表），数值由 analyzer 填 |
| `live_link` | 必须挂 `analyzer_links`，运行时用 live 数据验证 |

**默认**：persona 步骤用 `reference_structure` 或 `live_link`；超过 6 个月的周报蒸馏时优先 `mind_only` + `reference_structure`。

### 6. 时效维 `freshness`

| 取值 | 复审周期 |
|------|----------|
| `evergreen` | 框架类，年度扫一眼即可 |
| `semi_annual` | 每半年对照新报告修订 |
| `event` | 事件模板，叙事失效即标记 deprecated |
| `deprecated` | 保留 id，不再被 selector 优先选用（可选实现） |

---

## 每篇报告（Catalog）打哪些标

`playbooks/catalogs/{author}.yaml` 中，**每一篇 PDF** 一行：

```yaml
- file: 20260608-中信期货-累库压力下铁矿逢高做空策略.pdf
  report_date: "2026-06-08"
  parsed_ok: true
  chain: strategy          # 本篇主逻辑链
  tags: [铁矿, 累库, 做空, 波动率]
  boards: [黑色]
  products: [i]
  distill_status: done     # pending | partial | done | skip
  distilled_to:            # 写入了哪些 step id
    - citic_i_inventory_short_rally
  data_policy: mind_only   # 本篇数字不入库，只提炼策略形态
  knowledge_type: strategy
  freshness: event
```

| Catalog 字段 | 用途 |
|--------------|------|
| `distill_status` | 维护进度，避免重复蒸馏 |
| `distilled_to` | 溯源到 Playbook 步骤 |
| `report_date` | 判断材料是否「只剩思维价值」 |
| `skip` | 纯重复、质量差、与已有 step 完全重叠 |

---

## 蒸馏步骤里「提炼哪些信息」

对每条 **`reasoning_chain` 步骤**，按下面清单产出（**不要**产出观点口号）：

| 产出字段 | 写什么 | 不写什么 |
|----------|--------|----------|
| `title` | 这一步判断什么 | 「看多」「重磅」 |
| `focus` | 变量/主题名词 | 具体库存吨数 |
| `questions` | 可核对、可回答 yes/no 或方向的问题 | 「后市如何」 |
| `fallback` | 缺数据时的默认推理顺序 | 复制研报摘要 |
| `analyzer_links` | 用哪个 live 模块填数 | — |
| `confirmation` | 逻辑成立的 **条件**（可观测） | 目标价 |
| `invalidation` | 逻辑失效条件 | 「风险自担」套话 |

Persona 顶层还可有：

- `confirmation` / `invalidation` / `risk_factors` / `seasonal_notes`：该作者**跨步骤**共性，仍不写数字。

---

## 蒸馏工作流（人工或 Agent）

```text
1. 入库    PDF → 期货原始资料/{机构}/
2. 解析    parse_reports.py → parsed/*.md
3. 登记    catalogs/*.yaml 补一行，打 chain/tags/boards/products
4. 判断    数字是否过期？→ data_policy: mind_only
           是否新框架？  → 新 step 或合并进已有 step
           是否重复？    → distill_status: skip，notes 指向已有 step
5. 提炼    只写 questions/focus/fallback，过一遍 data_policy
6. 挂接    analyzer_links 能对上的必挂；对不上写进 gaps 说明缺模块
7. 校验    validate_playbooks.py
8. 回写    catalog.distilled_to + distill_status: done
```

### 合并 vs 新建步骤

| 情况 | 做法 |
|------|------|
| 与已有 step 同一框架，只是又多一篇周报 | 不新建；catalog 指向已有 step，`freshness` 复审即可 |
| 同作者对同一板块 **框架升级** | 改原 step 的 `questions`，catalog 记 `partial` |
| 同作者对同一板块 **观点相反** | **不**覆盖；若框架不同则新建 step 并打不同 `tags`；若只是周度多空 → **不蒸馏** |
| 事件链（伊朗、菜油过山车） | `chain: event`，`freshness: event`，叙事过期标 `deprecated` |

---

## 与产品决策闭环的对应

蒸馏出的步骤，应能回答 [product-preferences.md](./product-preferences.md) 里六步中的某一步：

| 决策步 | 优先 chain / knowledge_type |
|--------|------------------------------|
| 状态 / 背景 | macro, cross_asset |
| 主导叙事 | board, product, framework |
| 一致/分歧 | 多 persona 同 chain 不同 step（未来 insight） |
| 缺口 | checklist + live_link 未命中 → gaps |
| 触发 | strategy, causal + confirmation |
| 失效 | invalidation |

---

## 示例对照

### 培风客 · 铜（独立大 V，单品种）

- Persona：`peifengke_cu`，`scope.products: [cu]`
- 步骤：`knowledge_type: framework`，`freshness: evergreen`
- `data_policy: reference_structure` + `analyzer_links`
- **不**把「2025 Q2 看多」写进 YAML

### 中信期货 · 全板块（机构）

- Persona：`citic`，`scope.all_commodities: true`
- 宏观步骤：无 `boards`，`chain: macro`
- 铁矿策略：`products: [i]`，`chain: strategy`，`data_policy: mind_only`
- Catalog：`catalogs/citic.yaml` 52 篇，`parsed_ok: 29`

---

## 文件与模板

| 文件 | 作用 |
|------|------|
| [personas/_example.yaml](../src/research/playbooks/personas/_example.yaml) | 带完整标签字段的 persona 模板 |
| [catalogs/citic.yaml](../src/research/playbooks/catalogs/citic.yaml) | 报告级索引示例 |
| [research-playbooks.md](./research-playbooks.md) | Playbook 维护与 runtime 说明 |

新增机构：复制 catalog 结构 + 新建 `personas/{id}.yaml`，**不要**往 `layers/macro.yaml` 里堆带立场内容。

---

## 业界可参考的沉淀形态（借什么、不借什么）

后面会持续进材料，**扩展性**来自「分层 + 固定 schema + 索引」，而不是把 PDF 全文塞进向量库就完事。下面几类是机构与开源里较成熟的做法，以及和本项目的映射。

### 对照总表

| 业界形态 | 典型做法 | 可借鉴点 | 不建议照搬 |
|----------|----------|----------|------------|
| **研究框架 Playbook** | 卖方可研「研究框架」PDF、CME 课程、团队 Issue Tree | ✅ 你现在的 `reasoning_chain` + `questions` | 把每篇周报观点写进 YAML |
| **知识原子 + 溯源** | 中信建投「信谛听」：研报拆成可溯源知识原子，问答带原文链接 | ✅ `catalogs/*.yaml` 每篇 `file` + `distilled_to` | 10 万原子全量 embedding 当主库 |
| **组件化投研** | 泰康等：数据/指标/图表/观点组件，研究员自行组装 | ✅ Analyzer 组件 + Playbook 步骤选用 | 无 schema 的自由文档堆 |
| **标签库 / 画像** | 「智研+」500+ 标签基金画像 | ✅ `chain` + `tags` + `boards`/`products` 多维标 | 标签爆炸不合并到 step |
| **知识图谱 KG** | FinReflectKG、QuantMind：实体-关系-三元组 | ⚠️ 仅对 **因果链** 用 `knowledge_type: causal` 表达 | 一上来建全品种 ontology |
| **Graph RAG** | 检索时沿关系多跳 | ⚠️ 二期：`parsed/` 片段检索辅助蒸馏 | 替代 Playbook 运行时逻辑 |
| **假设驱动研究** | 买方：Hypothesis → Evidence → Update → Kill | ✅ `confirmation` / `invalidation` / `gaps` | 只存结论不存证伪 |
| **ADR / 变更记录** | 工程：Architecture Decision Record | ✅ 步骤 `superseded_by`、persona `version`（见下） | 每改一行写长文 |
| **Diátaxis 四型文档** | Tutorial / How-to / Reference / Explanation | ✅ framework=Explanation，checklist=How-to | 四种混在一个 md |

**结论**：你现在的 **Catalog（索引）+ Playbook（框架）+ Analyzer（事实）** 三角，本质上接近机构「框架数字化 + 组件化数据 + 溯源索引」，比纯 RAG 更贴 **决策闭环**；缺的是 **版本、去重、维护脚本**，不是再上一套 KG。

### 三种常见架构路线（选型）

```text
路线 A  文档/RAG 为主     PDF → 向量库 → LLM 答问
        扩展快，但难维护「同一作者不同板块」、数字易 hallucinate

路线 B  图谱为主         PDF → 三元组 → Graph RAG
        关系清晰，但 schema 成本高、期货快变量难穷举

路线 C  框架为主（本项目） PDF → Catalog 打标 → Playbook 蒸馏 → Analyzer 填数
        进材料要人工/agent 提炼，但 runtime 稳定、可审计、可 diff
```

后续材料增多，推荐 **C 为主、A 为辅**：`parsed/` 只服务 **蒸馏与溯源**，不直接参与每品种 insight（除非二期做「引用原文段落」展示）。

### 可继续借鉴的「沉淀单元」形态

若单条 `reasoning_chain` 步骤变长，可拆 **二级单元**（仍不存数字）：

| 单元 | 存什么 | 放哪 |
|------|--------|------|
| **Framework Card** | 3～5 条 focus + 论证顺序 | Playbook step |
| **Checklist Card** | questions 列表 | 同上 |
| **Causal Mini-graph** | A→B→C 文字链（非图数据库） | step.notes 或 `causal_steps: []` |
| **Source Atom** | 报告日期、章节、distill_status | catalog 一行 |
| **Live Binding** | analyzer id 列表 | analyzer_links |

这与「知识原子」同构，但 **原子类型受 schema 约束**，避免维护地狱。

---

## 扩展性与维护性（持续进材料时的约定）

### 1. 新增材料的标准路径（不要分叉）

```text
期货原始资料/{作者}/           ← 只放原件，按 YYYYMMDD 命名
catalogs/{作者}.yaml          ← 先登记 + 打标（可 parsed_ok: false）
parse → parsed/{作者}/
蒸馏 → 合并进 personas/{id}.yaml 或 boards/products（通用框架才进层）
validate_playbooks.py
```

**禁止**：新券商 PDF 直接改 `layers/macro.yaml`（会再次杂糅）。

### 2. 版本与演进（借鉴 ADR）

Persona 顶层建议逐步加上：

```yaml
version: 1
updated: "2026-06-08"
changelog:
  - date: "2026-06-08"
    note: 自中信 52 篇蒸馏 macro/board/product 链
```

步骤级合并/废弃：

```yaml
- id: citic_old_methanol_story
  freshness: deprecated
  superseded_by: citic_event_methanol_iran
```

运行时 selector 可对 `deprecated` 降权（待实现）。

### 3. 去重规则（避免 step 爆炸）

| 情况 | 动作 |
|------|------|
| 新周报与已有 step 同框架 | 只更新 catalog.distilled_to，**不新建 step** |
| 框架升级 | 改原 step，changelog 记一笔 |
| 仅周度多空相反 | **不蒸馏** |
| 新作者 | 新 persona + 新 catalog，不并入 citic |

### 4. 目录命名约定（扩展）

```text
期货原始资料/
  中信期货研究所/          → persona citic
  培风客-铜/               → persona peifengke_cu
  宏观-{作者}/             → persona macro_{作者}（若做宏观对比）
  {大V}-{侧重}/            → 如 某人-黑色；仍是一个 persona id
```

一个作者一个 persona id；「侧重」体现在 catalog 与 step 的 tags，不是新 id。

### 5. 建议维护脚本（可后续实现）

| 脚本 | 作用 |
|------|------|
| `parse_reports.py` | 已有；按 `--source` 解析 |
| `validate_playbooks.py` | 已有；schema 校验 |
| `check_distill_gap.py`（待写） | catalog 里 parsed_ok 且 distill_status≠done |
| `check_orphan_steps.py`（待写） | step 无 catalog 引用且非 framework 层 |

### 6. 与 RAG/KG 的边界（二期）

若材料量到 **数百篇/作者** 且蒸馏跟不上：

- **Catalog + parsed** 做轻量 RAG：蒸馏时检索相似段落，**输出仍写入 Playbook schema**
- **不**让 LLM 在 runtime 直接读 PDF 生成多空（违背 product 调性）

参考：[QuantMind](https://github.com/LLMQuant/quant-mind) 两阶段（ingest / retrieve）、FinReflectKG 的 schema-guided extraction——都只借 **「有 schema 的抽取」**，不借 **runtime 生成观点**。

---

## 后续可增强（未实现）

- Selector 按 `freshness: deprecated` / `superseded_by` 降权
- `insight` 输出同作者不同 `chain` 的一致/分歧
- `distill_status` 仪表盘或 `check_distill_gap.py`
- Persona `version` + step `superseded_by` 字段写入 schema 校验
- 可选 `playbooks/atoms/` 存放极短 causal/checklist 卡片供多 persona 引用
