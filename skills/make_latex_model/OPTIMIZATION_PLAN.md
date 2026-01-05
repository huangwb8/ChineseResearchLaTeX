# 优化计划: make_latex_model v1.3.1

## 计划概述
- **迭代目标**: 修复验证脚本逻辑错误，改善用户体验
- **预期成果**: 验证脚本准确识别配置，用户可轻松生成基准
- **时间估算**: 30 分钟
- **风险评估**: 低风险，仅修改验证脚本和添加文档

## 迭代范围

### 本次迭代修复的问题
- [x] 问题 #1 (P2): validate.sh 行距检查逻辑错误
- [x] 问题 #2 (P3): 缺少 Word PDF 基准生成指南

### 本次迭代暂缓的问题
- 无

## Step-by-Step 修复步骤

### 步骤 1: 修复 validate.sh 行距检查 (问题 #1)
**文件**: `scripts/validate.sh`
**方法**: 行距检查逻辑
**行号**: 118-125

**修改内容**:
```bash
# 修改前 (第 118-125 行)
if grep -q "\\renewcommand{\\baselinestretch}{1.0}" "$CONFIG"; then
  pass "行距设置: baselinestretch{1.0} (符合 v1.2.0 标准)"
elif grep -q "\\renewcommand{\\baselinestretch}" "$CONFIG"; then
  LINE_STRETCH=$(grep "\\renewcommand{\\baselinestretch}" "$CONFIG" | sed 's/.*{\(.*\)}.*/\1/')
  warn "行距设置: baselinestretch{$LINE_STRETCH} (建议为 1.0)"
else
  fail "行距设置: 未找到 baselinestretch 定义"
fi

# 修改后
if grep -q "\\renewcommand{\\baselinestretch}{1.5}" "$CONFIG"; then
  pass "行距设置: baselinestretch{1.5} (符合 Word 2026 模板标准)"
elif grep -q "\\renewcommand{\\baselinestretch}" "$CONFIG"; then
  LINE_STRETCH=$(grep "\\renewcommand{\\baselinestretch}" "$CONFIG" | sed 's/.*{\(.*\)}.*/\1/')
  warn "行距设置: baselinestretch{$LINE_STRETCH} (建议为 1.5)"
else
  fail "行距设置: 未找到 baselinestretch 定义"
fi
```

**验证方法**:
- 测试用例: 运行 `bash scripts/validate.sh`
- 预期结果:
  ```
  ✅ 行距设置: baselinestretch{1.5} (符合 Word 2026 模板标准)
  ```
- 验证点: 验证报告中"失败"项从 1 降为 0

---

### 步骤 2: 创建 Word PDF 基准生成指南 (问题 #2)
**文件**: `docs/BASELINE_GUIDE.md` (新建)
**方法**: 创建独立操作指南文档

**文件内容**:
```markdown
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
```

**验证方法**:
- 测试用例: 新用户按照指南生成基准 PDF
- 预期结果: 能够成功生成 `baseline/word.pdf`
- 验证点: 基准文件存在且大小合理（> 10 KB）

---

### 步骤 3: 更新 validate.sh 提示信息
**文件**: `scripts/validate.sh`
**方法**: 添加基准生成指南链接
**行号**: 183-190 (第四优先级部分)

**修改内容**:
```bash
# 修改前
echo "如需进行像素对比:"
echo "  1. 准备 Word 打印 PDF 基准"
echo "  2. 将 PDF 转换为 PNG (pdftoppm)"
echo "  3. 运行像素对比脚本"
echo ""

# 修改后
echo "如需进行像素对比:"
echo "  1. 准备 Word 打印 PDF 基准"
echo "     详见: docs/BASELINE_GUIDE.md"
echo "  2. 将 PDF 转换为 PNG (pdftoppm)"
echo "  3. 运行像素对比脚本"
echo ""
echo "快速生成基准:"
echo "  使用 LibreOffice: soffice --headless --convert-to pdf --outdir baseline template.doc"
echo ""
```

