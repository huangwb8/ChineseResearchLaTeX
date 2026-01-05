# Word PDF 基准生成指南

## 概述

本指南说明如何从 Word 模板生成 PDF 基准，用于像素级对比验证。

**重要提示**: 必须使用 Word 打印 PDF，不能使用 QuickLook 预览！

---

## 方法 1: Microsoft Word (强烈推荐)

### 步骤

1. 打开 Microsoft Word
2. 打开模板文件: `projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.doc`
3. 选择 "文件" → "导出" → "创建 PDF"
4. 保存 PDF 到: `tests/v{timestamp}/baseline/word.pdf`

### 优点
- ✅ 最精确，完全符合 Word 渲染效果
- ✅ 像素级对比基准最可靠

### 缺点
- ❌ 需要 Microsoft Word 许可证

---

## 方法 2: LibreOffice (免费替代)

### 安装 LibreOffice

**macOS**:
```bash
brew install --cask libreoffice
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get install libreoffice
```

**Windows**:
- 从 https://www.libreoffice.org/ 下载安装

### 转换命令

```bash
# 创建输出目录
mkdir -p tests/v{timestamp}/baseline

# 转换 Word → PDF
soffice --headless --convert-to pdf \
  --outdir tests/v{timestamp}/baseline \
  "projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.doc"

# 将 PDF 转换为高分辨率 PNG（用于像素对比）
pdftoppm -png -r 150 -singlefile \
  tests/v{timestamp}/baseline/word.pdf \
  tests/v{timestamp}/baseline/word
```

### 优点
- ✅ 免费、跨平台、命令行自动化
- ✅ 渲染效果与 Word 接近

### 缺点
- ⚠️ 渲染效果可能与 Word 有细微差异（但远好于 QuickLook）

---

## 验证 PDF 质量

### 检查 PDF 信息

```bash
# 安装 pdfinfo (如果未安装)
# macOS: brew install poppler
# Linux: sudo apt-get install poppler-utils

pdfinfo tests/v{timestamp}/baseline/word.pdf
```

### 预期输出

```
Title:          2026年最新word模板-青年科学基金项目（C类）-正文
Author:
Creator:        Microsoft Word
Producer:       Microsoft Word
CreationDate:   ...
ModDate:        ...
Tagged:         no
Form:           none
Pages:          1
Encrypted:      no
Page size:      595 x 842 pts (A4)
Page rot:       0
File size:      XXXXX bytes
Optimized:      no
PDF version:    1.5
```

**关键检查点**:
- ✅ Page size: 595 x 842 pts (A4 纸标准)
- ✅ PDF version: ≥ 1.4
- ✅ 无加密 (Encrypted: no)

---

## 常见问题

### Q1: 为什么不能用 QuickLook 预览?

**A**: QuickLook 的渲染引擎与 Word 不同：
- 行距算法不同
- 字体渲染不同
- 断行位置不同

使用 QuickLook 基准会导致像素对比指标失真，即使样式配置正确也会显示对比失败。

### Q2: LibreOffice 转换的 PDF 可以用吗?

**A**: 可以，但需要注意：
- LibreOffice 的渲染效果与 Word 有 95% 以上的相似度
- 对于像素级对比，可能存在 5-10% 的像素差异
- 如果对像素对比要求不高（changed_ratio < 0.20 即可接受），LibreOffice 完全够用

### Q3: 没有安装 Microsoft Word 或 LibreOffice 怎么办?

**A**: 有以下选择：
1. 安装 LibreOffice（免费）
2. 使用在线转换工具（仅适用于非敏感内容）
3. 跳过像素对比验证，仅进行样式参数检查

---

## 绝对禁止的做法

❌ **错误**: 使用 `qlmanage -t` 生成 QuickLook 缩略图
```bash
# 不要这样做！
qlmanage -t -s 1000 -o . word_template.doc
```

❌ **错误**: 使用 macOS 预览应用打开 .doc 文件截图

❌ **错误**: 使用任何非 Word/LibreOffice 的渲染工具

---

## 下一步

生成基准 PDF 后，可以：

1. 运行验证脚本: `bash scripts/validate.sh`
2. 进行像素对比（如果基准 PDF 存在）
3. 填写测试报告

---

**参考**:
- [SKILL.md Q1.1](../SKILL.md#q11-如何获取-word-打印-pdf最佳实践)
- [测试报告示例](../tests/v202601052118/TEST_REPORT.md)
