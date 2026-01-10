# Get Review Theme — 用户使用指南

本 README 面向**使用者**：教你如何触发并正确使用 `get-review-theme` skill。

如果你在编辑/维护该 skill：执行指令与强制规范在 `get-review-theme/SKILL.md`。

## 快速开始

### 最简单的用法

```
用户：帮我从这句话提取综述主题："我想了解深度学习在医学影像中的应用，特别是癌症诊断"
```

**输出**：
```
主题：深度学习在医学影像癌症诊断中的应用
关键词：deep learning、medical imaging、cancer diagnosis、computer-aided detection、convolutional neural network
核心问题：小样本学习、模型可解释性、多模态数据融合
```

## 功能概述

`get-review-theme` 能够从各种输入源中提取结构化的综述主题，包括：

| 输入类型 | 示例 | 说明 |
|---------|------|------|
| **自然语言描述** | "我想了解..." | 最简单直接 |
| **图片** | `/path/to/figure.png` | 使用 LLM 视觉能力分析 |
| **文本文件** | `.md`、`.txt`、`.tex` | 自动读取并分析 |
| **PDF** | `/path/to/paper.pdf` | 提取论文主题 |
| **网页 URL** | `https://example.com` | 解析网页内容 |
| **文件夹** | `/path/to/folder` | 递归扫描并合并分析 |

**输出格式**：
- **主题**：一句话概括，适合作为综述标题
- **关键词**：英文标准术语，适合文献检索
- **核心问题**：具体挑战，反映研究热点

## 提示词示例

### 示例 1：从自然语言提取（最简单）

```
用户：帮我提取综述主题：Transformer 在自然语言处理中的应用，特别是机器翻译和文本分类
```

### 示例 2：从文件提取

```
用户：从这个文件提取综述主题：/path/to/research-notes.md
```

### 示例 3：从图片提取

```
用户：分析这张研究框架图并提取综述主题：/path/to/framework.png
```

### 示例 4：从 PDF 提取

```
用户：分析这篇论文并提取综述主题：/path/to/paper.pdf
```

### 示例 5：从网页 URL 提取

```
用户：从这个研究项目页面提取综述主题：https://example.com/project
```

### 示例 6：从文件夹提取

```
用户：从这个研究文件夹提取综述主题：/path/to/research-docs
```

### 示例 7：指定输出格式（YAML）

```
用户：从 /path/to/document.pdf 提取主题，输出 YAML 格式
```

### 示例 8：指定输出格式（JSON）

```
用户：分析这个图片并输出 JSON 格式的主题：/path/to/concept-map.png
```

### 示例 9：结合 systematic-literature-review 使用

```
用户：分析 /path/to/proposal.txt 提取主题，然后用 systematic-literature-review 做标准级综述
```

### 示例 10：批量处理多个输入

```
用户：分别从这三个文件提取主题：file1.md、file2.pdf、image.png，然后我选择最合适的做综述
```

## 输出格式说明

### 格式 1：纯文本（默认）

```
主题：深度学习在医学影像癌症诊断中的应用
关键词：deep learning、medical imaging、cancer diagnosis、computer-aided detection、convolutional neural network
核心问题：小样本学习、模型可解释性、多模态数据融合
```

### 格式 2：YAML

```yaml
topic: "深度学习在医学影像癌症诊断中的应用"
keywords:
  - "deep learning"
  - "medical imaging"
  - "cancer diagnosis"
  - "computer-aided detection"
  - "convolutional neural network"
core_questions:
  - "小样本学习"
  - "模型可解释性"
  - "多模态数据融合"
```

### 格式 3：JSON

```json
{
  "topic": "深度学习在医学影像癌症诊断中的应用",
  "keywords": ["deep learning", "medical imaging", "cancer diagnosis", "computer-aided detection", "convolutional neural network"],
  "core_questions": ["小样本学习", "模型可解释性", "多模态数据融合"]
}
```

## 与 systematic-literature-review 的集成