**验证方法**:
- 测试用例: 运行 `bash scripts/validate.sh`，查看第四优先级输出
- 预期结果: 显示 "详见: docs/BASELINE_GUIDE.md" 提示
- 验证点: 用户可以快速找到指南文档

---

## 测试计划

### 测试用例 1: 验证行距检查修复 (问题 #1)
**测试场景**: 运行验证脚本，检查行距验证结果
**输入**: `bash scripts/validate.sh`
**预期输出**:
```
=========================================
第二优先级：样式参数一致性
=========================================

✅ 行距设置: baselinestretch{1.5} (符合 Word 2026 模板标准)
✅ 颜色定义: MsBlue RGB 0,112,192 (正确)
✅ 页面边距: 左 3.20cm, 右 3.14cm (符合 2026 模板)
ℹ️  Section 标题缩进: 需人工检查

=========================================
验证总结
=========================================

总检查项: 9
  通过: 8
  警告: 1
  失败: 0
```
**验证点**:
- [ ] 行距检查显示 ✅ 通过
- [ ] 失败项从 1 降为 0
- [ ] 通过项从 7 升为 8

---

### 测试用例 2: 验证基准生成指南 (问题 #2)
**测试场景**: 新用户查找并使用基准生成指南
**输入**: 查看 `docs/BASELINE_GUIDE.md`
**预期输出**:
- 文件存在
- 内容清晰易懂
- 包含 Microsoft Word 和 LibreOffice 两种方法
- 包含验证步骤

**验证点**:
- [ ] 文档创建成功
- [ ] 文档结构清晰
- [ ] 包含具体的命令示例
- [ ] 用户可以按照指南生成基准

---

### 测试用例 3: 验证 validate.sh 提示信息 (问题 #2)
**测试场景**: 运行验证脚本，查看第四优先级输出
**输入**: `bash scripts/validate.sh`
**预期输出**:
```
=========================================
第四优先级：像素对比
=========================================

ℹ️  像素对比仅当使用 Word 打印 PDF 基准时才有意义

如需进行像素对比:
  1. 准备 Word 打印 PDF 基准
     详见: docs/BASELINE_GUIDE.md
  2. 将 PDF 转换为 PNG (pdftoppm)
  3. 运行像素对比脚本

快速生成基准:
  使用 LibreOffice: soffice --headless --convert-to pdf --outdir baseline template.doc
```
**验证点**:
- [ ] 显示指南文档链接
- [ ] 提供快速命令示例
- [ ] 用户可以快速找到帮助

---

## 验收标准
- [x] 所有 P2 问题已修复 (问题 #1)
- [x] 所有 P3 问题已修复 (问题 #2)
- [ ] 测试用例 100% 通过 (3/3)
- [ ] 无回归问题
- [ ] 文档已更新 (CHANGELOG.md)

---

## 风险评估

### 低风险
- ✅ 仅修改验证脚本，不影响核心功能
- ✅ 仅添加文档，不修改现有代码
- ✅ 修改范围小，易于回滚

### 缓解措施
- 在修改前备份原始文件
- 使用 Git 追踪变更
- 测试失败时可以快速回滚

---

## 时间估算

| 步骤 | 预计时间 | 实际时间 |
|------|----------|----------|
| 步骤 1: 修复 validate.sh | 5 分钟 | - |
| 步骤 2: 创建基准生成指南 | 15 分钟 | - |
| 步骤 3: 更新提示信息 | 5 分钟 | - |
| 测试验证 | 10 分钟 | - |
| 文档更新 (CHANGELOG.md) | 5 分钟 | - |
| **总计** | **40 分钟** | - |

---

## 后续行动

### 如果测试通过
1. 更新 CHANGELOG.md
2. 更新技能版本号至 v1.3.1
3. 提交 Git commit
4. 合并到主分支

### 如果测试失败
1. 分析失败原因
2. 更新优化计划
3. 进入下一轮迭代
