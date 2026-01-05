# Bug报告: make_latex_model 技能

## 问题概述
- **测试时间**: 2026-01-05
- **测试实例**: v202601052118
- **测试环境**: macOS Darwin 25.2.0, arm64
- **问题总数**: 2
- **严重程度分布**: P2 (1个), P3 (1个)

## 问题清单

### 问题 #1: validate.sh 行距检查逻辑错误
**严重程度**: Medium
**优先级**: P2
**状态**: Open
**发现来源**: 测试实例 v202601052118 验证脚本测试

**问题描述**:
验证脚本 `scripts/validate.sh` 第 118 行的行距检查逻辑与实际配置不符。

- **实际行为**: 脚本检查 `\\renewcommand{\\baselinestretch}{1.0}`，导致检查失败
- **期望行为**: 应检查 `\\renewcommand{\\baselinestretch}{1.5}`（符合 Word 2026 模板标准）
- **影响范围**: 验证报告准确性，用户可能误认为行距配置错误

**根因分析**:
- **问题根源**: 技能 v1.2.0 中将行距从 1.5 改为 1.0，但 v1.3.0 又改回 1.5（符合 Word 模板），验证脚本未同步更新
- **相关文件**: `scripts/validate.sh` (第 118 行)
- **为什么出现**: 验证脚本的硬编码期望值与配置文件不同步

**实际配置** (正确):
```latex
% extraTex/@config.tex 第 90 行
\renewcommand{\baselinestretch}{1.5}
```

**验证脚本** (错误):
```bash
# scripts/validate.sh 第 118 行
if grep -q "\\renewcommand{\\baselinestretch}{1.0}" "$CONFIG"; then
  pass "行距设置: baselinestretch{1.0} (符合 v1.2.0 标准)"
```

**修复建议**:
- **推荐方案**: 更新 `validate.sh` 第 118-125 行，改为检查 1.5 倍行距
- **替代方案**: 从配置文件动态读取期望值
- **预期效果**: 验证脚本正确识别 1.5 倍行距配置

**验证方法**:
- 测试用例: 运行 `bash scripts/validate.sh`
- 预期结果: 行距检查显示 ✅ 通过
- 验证点: "通过: 7" 应变为 "通过: 8"，"失败: 1" 应变为 "失败: 0"

---

### 问题 #2: 缺少 Word PDF 基准生成指南
**严重程度**: Low
**优先级**: P3
**状态**: Open
**发现来源**: 测试实例 v202601052118 像素对比测试

**问题描述**:
文档中说明了必须使用 Word 打印 PDF 作为基准，但缺少具体的操作指南。

- **实际行为**: 用户需要手动探索如何生成 Word PDF 基准
- **期望行为**: 提供清晰的 Step-by-Step 操作指南
- **影响范围**: 用户体验，像素对比验证的执行便利性

**根因分析**:
- **问题根源**: SKILL.md 中有详细说明（Q1.1），但缺少独立可执行的操作指南
- **相关文件**: `SKILL.md` (第 318-368 行)
- **为什么出现**: 文档结构设计问题，操作指南嵌入在 FAQ 中

**当前说明** (SKILL.md Q1.1):
```markdown
### Q1.1: 如何获取 Word 打印 PDF（最佳实践）？

**方法 1：Microsoft Word（强烈推荐）**
```bash
# 1. 在 Microsoft Word 中打开模板文件
# 2. 选择"文件" → "导出" → "创建 PDF"
# 3. 保存为 artifacts/baseline/word.pdf
```

**方法 2：LibreOffice（免费替代）**
```bash
soffice --headless --convert-to pdf \
  --outdir artifacts/baseline \
  "projects/NSFC_Young/template/2026年最新word模板-*.doc*"
```
```

**修复建议**:
- **推荐方案**: 创建独立的 `docs/BASELINE_GUIDE.md` 操作指南
- **替代方案**: 在 `scripts/validate.sh` 中添加生成基准的提示信息
- **预期效果**: 用户可以轻松找到并执行基准生成操作

**验证方法**:
- 测试用例: 新用户按照指南生成 Word PDF 基准
- 预期结果: 能够成功生成基准 PDF，无需额外帮助
- 验证点: 基准 PDF 文件存在于 `baseline/word.pdf`

---

## 附录

### 测试环境信息
```yaml
操作系统: macOS Darwin 25.2.0
架构: arm64 (Apple Silicon)
Shell: bash
XeLaTeX: TeX Live 2024
Python: 3.x
LibreOffice: 未安装
```

### 相关文档
- 测试报告: `tests/v202601052118/TEST_REPORT.md`
- 测试计划: `tests/v202601052118/TEST_PLAN.md`
- 技能文档: `SKILL.md`
- 配置文件: `config.yaml`

### 优先级说明
- **P2 (Medium)**: 中等问题，验证功能受限，需在3天内修复
- **P3 (Low)**: 轻微问题，用户体验优化，可在1周内修复
