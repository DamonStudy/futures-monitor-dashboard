# 贡献指南

感谢考虑参与 **期货决策系统**。本项目目标是做「期货主动决策研究员」——用数据模块 + 分层 Playbook 知识库，帮助盘后快速理解**市场状态**与**涨跌原因**，而非替代交易决策。

## 开始前

1. 阅读 [README.md](./README.md) 完成本地运行（需天勤账号；宏观/全球页建议配置 `TUSHARE_TOKEN`）。
2. 阅读 [docs/product-preferences.md](./docs/product-preferences.md) 了解产品边界与 UI 原则。
3. 查看 **[docs/open-source-roadmap.md](./docs/open-source-roadmap.md)** —— 开源路线图、覆盖率缺口、以及我们**希望社区从哪些维度帮忙**（数据源、Playbook、analyzer、功能、工程）。

## 可以贡献什么

| 类型 | 入口 |
|------|------|
| Playbook 知识库 | `src/research/playbooks/`，运行 `python3 scripts/research/validate_playbooks.py` |
| 数据模块 | `src/analyzers/`，遵循 `schema.py` |
| 知识 Skill | `src/skills/` |
| 功能与 UI | `src/`、`static/index.html`，遵循 `docs/ui-design-spec.md` |
| 文档 | `docs/` |
| 数据源调研 | Issue 讨论即可，PoC 可放 `scripts/` |

**请勿提交**：`.env`、本地 `data/` 缓存、券商 PDF 原文、未授权的大段研报摘录。

## Pull Request

1. 小步提交，说明「为什么改」而不只列文件。
2. Playbook 变更必须通过 `validate_playbooks.py`。
3. 改 API 或刷新逻辑时，在 PR 中说明对手动缓存/前端的影响。
4. UI 改动请对照 `docs/ui-mockups/theme-briefing.html` 与 `docs/ui-design-spec.md`。

## Issue

请先搜索是否已有同类讨论。建议标题带上维度，例如：

- `[playbook] 补充 CU 品种研究 SOP`
- `[data-source] 仓单数据 alternative`
- `[ui] 侧栏关注分改版`

推荐标签见 [open-source-roadmap.md § Issue 分类](./docs/open-source-roadmap.md#4-如何参与给未来贡献者)。

## 行为准则

- 尊重数据与内容版权；Playbook 存方法论与思维链，不存具体喊单。
- 讨论对事不对人；欢迎质疑阈值与框架，请附带可复现的例子或数据说明。

如有疑问，直接在 GitHub Issue 中 @ 维护者或开 `discussion` 标签议题。
