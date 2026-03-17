# 开发者贡献规范

本文档面向希望为 ChineseResearchLaTeX 提交 Issue 或 Pull Request 的开发者。目标只有一个：让外部协作真正帮助项目演进，而不是制造额外维护成本。

本项目当前采用明确的 **Issue 先行** 流程：

1. 先提 Issue，说明问题、动机或提案。
2. 等待维护者确认方向、边界或实现层级。
3. 只有在维护者明确表示欢迎推进后，再提交 PR。

未经过 Issue 讨论和维护者确认的 PR，可能会被直接关闭。这不是针对贡献者个人，而是为了避免垃圾 PR、重复劳动、错误分层和与项目路线不一致的大改。

---

## 为什么要求先提 Issue

本仓库已经从“单一模板仓库”演进为“公共包 + 薄项目 + 官方脚本入口 + AI Skills”的协作仓库。很多改动表面上看只是改一个模板，实际上会影响：

- `packages/` 下多个产品线共享的样式、字体或脚本
- `projects/` 下示例项目与 Release 资产
- `scripts/`、`README.md`、`CHANGELOG.md`、`AGENTS.md` 等公开承诺的官方工作流

因此，维护者需要先判断一件事应该落在哪一层、是否符合当前路线、是否值得合并，避免出现以下情况：

- 把共享逻辑复制回单个项目目录
- 按旧目录结构或旧工作流提交改动
- 做了大规模重构，但与当前主线不兼容
- 改动很大，却没有验证官方构建链路

---

## Issue 阶段应该提供什么

请优先使用 GitHub Issues，而不是先写代码再“发起试试看”。

一个高质量 Issue 至少应包含：

- 你要解决的具体问题，或你要新增的具体能力
- 为什么这件事值得做，受益对象是谁
- 你判断会影响哪一层：`packages/`、`projects/`、`scripts/`、`docs/`、`skills/`
- 你准备如何验证：编译、脚本校验、像素对比、文档同步等
- 如果是新模板/新功能，请说明是否已有可公开的示例、基线或学校规范依据

如果是 Bug，请尽量补充：

- 受影响的模板或包
- 操作系统与 TeX 环境
- 复现命令
- 报错日志或截图

如果是功能提案，请尽量补充：

- 预期用户场景
- 为什么现有包/脚本无法满足
- 是否会影响已有公开接口或 Release 资产

---

## PR 提交前的前置条件

只有在维护者已经在 Issue 中明确表示“可以做”“欢迎 PR”“按这个方向推进”之后，才建议开始编码并提交 PR。

默认不鼓励以下做法：

- 先写一大堆代码，再要求维护者接受设计
- 跳过 Issue 直接提 PR
- 把个人偏好型重构包装成“顺手优化”
- 在没有共识的情况下改公开工作流、脚本入口或目录结构

请把“维护者明确同意”理解为 PR 的前置条件，而不是可选礼节。

---

## 本项目欢迎什么样的 PR

以下方向通常是受欢迎的，但仍然应先开 Issue 对齐边界：

### 1. 基于公共包扩展新的毕业论文模板

这是当前明确欢迎的贡献方向之一。

理想形态是：

- 共享逻辑优先沉淀到 `packages/bensz-thesis/`
- 学校/学位差异通过 profile、style 或公共包扩展实现
- `projects/thesis-*` 只保留薄封装、示例正文、项目级 wrapper 和公开演示资产
- 项目根目录补齐 `template.json`，至少包含 `project_name`、`school`、`degree`
- `degree` 使用统一枚举：`bachelor` / `master` / `doctor`

提交这类 PR 时，最好同时说明：

- 学校与学位来源
- 是否有可公开展示的正文/图片/参考文献
- 是否已通过 `python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir <项目路径>` 验证

### 2. 修复公共包或官方脚本中的真实问题

例如：

- `packages/bensz-nsfc/`、`packages/bensz-paper/`、`packages/bensz-thesis/`、`packages/bensz-cv/` 中的共享问题
- 根级 `scripts/` 或包级 `scripts/` 的安装、构建、校验、打包问题
- README/文档与真实脚本接口不一致的问题

