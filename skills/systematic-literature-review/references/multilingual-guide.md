# 多语言支持指南

本指南说明 systematic-literature-review 技能的多语言翻译与智能编译功能。

## 功能概述

支持将综述正文翻译为多种语言，自动修复 LaTeX 渲染错误，确保 PDF 和 Word 正确输出。

### 核心特性

- **用户主动指定**：在请求中明确语言需求
- **覆盖原文件**：翻译后覆盖 `{topic}_review.tex`，原文备份为 `.bak`
- **重试到成功**：智能修复编译，无理论上限（通过循环检测和超时保护）
- **引用不可变**：`.bib` 文件保持不变，所有 `\cite{key}` 完整保留
- **结构不可变**：LaTeX 命令、数学公式、图表标签不翻译

## 支持的语言

| 语言 | 代码 | 关键词 | LaTeX 处理 |
|------|------|--------|-----------|
| 英语 | en | 英语、英文、English、en | 无需特殊处理 |
| 中文 | zh | 中文、汉语、Chinese、zh | CTeX 宏包 |
| 日语 | ja | 日语、日文、Japanese、ja | `luatexja-preset` |
| 德语 | de | 德语、德文、German、de、Deutsch | `babel` + `ngerman` |
| 法语 | fr | 法语、法文、French、fr、Français | `babel` + `french` |
| 西班牙语 | es | 西班牙语、西班牙文、Spanish、es、Español | `babel` + `spanish` |

## 使用方法

### 基本用法

在综述请求中指定目标语言：

```
# 日语综述
请用 systematic-literature-review 做"AI for protein design"的日语综述，旗舰级。

# 德语综述
请用 systematic-literature-review 做"Transformer in NLP"的德语综述，标准级。

# 法语综述
请做"癌症免疫治疗"的法语综述，旗舰级，12000-14000 字。
```

### 工作流程

```
用户指定目标语言 → 写作完成原版 {topic}_review.tex
    ↓
[multi_language.py] 单一脚本处理：
  1. 语言检测与验证
  2. AI 翻译正文（保留引用和结构）
  3. 备份原文为 .bak，覆盖原 tex
  4. 智能修复编译循环
  5. 导出 PDF/Word
    ↓
成功 → 输出 PDF/Word
失败 → 输出 broken 文件 + 错误报告（可恢复 .bak）
```

## 错误处理

### 可修复错误

以下错误会自动修复或提示 AI 修复：

| 错误类型 | 说明 | 修复策略 |
|---------|------|---------|
| missing_package | 缺少宏包 | 自动添加 `\usepackage{...}` |
| undefined_command | 命令未定义 | 添加对应宏包或替换命令 |
| missing_font | 字体缺失 | 替换为系统可用字体 |
| encoding_error | 编码错误 | 添加编码支持 |
| syntax_error | 语法错误 | 修复括号匹配等 |
| file_not_found | 文件未找到 | 检查路径 |
| ctex_error | CTeX 错误 | 调整 CTeX 配置 |

### 不可修复错误

以下错误会立即停止并报告：

| 错误类型 | 说明 | 解决方案 |
|---------|------|---------|
| permission_denied | 文件权限错误 | 检查目录权限 |
| memory_exceeded | TeX 内存溢出 | 简化文档或增加内存限制 |

### 循环检测

系统记录修复历史，避免重复无效修复：
- 使用 `(错误类型, 错误详情前100字符)` 作为签名
- 检测到循环后停止并报告

### 超时保护

- 单次编译超时：5 分钟（可配置）
- 总计超时：30 分钟（可配置）
- 超时后可选择继续等待或恢复原文

## CLI 工具

### multi_language.py

核心脚本，处理所有多语言相关操作。

#### 翻译模式

生成翻译提示词（由 AI 执行实际翻译）：

```bash
python scripts/multi_language.py --tex-file review.tex --language ja
```

#### 编译模式

