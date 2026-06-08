# UI 设计规范

本文档定义期货决策系统的 **视觉系统、组件约定与实现映射**，供改版 `static/index.html` 或新增模块时对齐。

- **产品原则**（信息分层、默认收起等）→ [product-preferences.md](./product-preferences.md)
- **详情页栏目归属**（总览 / 量价 / 基本面等）→ [detail-information-architecture.md](./detail-information-architecture.md)
- **风格预览稿**（选定方向）→ [ui-mockups/theme-briefing.html](./ui-mockups/theme-briefing.html)

## 1. 设计方向

**研报简报风（Template A）** — 暖白纸感、像盘后晨报 PDF，不是行情终端。

气质关键词：克制、可扫读、结论前置、证据次之、附录折叠。

### 1.2 辅助信息：全局一次，行内只留差异

**思想**（改 UI 前先对齐，避免单点删词换词）：

> 凡 **全表/全列表相同** 的操作说明、时间尺度、交互提示，只在 **一处** 交代；行内只展示 **该行独有** 的信息（名称、数值、涨跌）。

删「查看走势图」却每行仍留「180日」，只是换了一种重复——没有贯彻上述原则。

| 层级 | 放什么 | 示例 |
|------|--------|------|
| **区块/侧栏**（一次） | 本表共性：怎么展开、走势窗口多长 | 侧栏：「点击名称旁箭头展开走势（180日）」 |
| **行内**（差异） | 仅本行名称；可选 **无字** chevron 或整行可点 | 指数名一行；箭头 `caption` 色、无文字 |
| **展开后** | 图表 + 该行解读 | 不在折叠态重复尺度 |

| 做法 | 避免 |
|------|------|
| 行内仅 chevron / 行点击展开，`aria-label` 写全说明 | 每行「查看走势图」「180日」「近180日」 |
| 模块标题或侧栏 **一行** 弱提示 | 把教学文案铺满每个 matrix-name-block |
| 无走势数据行显示「—」或不渲染控件 | 无数据仍占一行辅助结构 |

**矩阵名称列**：默认 **单行标题**；有走势时右侧小箭头即可，**禁止**第二行辅助文字带重复尺度。

### 1.1 视觉品味（避免「俗」与「报警器感」）

面向**盘后决策简报**，不是彩票站、不是行情终端红点轰炸。

| 更想要 | 避免 |
|--------|------|
| 低饱和、纸感、字号与字重区分优先级 | 高饱和红/黄/蓝实心圆点、大色块徽章 |
| 关注分用 **数字 + 轻量底** 或 **左侧细条** 暗示优先级 | 列表每项一颗鲜红圆「勋章」 |
| 红/绿只表达 **涨跌、多空语义** | 红绿当装饰色铺满导航、分数、选中态 |
| 选中态：浅底 + 细 accent 边条 | 选中态大面积亮蓝底（后台默认风） |

**侧栏关注分（待统一改版）**：弃用 `score-ring` 实心圆；改为右对齐数字或 2px 左侧色条（高关注用 muted 琥珀/赤褐，非 `#ea4335` 纯红）。

---

## 2. 内容三层（全站统一）

任何页面、任何新模块必须先归入一层，**不可三层混用同一套重样式**。

| 层级 | 名称 | 放什么 | 视觉权重 |
|------|------|--------|----------|
| **L1** | 决策带 | 决策解读、走势解读首段、状态+原因主叙事 | 最强：浅暖底 + 左侧 accent 色条 |
| **L2** | 证据区 | 方向矩阵、关键位、核心指标、板块矩阵 | 中等：白/浅底卡片，1px 边框，无阴影 |
| **L3** | 附录区 | K 线、信号详表、长列表、成分展开 | 最弱：顶部分割线 + `<details>` 默认收起 |

```
L1 决策带     ← 10 秒内必须读完
L2 证据区     ← 支撑判断，可略读
L3 附录区     ← 需要时再展开
```

**禁止**：L2/L3 使用 L1 的左边色条；L1 区堆超过 1 个主标题级结论。

---

## 3. 设计令牌（Design Tokens）

落地时集中在 `static/index.html` 的 `:root`，**禁止在组件内硬编码色值**（涨跌语义色除外且须用变量）。