### 场景 1：单步传递主题

```
用户：从 /path/to/grant-proposal.txt 提取主题，然后用 systematic-literature-review 做综述

AI 执行流程：
1. 调用 get-review-theme 分析文本
2. 获取结构化主题
3. 提取"主题"字段
4. 传递给 systematic-literature-review
5. 执行文献综述流程
```

### 场景 2：完整参数传递

```
用户：从 research-plan.md 提取主题（含关键词和核心问题），然后用 systematic-literature-review 做旗舰级综述

AI 执行流程：
1. 调用 get-review-theme，请求 JSON 格式输出
2. 解析 JSON，获取 topic、keywords、core_questions
3. 将 topic 作为主题
4. 将 keywords 补充到检索策略
5. 将 core_questions 作为研究范围参考
6. 传递给 systematic-literature-review
```

## 支持的文件类型

| 类别 | 扩展名 | 说明 |
|------|--------|------|
| **文本文件** | `.md`、`.txt`、`.tex`、`.rst` | 直接读取 |
| **文档文件** | `.pdf`、`.doc`、`.docx` | 提取文本内容 |
| **图片文件** | `.png`、`.jpg`、`.jpeg`、`.gif`、`.webp` | LLM 视觉理解 |

## 常见问题

### Q1：提取的主题不准确怎么办？

**A**：提供更多上下文或更具体的描述：

```
用户：从这句话提取主题："CRISPR"

AI 输出可能不准确

改进方式：
用户：从这句话提取主题："CRISPR 基因编辑技术在遗传病治疗中的应用和安全性问题"
```

### Q2：如何提高关键词质量？

**A**：在输入中明确研究领域和核心问题：

```
用户：从这段描述提取主题："我们关注计算机视觉中的目标检测任务，特别是小目标检测、实时检测、以及在自动驾驶场景中的应用"
```

### Q3：图片内容无法理解怎么办？

**A**：提供图片的文字描述或使用文本版本：

```
用户：这张图展示了深度学习模型架构，包括 CNN、RNN 和注意力机制模块，提取主题

或

用户：从 architecture-diagram.png 提取主题。图片内容：一个多层神经网络架构图，包含卷积层、池化层、全连接层
```

### Q4：文件夹内容太多怎么办？

**A**：指定关键文件或子文件夹：

```
用户：从 /path/to/research-folder/papers/ 提取主题

或

用户：从 research-folder 中的 intro.md 和 methods.md 提取主题
```

### Q5：如何验证主题质量？

**A**：检查以下标准：
- [ ] 主题表述简洁明确，适合作为综述标题
- [ ] 关键词是英文标准术语，可以用于文献检索
- [ ] 核心问题具体而非泛泛，反映真实挑战

## ❌ 不推荐的写法

| 不推荐写法 | 问题 | 推荐写法 |
|-----------|------|---------|
| "提取主题" | 缺少输入源 | "从这句话提取主题：..." |
| "分析这个" | 缺少具体内容 | "分析 /path/to/file.md 并提取主题" |
| "给我几个关键词" | 目标不明确 | "从...提取综述主题，包含关键词" |
| "这是什么主题？" | 过于宽泛 | "从以下内容提取结构化综述主题：..." |

## 最佳实践

### 1. 明确输入源
- ✅ 提供文件路径、URL 或具体描述
- ❌ 仅说"分析这个"

### 2. 提供足够上下文
- ✅ 描述研究领域、核心问题、应用场景
- ❌ 仅提供单个术语

### 3. 选择合适的输出格式
- ✅ 默认纯文本（可读性好）
- ✅ 程序调用用 YAML/JSON
- ❌ 不指定格式却期望结构化输出

### 4. 结合下游技能
- ✅ 提取主题后直接用于文献综述
- ✅ 将关键词和核心问题传递给下游流程
- ❌ 重复描述相同内容

## 更新记录

- **2026-01-04**：初始版本，支持 7 种输入类型和 3 种输出格式