仅编译（跳过翻译）：

```bash
python scripts/multi_language.py \
  --tex-file review.tex \
  --bib-file refs.bib \
  --compile-only
```

编译成功后导出 Word：

```bash
python scripts/multi_language.py \
  --tex-file review.tex \
  --bib-file refs.bib \
  --compile-only \
  --export-word
```

#### 恢复模式

从备份恢复原文：

```bash
python scripts/multi_language.py --tex-file review.tex --restore
```

## AI 翻译提示词

翻译时使用的提示词模板（可自定义）：

```
你是一位学术翻译专家。请将以下综述正文翻译为{language}。

要求：
1. 保持学术语气、专业性和逻辑连贯性
2. 保留所有 \cite{key} 引用标记及其位置，绝对不可修改
3. 保留所有 LaTeX 结构命令（\section, \subsection, \begin{itemize}, \begin{enumerate} 等）
4. 保留所有数学公式（$...$, \[...\], \begin{equation} 等）
5. 保留图表标签和引用（\label{}, \ref{} 等）
6. 专业术语可保留原文或添加译注（如"Transformer（变换器）"）
7. 缩略词首次出现时展开（如"Artificial Intelligence (AI)"）

仅输出翻译后的 LaTeX 源码，不要包含任何解释性文字。
```

## 配置

在 `config.yaml` 中配置多语言支持：

```yaml
multilingual:
  enabled: true
  supported_languages: [...]
  max_compile_retries: 99
  compile_timeout: 300
  total_timeout: 1800
  translation_prompt_template: |
    ...
```

## 备份与恢复

### 备份策略

翻译前自动备份原文：
- 第一次备份：`{topic}_review.tex.bak`
- 后续备份：`{topic}_review.tex.bak.20260103_143000`（带时间戳）

### 恢复方法

```bash
# 方法 1：使用 CLI
python scripts/multi_language.py --tex-file review.tex --restore

# 方法 2：手动恢复
cp review.tex.bak review.tex
```

## 错误报告

编译失败时自动生成错误报告：

- 文件名：`{topic}_review_error_report.md`
- 内容：
  - 文件路径和时间戳
  - 错误类型和详情
  - 修复历史
  - 建议操作

## 故障排查

### 问题：翻译后编译失败

**可能原因**：
1. 翻译引入了 LaTeX 语法错误
2. 缺少目标语言的字体
3. 宏包冲突

**解决方案**：
1. 查看错误报告（`_error_report.md`）
2. 使用 `--restore` 恢复原文
3. 检查 TeX 发行版是否安装完整

### 问题：字体缺失

**解决方案**：

Ubuntu/Debian:
```bash
sudo apt-get install fonts-noto-cjk
```

macOS:
```bash
# 字体已预装，检查 TeX 发行版
```

Windows:
```bash
# 下载并安装 Noto CJK 字体
# https://www.google.com/get/noto/
```

### 问题：AI 翻译破坏了引用

**解决方案**：
1. 立即使用 `--restore` 恢复原文
2. 检查翻译提示词是否明确要求保留引用
3. 重新翻译，强调引用不可变

## 最佳实践

1. **测试先行**：先在小型文档上测试翻译和编译
2. **检查备份**：翻译前确认备份已创建
3. **验证引用**：编译后检查 PDF 中的引用是否正确
4. **人工审核**：AI 翻译后建议人工检查专业术语
5. **保留日志**：错误报告有助于问题诊断

## 限制

1. **混合语言文档**：不支持单个文档中多种语言混杂
2. **RTL 语言**：阿拉伯语等从右到左语言暂不支持
3. **特殊字体**：某些特殊字体可能需要手动安装
4. **复杂宏包**：使用复杂自定义宏包的文档可能需要额外调整

## 更新日志

- **v1.0.0** (2026-01-03)：初始版本，支持 en/zh/ja/de/fr/es 六种语言