```css
:root {
  /* 背景 */
  --bg: #f3f0ea;           /* 主内容区外底色 */
  --bg-side: #faf8f4;       /* 侧栏、Tab 槽 */
  --panel: #fffcf7;         /* 卡片、顶栏 */
  --l1-bg: #fff9f0;        /* L1 决策带底色 */

  /* 文字 */
  --text: #2a241c;
  --muted: #6f6558;         /* 正文辅助、证据说明 */
  --subtle: #9a9084;        /* 标签、表头、附录 */

  /* 结构 */
  --line: #e4ddd2;

  /* 品牌 / 交互 */
  --accent: #8b5a2b;
  --accent-soft: #f5ebe0;
  --accent-line: #c4a574;   /* L1 边框、强调线 */

  /* 语义 · 国内涨跌惯例：红涨绿跌 */
  --danger: #b83232;        /* 涨、偏多、高关注 */
  --danger-soft: #fce8e6;
  --success: #2d6a3e;       /* 跌、偏空 */
  --success-soft: #e6f0e8;
  --warning: #9a6b00;       /* 中性偏高关注、级别提示 */
  --warning-soft: #faf0d4;

  /* 字体 */
  --font-sans: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  --font-display: "PingFang SC", "Songti SC", "STSong", "Microsoft YaHei", serif;

  /* 间距（仅使用此表） */
  --space-1: 8px;
  --space-2: 16px;
  --space-3: 24px;
  --space-4: 32px;

  /* 圆角 */
  --radius-sm: 4px;   /* pill、小标签 */
  --radius-md: 8px;   /* 卡片、按钮、矩阵格 */
  --radius-lg: 10px;  /* L1 决策带右侧圆角 */
}
```

### 3.1 颜色使用规则

| 颜色 | 允许用于 | 禁止用于 |
|------|----------|----------|
| `--accent` | 选中态、主按钮、L1 左边条、栏目标题 | 大面积背景、普通正文 |
| `--danger` / `--success` | 涨跌幅数字、矩阵多/空格、偏多/偏空标签 | 侧栏分数圆点、列表装饰、选中背景 |
| `--muted` / `--subtle` | 说明文字、附录、表头 | L1 主标题 |
| 阴影 | **不使用**（用底色对比分区） | `box-shadow` 装饰 |

---

## 4. 字体层级

全站 **4 级**，禁止新增第五级「特殊标题」。

| 令牌 | 字号 | 字重 | 字体 | 用途 |
|------|------|------|------|------|
| `display` | 20px | 600 | `--font-display` | L1 状态标题（如「趋势上行后的反转预警 · 中级行情候选」） |
| `title` | 14–15px | 600 | `--font-sans` | L2 卡片标题、栏目标题 |
| `body` | 14px | 400 | `--font-sans` | 正文、决策行、列表名 |
| `caption` | 11–12px | 600 | `--font-sans` | 组标签、eyebrow、pill、表头 |

行高：正文 `1.55–1.65`；`display` `1.45`。

**禁止**：正文中滥用 `font-weight: 800`；同一屏超过 1 处 `display` 级标题。

---

## 5. 布局

### 5.1 全局框架

| 区域 | 规格 |
|------|------|
| 顶栏 `header` | 高 52px；左：系统名 + 视图 Tab；右：刷新按钮 |
| 主栅格 `main` | 品种决策：`300px` 侧栏 + `1fr` 内容；大盘首页：单栏全宽 |
| 侧栏 `aside` | `overflow-y: auto`；`background: var(--bg-side)` |
| 内容 `content` | `overflow-y: auto`；内层 `max-width: 920px`；`padding: 20px 24px 32px` |
| 页面 `body` | `height: 100vh; overflow: hidden`（双栏独立滚动） |

### 5.2 品种决策 · 右侧模块顺序

与 [detail-information-architecture.md](./detail-information-architecture.md) 对齐，总览 Tab 内：

1. L1 · 决策解读（`insight`）
2. L2 · 方向矩阵 + 关键位（可并排 `grid`）
3. L2 · 核心指标条
4. L3 · K 线（`<details>` 默认关）
5. L3 · 各周期信号 / 详表（限量 + 折叠）

### 5.3 大盘首页 · 模块顺序

1. L1 · 走势解读（`narrative`）
2. L2 · 商品指数（宽表，可独占一行）+ **核心变量**（稀疏分组，见 5.4）
3. L3 · 走势图、成分展开（按需）

### 5.4 稀疏模块并排（减少纵向滚动）

**问题**：仅 1～3 行的分组（如「海外利率」「国内利率」）若各占满屏宽，会造成大量空白与无谓下滑。

**原则**：按 **数据密度** 选布局，不按模块「一律全宽」。

