# make_latex_model 能力评估执行指南

## 快速开始

```bash
# 进入测试目录
cd skills/make_latex_model/tests/v202601052142

# 执行测试
./run_test.sh
```

## 详细步骤

### 步骤 1：环境准备

测试脚本会自动检查以下依赖：

- **必需**：
  - `python3`：运行验证脚本
  - `xelatex`：LaTeX 编译引擎
  - `bibtex`：参考文献处理

- **可选**：
  - `soffice`（LibreOffice）：生成 Word PDF 基准
  - `pdftoppm`：像素对比工具

安装可选依赖：

```bash
# macOS
brew install --cask libreoffice poppler

# Linux (Ubuntu/Debian)
sudo apt-get install libreoffice poppler-utils
```

### 步骤 2：准备 Word PDF 基准（推荐）

虽然测试可以在没有 Word PDF 基准的情况下运行，但强烈建议准备基准文件以获得完整的验证结果。

#### 方法 A：使用 LibreOffice（推荐）

```bash
# 进入测试目录
cd skills/make_latex_model/tests/v202601052142

# 转换 Word 为 PDF
soffice --headless --convert-to pdf \
  --outdir expected \
  input/word_template/2026年最新word模板-青年科学基金项目（C类）-正文.doc

# 重命名
mv expected/2026年最新word模板-青年科学基金项目（C类）-正文.pdf \
   expected/word_baseline.pdf
```

#### 方法 B：使用 Microsoft Word

1. 在 Microsoft Word 中打开模板文件
2. 选择"文件" → "导出" → "创建 PDF"
3. 保存为 `expected/word_baseline.pdf`

### 步骤 3：执行测试

```bash
./run_test.sh
```

测试脚本会自动执行以下步骤：

1. ✓ 检查依赖
2. ✓ 准备测试环境
3. ✓ 生成 Word PDF 基准（如果需要）
4. ✓ 编译 LaTeX
5. ✓ 运行验证
6. ✓ 生成测试报告

### 步骤 4：查看结果

#### 查看测试报告

```bash
cat REPORT.md
```

#### 查看 JSON 格式的验证结果

```bash
cat validation/style_check.json | python3 -m json.tool
```

#### 对比 PDF

```bash
# macOS
open output/artifacts/main.pdf

# Linux
xdg-open output/artifacts/main.pdf
```

如果生成了 Word PDF 基准，可以并排对比：

```bash
# macOS（使用预览应用）
open -a Preview output/artifacts/main.pdf expected/word_baseline.pdf

# 或使用专业 PDF 对比工具
```

## 测试场景

### 场景 A：快速验证（5分钟）

仅验证编译是否成功，不进行深度检查。

```bash
cd output/latex_project
xelatex -interaction=nonstopmode main.tex
```

### 场景 B：标准测试（15分钟）

运行完整的测试流程，包括所有自动化验证。

```bash
./run_test.sh
```

### 场景 C：深度分析（30分钟）

在标准测试的基础上，添加人工验证和像素对比。

1. 运行标准测试
2. 人工对比 PDF
3. 检查关键样式参数
4. 分析代码变更

## 验证清单

### 自动验证（由脚本执行）

- [ ] 编译无错误
- [ ] PDF 生成成功
- [ ] 样式参数检查（页面、字体、颜色、行距、标题）
- [ ] JSON 报告生成

### 人工验证（推荐）

- [ ] 视觉对比 PDF 整体布局
- [ ] 检查每行字数是否接近
- [ ] 检查换行位置是否对齐
- [ ] 检查关键区域（标题、列表）的格式

### 高级验证（可选）

- [ ] 像素级对比（需要 Word PDF 基准）
- [ ] 跨平台测试（在 Mac/Windows/Linux 上编译）
- [ ] 性能基准测试（编译时间、PDF 大小）

## 测试结果解读

### 评分标准

测试结果分为四个优先级，权重递减：

1. **第一优先级（40%）**：编译验证
   - 必须全部通过

2. **第二优先级（30%）**：样式参数验证
   - 推荐通过 ≥ 80%

3. **第三优先级（20%）**：视觉相似度
   - 优秀 ≥ 70%

4. **第四优先级（10%）**：像素对比
   - 可选，仅供参考

### 通过/失败判定

- ✅ **通过**：总分 ≥ 80%，且第一优先级全部通过
- ⚠️ **部分通过**：总分 ≥ 60%，但未达到优秀标准
- ❌ **失败**：总分 < 60%，或第一优先级有失败项

### 常见问题

#### Q1: 编译失败怎么办？

检查：
1. 字体是否正确安装（楷体、Times New Roman）
2. 宏包是否完整
3. 文件路径是否正确

查看详细日志：

```bash
cat output/latex_project/main.log
```

#### Q2: 样式参数检查失败？

可能原因：
1. `@config.tex` 中缺少相关定义
2. 参数值与 Word 模板不一致
3. 正则表达式匹配失败

解决方法：
1. 手动检查 `@config.tex`
2. 对比 Word 模板的样式设置
3. 调整参数值

#### Q3: 像素对比指标很差？

这是正常现象，原因：
1. 基准可能来自 QuickLook（而非 Word 打印 PDF）
2. 行距调整会导致换行位置变化
3. 字体渲染差异不可避免

应对方法：
1. 优先使用 Word 打印 PDF 作为基准
2. 以样式参数正确性为主
3. 像素对比仅作为辅助参考

## 扩展测试

### 测试其他项目

修改 `config.yaml` 中的 `source.project`：

```yaml
source:
  project: NSFC_General  # 或其他项目
```

### 测试不同优化级别

修改 `config.yaml` 中的 `optimization.level`：

```yaml
optimization:
  level: thorough  # minimal | moderate | thorough
```

### 自定义验证标准

修改 `config.yaml` 中的 `validation.acceptance_criteria`：

```yaml
validation:
  acceptance_criteria:
    min_priority_1_pass: 1.0
    min_priority_2_pass: 0.90  # 提高标准
    min_priority_3_pass: 0.80
```

## 测试报告模板

测试完成后，可以基于以下模板撰写详细报告：

```markdown
# make_latex_model 测试报告

## 测试概述

- **测试ID**: v202601052142
- **测试日期**: YYYY-MM-DD
- **测试人员**: [姓名]
- **测试环境**: [操作系统、软件版本]

## 测试执行

### 执行时间
开始时间: ...
结束时间: ...
总耗时: ...

### 执行步骤
1. ...
2. ...

### 遇到的问题
- [问题描述]
  - 原因：...
  - 解决：...

## 测试结果

### 自动验证结果
- 编译: ✓/✗
- 样式参数: X%
- 视觉相似度: X%
- 像素对比: X%

**综合评分**: X%

### 人工验证结果
- 整体布局: ✓/✗
- 标题格式: ✓/✗
- 每行字数: ✓/✗
- 换行位置: ✓/✗

## 分析总结

### 成功经验
1. ...
2. ...

### 失败原因
1. ...
2. ...

### 改进建议
1. ...
2. ...

## 附录

### 编译日志
[粘贴编译日志]

### 样式检查结果
[粘贴 JSON 结果]

### 对比截图
[插入截图]
```

## 联系与反馈

如有问题或建议，请通过以下方式反馈：

- GitHub Issues: [项目地址]/issues
- 项目文档: [CLAUDE.md](../../../../CLAUDE.md)
- 技能定义: [SKILL.md](../../SKILL.md)
