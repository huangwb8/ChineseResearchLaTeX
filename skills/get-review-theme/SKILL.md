---
name: get-review-theme
description: 当用户明确要求"从文件/图片/网页/描述中提取综述主题"或"生成主题+关键词+核心问题结构化输出"时使用。支持文件（PDF/Word/Markdown/Tex）、文件夹、图片、自然语言描述、网页 URL 等多种输入源，自动识别输入类型并提取内容，生成可直接用于 systematic-literature-review 及其他文献综述技能的结构化输出。

metadata:
  author: Bensz Conan
  short-description: 多源输入的结构化综述主题提取工具
  keywords:
    - get-review-theme
    - 主题提取
    - 综述主题
    - review topic
    - 关键词提取
    - 核心问题识别
    - 文献调研准备
    - systematic literature review
    - 输入分析
    - PDF 分析
    - 图片理解
    - 网页解析
    - 内容理解
    - 学术主题识别
---

# Get Review Theme

## 与 bensz-collect-bugs 的协作约定

- 当用户环境中出现因本 skill 设计缺陷导致的 bug 时，优先使用 `bensz-collect-bugs` 按规范记录到 `~/.bensz-skills/bugs/`，严禁直接修改用户本地 Claude Code / Codex 中已安装的 skill 源码。
- 若 AI 仍可通过 workaround 继续完成用户任务，应先记录 bug，再继续完成当前任务。
- 当用户明确要求“report bensz skills bugs”等公开上报动作时，调用本地 `gh` 与 `bensz-collect-bugs`，仅上传新增 bug 到 `huangwb8/bensz-bugs`；不要 pull / clone 整个 bug 仓库。

## 定位

- 从文件、图片、网页、文件夹或自然语言描述中提取结构化综述主题。
- 输出直接服务 `systematic-literature-review` 或其他文献综述工作流。
- 最高原则：主题要可操作、关键词要能检索、核心问题要具体。

## 输入

必需：

- `{输入源}`：文件路径、URL、文件夹路径、图片路径，或直接文本描述

可选：

- `{输出格式}`：`text` / `yaml` / `json`，默认 `text`

## 输出

始终包含三项：

- `主题`
- `关键词`
- `核心问题`

格式由用户选择：

- `text`
- `yaml`
- `json`

## 工作流

### 1. 识别输入类型

- 自然语言描述
- 图片
- URL
- 文本文件
- PDF
- Word
- 文件夹

### 2. 提取内容

- 自然语言：直接使用
- 图片：依赖 LLM 原生视觉能力
- URL：优先网页读取工具，失败则请用户提供正文
- 文本 / PDF / Word：直接读取
- 文件夹：递归扫描并合并 `.md/.txt/.pdf` 等核心材料

原则：

- 优先用宿主原生能力和现有标准工具
- 工具不可用时优雅降级，不额外引入脚本依赖

### 3. 语义提取

围绕以下任务输出：

- 用一句话概括主题
- 提取 5-10 个英文标准术语
- 提取 2-5 个具体研究问题或挑战

### 4. 格式化

- `text`：适合直接复制给下游 skill
- `yaml` / `json`：适合结构化衔接

## 质量要求

- 主题要包含研究对象与核心问题或方法
- 关键词优先用标准检索术语
- 核心问题必须具体，避免“意义重大/挑战很多”这种空话

## 错误处理

- 文件不存在：提示用户改路径或直接粘贴内容
- 格式不支持：提示转换
- 内容提取失败：让用户手动提供文本
- URL 解析失败：让用户复制网页正文或提供 PDF
- 图片语义不清：请用户补一句描述

## 与下游技能的关系

- `topic` 可直接喂给 `systematic-literature-review`
- `keywords` 可补充检索策略
- `core_questions` 可作为综述边界和纳排参考