| 类型 | 行数/列数 | 布局 |
|------|-----------|------|
| 核心变量分组 | 每组通常 ≤4 行、5 列 | **多列并排** `repeat(auto-fill, minmax(300px, 1fr))` |
| 商品指数矩阵 | 行多、含代码/成分/走势 | **独占全宽** |
| 走势解读 | 3～5 条短句 | L1 全宽 |

**实现约定**：

```css
.driver-groups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-2);
  align-items: start;
}
.driver-group-block { margin-top: 0; }  /* 取消纵向 stack 的 margin-top */
.driver-groups-grid .change-matrix.compact {
  min-width: 0;   /* 禁止 560px 撑破窄卡 */
  width: 100%;
}
```

- 宽屏目标 **2～3 列**；`<900px` 自动单列。
- 组内表格保持 `overflow-x: auto`，但卡片本身不强制整页宽。
- 组标题保留「类别名 + N 项」，去掉多余说明 chip（或收进附录）。

**反例**：每个 `driver-group-block` 纵向 `margin-top` 堆叠且内部 `min-width: 560px` → 行少却占满一屏。

---

## 6. 组件规范

命名约定：语义化 class，前缀表层级。

### 6.1 壳层

| Class | 层级 | 说明 |
|-------|------|------|
| `.decision-band` | L1 | 决策带容器；`border-left: 5px solid var(--accent)` |
| `.decision-band .eyebrow` | L1 | 栏眉，如「决策解读 · 方向偏多」 |
| `.decision-headline` | L1 | `display` 级状态标题 |
| `.decision-line` + `.k` | L1 | 命中/缺项/待验行；`.k` 为 2.5em 标签 |
| `.zone-label` | — | L2/L3 分区小标题（如「证据区」「附录」） |
| `.evidence-card` | L2 | 白底卡片，`border: 1px solid var(--line)`，无阴影 |
| `.appendix-block` | L3 | 仅 `border-top` + `<details>` |

### 6.2 侧栏索引

| Class | 说明 |
|-------|------|
| `.group-label` | 板块组头；sticky；`caption` 级 |
| `.item-row` | 三列：优先级指示 · 名称/交易所 · 关注分数字 + `bias` |
| `.item-row.active` | `background: var(--accent-soft)` + 左 inset 色条（accent 色，非亮蓝） |

**列表只展示**：合约名、代码、方向标签、关注分（**数字**，非实心圆徽章）。

**关注分样式（规范目标）**：

```css
/* ✅ 冷静：数字 + 可选细条 */
.item-priority { width: 3px; border-radius: 2px; background: var(--subtle); }
.item-priority.high { background: var(--accent); }  /* 赤褐，非正红 */
.item-score { font-size: 13px; font-weight: 600; color: var(--muted); tabular-nums: 1; }
.item-row.active .item-score { color: var(--accent); }

/* ❌ 避免：score-ring 实心圆 + score-high 正红底 */
```

### 6.3 标签

| Class | 用途 |
|-------|------|
| `.pill` | L1 元信息（合约、最新价、板块共振） |
| `.pill.hot` | 高关注分等重要 pill |
| `.bias` / `.bias.short` | 偏多 / 偏空 |
| `.chip` | **仅语义标签**（方向、不可用等）；见下表 |

#### 模块头禁止装饰 chip

`module-head` 右侧 **不设** 说明型、教学型、计数型小标识。标题即足够；交互与尺度已在侧栏/§1.2 全局说明。

| 删除（装饰/复述） | 保留（语义） |
|-------------------|--------------|
| 「快速抓住重点」「分系列展示 · 含指数代码」 | 矩阵格内 多/空/中 |
| 「按类别分组 · 标题下方可展开走势」 | Hero/决策带内 偏多·偏空（改版后或改 pill） |
| 分组标题旁「3 项」 | 数据真实不可用时的正文空态（不用 chip 重复喊「暂不可用」） |
| 「更新 12:00」chip（全局 meta 已有刷新时间） | 信号卡上的数值阈值（必要时） |

**原则**：chip/pill 只表达 **本条数据的判断或状态**，不表达「这个模块是干嘛的」。

### 6.4 数据组件

