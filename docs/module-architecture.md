# 模块架构

> 与 `.cursor/rules/module-architecture.mdc` 对齐；2026-06 起逐步落地。

## 目标

- 新数据维度、新投研 skill 可插拔
- 出问题能快速定位（抓数 / 算信号 / 做研究 / 编排 / HTTP）
- 模块之间不互相 import 打架

## 流水线

```text
sources（抓） → BatchContext
  → pipeline.diagnose（单品种）
       → analyzers.analyze_all
       → skills.analyze_knowledge → research.compose → insight
  → services 写缓存
  → server 返回 JSON
```

投研 skill 扩展：**优先加 Playbook YAML**（`layers/`、`boards/`、`products/`、`personas/`），Python 保持薄 wrapper。

## 目录（目标态）

```text
src/
  domain/           # 合约、symbol、指数成分等静态映射
  schemas/          # 共用输出结构
  sources/          # 按数据域抓数（market / macro / global / …）
  analyzers/        # 纯计算，registry 驱动（逐步）
  research/         # Playbook 引擎 + playbooks/
  skills/           # framework / persona / insight
  pipeline/         # 原 analysis.py（待迁）
  services/         # refresh / cache
  server.py         # Flask 路由
```

## 依赖铁律

见 `.cursor/rules/module-architecture.mdc`。

## 迁移阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| A | 架构文档 + Cursor rule | 已完成 |
| B | 断环：macro drivers、index_constituents→domain、term_chain→sources | 已完成 |
| C | BatchContext + services/refresh | 已完成 |
| D | analyzers registry、manifest 驱动 framework | 待做 |
| E | analysis→pipeline、series 工具迁入 sources/common | 待做 |

## 新接数据放哪

| 类型 | 位置 |
|------|------|
| 新 API / 文件抓取 | `src/sources/{域}/` |
| 指标与阈值 | `src/analyzers/{id}.py` |
| 研究 SOP | `src/research/playbooks/...` |
| 分析员视角 | `personas/{id}.yaml` |
| 首页展示 | `services` + `global_market` 组装，读 BatchContext |