这类 PR 的价值在于减少重复劳动、提升稳定性，并保持“官方入口”口径一致。

### 3. 补充与当前主线一致的文档和测试

例如：

- 为真实存在的脚本补充说明
- 为现有工作流补测试
- 修正文档中已经过时的描述

前提是文档内容必须以当前真实目录结构和真实脚本行为为准，而不是基于旧版本记忆。

---

## 通常不欢迎或必须先充分讨论的 PR

以下类型如果没有充分共识，通常不会直接合并：

- 未开 Issue、未获维护者确认的 PR
- 大规模“重构一切”的 PR
- 把共享逻辑复制到 `projects/` 的 PR
- 直接手改 README 中自动生成区域的 PR
- 为尚未落地的能力预埋复杂抽象或过度设计
- 改动官方脚本入口，却不更新 README / CHANGELOG / AGENTS 的 PR
- 依赖私有素材、私有正文、私有头像、不可公开 PDF 的模板 PR
- 与当前分层模型冲突的“单项目特化实现”

维护者也可能关闭“看起来能运行，但不符合项目演进方向”的 PR。

---

## 开发与提交时的工程要求

请尽量遵守以下规则：

### 修改边界

- 只改与当前任务直接相关的文件
- 优先做最小范围修改，不顺手夹带无关清理
- 不要把公共逻辑复制粘贴回示例项目
- 不要按旧版仓库结构想当然地放文件

### 目录分层

- 共享样式、共享资源、共享脚本优先改 `packages/`
- 项目示例正文、项目差异、演示资产优先改 `projects/`
- 项目级公共文档改 `README.md`、`docs/`、`CHANGELOG.md`
- VS Code 固定配置优先改 `scripts/vscode/`，再通过同步脚本下发

### 验证方式

请优先使用官方入口验证，而不是只跑手写的裸命令。

常见示例：

```bash
python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir projects/NSFC_General
python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir projects/paper-sci-01
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-smu-master
python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir projects/cv-01 --variant all
python packages/bensz-nsfc/scripts/validate_package.py
```

如果你没有运行某项验证，请在 PR 描述里明确写出原因。

### 文档同步

以下改动通常需要同步文档：

- 官方脚本入口变化
- 目录结构变化
- 公共包接口变化
- 开发者工作流变化

至少请检查：

- `README.md`
- `CHANGELOG.md`
- `AGENTS.md`
- 受影响包或项目下的 README / docs

---

## PR 描述建议包含什么

为了让维护者更快 review，建议 PR 描述至少包含：

- 对应 Issue 链接
- 改动目的
- 修改层级与涉及目录
- 验证命令与结果
- 是否有已知限制、warning 或后续工作

如果是版式相关改动，建议附上：

- 编译产物截图
- 像素比对结果
- 改动前后说明

---

## 新增毕业论文模板的额外要求

如果你的 PR 是“新增学校/学位模板”，请特别注意：

- 优先复用 `packages/bensz-thesis/`，不要另起一套独立实现
- `projects/thesis-*` 必须保持薄项目结构
- 项目根目录必须有 `template.json`
- 示例内容必须可公开，不得混入真实隐私数据
- 如调整 VS Code 工作区或项目 wrapper，应保持与项目现有 launcher 体系一致

如果你的实现只是“复制一个旧项目再硬改”，通常不符合本项目的长期维护方向。

---

## Review 与合并预期

提交 PR 后，请默认接受以下可能性：

- 维护者要求拆分 PR，先合并较小部分
- 维护者要求把逻辑从 `projects/` 回收到 `packages/`
- 维护者要求补验证、补文档或补 `CHANGELOG.md`
- 维护者认为方向不合适，直接关闭 PR

“代码已经写好了” 不等于 “适合合并”。本项目更看重长期结构稳定、可维护性和官方工作流一致性。

---

## 一句话原则

如果你想提高 PR 被合并的概率，请遵循这条简单规则：

**先在 Issue 里对齐方向，再基于当前 `packages/` 分层做最小、可验证、可公开维护的改动。**