| 组件 | 规则 |
|------|------|
| 方向矩阵 | 格内仅「多/空/中」；红涨绿跌着色；禁止副标题重复方向；**无小时列** |
| 关键位 | 3 列：支撑 / 确认 / 压力；优先 **日线**；无 period 不写「-」chip |
| 品种顶栏（`.detail-header`） | **单行**：左名称+标签，右 4 指标竖线分隔；无独立夜盘指标格 |
| 信号卡片（`.signal-card`） | 量价/技术/形态统一 `renderSignalCardGrid`；限量 4～6 条 |
| 期限结构 | 信号卡 → 跨期价差 3 卡 → 合约链表（≤5 行）→ `mini-chart` 折线；**禁止**两张无标题宽表叠放 |
| 变更矩阵（大盘） | 行 hover 浅底；展开行用 `accent-soft` |

#### 折线图（全站统一）

凡 **单序列折线**（大盘行内走势、期限结构曲线等），一律：

- 绘制：`drawMiniLine` / `drawStandardLineChart`（勿新写 `drawXxxCurve`）
- 视觉：暖网格 `#e4ddd2`、线色 `#8b5a2b`（`cnColors` + `neutral`）、悬停竖线+ tooltip
- 容器：`canvas.mini-chart`（高 180px，1px 边框，圆角 8px）
- 折叠面板内图表：展开后再 `draw`（避免 `getBoundingClientRect` 宽度为 0）

### 6.5 按钮与顶栏

| 类型 | 样式 |
|------|------|
| 主按钮 | 填充 `var(--accent)`；全站慎用，避免与导航抢权重 |
| 视图 Tab（`.view-tab`） | 居中胶囊槽（`.view-switch`）；active 白底 + accent 字色 + 细边框 |
| 次按钮（`.btn-ghost`） | 白底 + `var(--line)` 边框；**顶栏「刷新」** 用此样式 |
| 次按钮 / toggle | 白底 + `var(--line)` 边框；禁止与主任务导航同色大面积并列 |

**顶栏三栏**（`header.app-header`）：左 `.app-brand`（产品名 + 可选副标）· 中 `.app-nav`（大盘首页 / 品种决策）· 右 `.app-actions`（刷新）。导航是主任务，不与品牌挤在同一 flex 组。

### 6.6 文本与容器（避免错位、溢出）

常见坏味道：**标签与正文挤在同一行 inline**、**容器水平 padding 为 0**、**Grid/Flex 子项缺少 `min-width: 0`**，会导致文字贴边或被右侧硬裁切。

#### 容器内边距

| 层级 | 水平 padding | 禁止 |
|------|----------------|------|
| L1 决策带 | `20px 22px` | `padding: 2px 0` 等「上下有、左右无」写法 |
| L2 证据卡 | `16px` | 子元素用负 margin 抵消父级 padding |
| L3 附录 | `0`（靠顶部分割线） | 长文在附录内仍须 `padding` 或 grid 行布局 |

**规则**：带边框的 `section` / `.module` 若被更具体选择器覆盖 padding，必须 **显式写出四边**，不可只写上下。

#### 标签 + 长文：用 Grid，不用 inline

```css
/* ✅ 推荐：标签固定列宽，正文自动换行 */
.decision-line {
  display: grid;
  grid-template-columns: 2.8em minmax(0, 1fr);
  gap: 6px;
  align-items: start;
  line-height: 1.65;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.decision-line .k { color: var(--subtle); font-size: 12px; font-weight: 700; }

/* ❌ 避免：inline-block 标签 + 超长 inline 正文（易撑破或贴边裁切） */
```

命中/缺项/待验：**一条信息一行**；多条用列表，禁止 `join(" · ")` 拼成单行。

#### Grid / Flex 防溢出三件套

凡可能放长文的列，父级与子级同时满足：

```css
.parent { min-width: 0; }          /* grid/flex 子列 */
.text   { min-width: 0; overflow-wrap: anywhere; word-break: break-word; }
```

主布局 `grid-template-columns: 300px minmax(0, 1fr)` 中的 `minmax(0, …)` **不可删**。

#### 截断策略（分层）

| 层级 | 做法 |
|------|------|
| 数据/展示 | 列表索引、表格单元格等极窄处 → `ellipsis` + `nowrap` |
| L1 决策正文 | **必须换行**；JS `clip()` 仅作兜底（建议 ≥80 字或分行展示） |
| 标题 | `cleanInsightHeadline` 去掉「方向」「关注分」等已在标签区展示的信息 |

#### 标题区重复信息

L1 内：**栏眉**（决策解读 · 方向）、**pill**（关注分）、**headline**（状态 · 级别）三者分工，headline 不再重复方向/分数（见 `cleanInsightHeadline`）。

#### 自检（截图级）

改完决策带后目视检查：

1. 文字距左边框是否 ≥16px？
2. 最长「命中」说明是否完整换行、右侧无硬切？
3. 缩小窗口时是否仍换行而非横向溢出？
4. 标签列与正文列是否顶对齐（`align-items: start`）？

---

## 7. 数据呈现契约

### 7.0 话术气质（与产品文档一致）

解读类字段（`brief`、`headline`、`core_hits`、`narrative`、矩阵 `summary`）须符合 [product-preferences.md §解读话术风格](./product-preferences.md#解读话术风格)：**平静、明确、务实**。

生成侧约束摘要：

- 单条命中说明建议 ≤40 字；超长截断或拆条，不在 UI 拼一行。
- `headline` 仅 `状态 · 级别`，不含方向/分数/感叹。
- `verify` / 待验必须是 **可观察条件**，非建议性口号。

### 7.1 字段映射

前端 `render*` 与后端 skill 字段对应关系（新增 skill 时必须更新此表）。

| UI 区块 | Skill / 字段 | 展示约束 |
|---------|--------------|----------|
| L1 标题 | `insight.brief.headline` 或 `state` + `level` | 仅一处 |
| L1 行 | `insight.core_hits` / `gaps` / 待验 | 各 ≤3–4 条，超出摘要 |
| 方向矩阵 | `direction_matrix` | 标签化格子，无长句 |
| 关键位 | `key_levels` | 最近 3 类点位 |
| 核心指标 | 合约诊断字段 | 4–6 个，不铺全表 |
| 信号列表 | 各 analyzer | 每周期 ≤4 条 +「另有 N 条」 |
| 详表 | 同主题卡片已有则不再全量 | ≤6 行 |

空态文案统一句式：`暂无{模块名}。` / `{字段}待更新`。

---

## 8. 交互状态

| 场景 | 行为 |
|------|------|
| 切换品种 | K 线、附录折叠 **重置为收起** |
| 列表滚动 | 切换品种 **不改变** 列表 `scrollTop` |
| 刷新 | 按钮 `disabled` + 等待态；不整页空白闪烁 |
| 矩阵格点击 | 仅更新同区解释文案，不弹窗 |
| 大盘走势图 | 行内展开，不占 L1 位 |

---

## 9. 改版检查清单

加新 UI 模块前逐项确认：

1. 归入 L1 / L2 / L3 哪一层？样式是否匹配？
2. 是否与决策解读重复？重复则降级到 L3 或删除。
3. 是否决策必需？否 → 默认折叠。
4. 是否使用令牌色？有无硬编码 hex？
5. 是否破坏双栏独立滚动？
6. 是否更新第 7 节数据契约表？

---

## 10. 反例（不要出现）

- 全页统一白卡片 + `box-shadow`（后台感）
- Hero、列表、矩阵三处重复 `state · level`
- L1 决策带内嵌 K 线或 20 行表格
- 五彩 chip 堆满首屏
- `module-head` 旁「快速抓住重点」「分系列展示」「N 项」等装饰角标
- 侧栏鲜红/亮黄圆点分数（「报警器」感）
- 选中行大面积高饱和蓝底
- 为「好看」新增第五种字号或第六种主色
- 附录默认展开占用首屏

---

## 11. 文件与维护

| 文件 | 职责 |
|------|------|
| `static/index.html` | 唯一前端：CSS 令牌、布局、组件 class、`render*` |
| `docs/ui-design-spec.md` | 本规范；改视觉规则先改文档再改代码 |
| `docs/ui-mockups/theme-briefing.html` | 静态预览；大改视觉前可先更新 mockup |
| `docs/product-preferences.md` | 产品原则；与 UI 冲突时 **产品原则优先** |
| `src/skills/*.py` | 输出字段；影响第 7 节契约时需同步文档 |

### 11.1 推荐改动流程

**禁止单点换药**：只删某一个词、只改某一个 class，容易留下同类的下一层重复（如删掉「查看走势图」却保留每行「180日」）。应先写清原则，再 **一轮统一改**。

```
1. 对照本节 + product-preferences，确认要贯彻的是哪条「思想」
2. 在 ui-mockups 或文档中列出受影响组件清单（凡同类项一并列入）
3. 更新 ui-design-spec.md（若原则或令牌有变）
4. 一次性改 index.html：:root、布局、render*、侧栏提示
5. 走查：品种决策 + 大盘首页 + 矩阵行展开 + 切换品种 + 折叠态
```

---

## 12. 落地状态

| 项 | 状态 |
|----|------|
| 规范文档 | 已建立（本文） |
| `index.html` 统一改版 | **第二轮已落地** — 品种页/资金结构/周期/顶栏；见 §12.2 验收项 |
| 预览稿 Template A | 已完成 → `ui-mockups/theme-briefing.html` |

### 12.1 统一改版清单（Template A + 已沉淀原则）

| # | 类别 | 内容 | 状态 |
|---|------|------|------|
| 1 | 视觉令牌 | 暖纸色、去阴影、accent 赤褐 | ✅ |
| 2 | L1 决策带 | padding、grid 行布局、headline 去重、`judgment_note` | ✅ |
| 3 | 侧栏索引 | 去 `score-ring` 实心圆；选中态去亮蓝 | 部分 |
| 4 | 大盘布局 | 核心变量并排、走势 `drawMiniLine`、标题四级 | ✅ |
| 5 | **辅助信息** | 矩阵行：**单行名称 + 无字 chevron**；尺度仅一处说明 | 部分 |
| 6 | **模块头** | 去掉装饰 chip | ✅ |
| 7 | 话术 | 平静、明确、务实 | 持续 |
| 8 | 分析周期 | 日/周优先；剥 hour；矩阵无小时 | ✅ |
| 9 | 品种顶栏 | `renderDetailHeader` 单行；去夜盘指标格 | ✅ |
| 10 | 资金结构 | 期限结构卡片化 + 统一折线 | ✅ |
| 11 | 顶栏导航 | 品牌 / 导航 / 操作三栏 | ✅ |

### 12.2 改版验收清单（实操）

提交前在 **大盘首页** 与 **品种决策** 各走查一遍。产品向清单见 [product-preferences.md §改版验收清单](./product-preferences.md#改版验收清单)。

#### 周期与缓存

| 检查项 | 期望 | 代码落点 |
|--------|------|----------|
| 后端分析周期 | 仅 `day` / `week` 进入量价/技术/关键位 | `src/analyzers/__init__.py`、`signal_periods()` |
| 缓存读取 | 剥 `hour` 信号与点位；矩阵含 hour 则重建 | `src/services/cache.py` |
| 前端展示 | 信号/点位过滤 hour；关键位优先日线 | `filterSignalsByPeriod`、`levelsForDisplay`、`normalizeSkills` |
| 服务 | 改 `src/` 后重启 `PORT=8011 python3 server.py` | `.cursor/rules/server-ops.mdc` |
| 数据 | 提示用户点「刷新数据」，不只浏览器强刷 | — |

#### 品种决策页模块

| 模块 | 期望 |
|------|------|
| 顶栏 | 一行：左标签区 + 右四指标；无夜盘独立格 |
| 总览 | 决策解读有 `judgment_note`；无重复关注分 pill |
| 方向矩阵 | 日/周/月列；解读区右侧 50% 并排 |
| 量价技术 | 三模块均为信号卡片栅格；周期 chip 仅 day/week |
| 关键点位 | 卡片脚注「日线 · …」；无小时线 |
| K 线 | 单层 `<details>` 默认收起；红涨绿跌 |
| 资金结构 | 价差三卡 + 合约链表 + `mini-chart` 折线 |

#### 图表

| 类型 | 绘制函数 | 容器 class |
|------|----------|------------|
| 大盘行内走势 | `drawMiniLine` | `.row-chart-canvas` / `.mini-chart` |
| 期限结构曲线 | `drawStandardLineChart` → `drawMiniLine` | `#term-curve-chart.mini-chart` |
| K 线 | `drawKline` | `#kline` |
| 季节性（多序列） | `drawSeasonalChart` | `#seasonal-chart` |

**禁止**：为单折线新增独立 canvas 绘制逻辑（蓝线+圆点+冷灰网格等与大盘不一致的样式）。

#### 表格与限量

- 默认 `MAX_DETAIL_TABLE_ROWS = 6`；期限结构合约链 ≤5
- 超出文案：`另有 N 行未展开` / `另有 N 个合约未展示` / `另有 N 个信号未展示`
- **禁止**：「卡片区已保留最近关键位」用于非关键位模块

#### 推荐走查路径

```
1. 大盘首页 → 展开一行走势 → 核对折线样式与悬停
2. 品种决策 → 选 1 个品种 → 总览 10 秒扫读
3. 量价技术 → 关键点位周期为日线
4. 资金结构 → 期限结构布局与折线
5. 切换大盘/品种 → 顶栏导航与刷新文案
6. 切换左侧品种 → 列表滚动位置稳定
```
