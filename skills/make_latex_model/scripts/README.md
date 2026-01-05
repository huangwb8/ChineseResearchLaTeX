# make_latex_model 辅助工具集

本目录包含 `make_latex_model` 技能的辅助工具，包括样式分析、标题对比、自动化验证和性能基准测试。

## 工具清单

### 1. analyze_pdf.py - PDF 样式分析工具

**功能**: 从 PDF（Word 导出的基准 PDF）中自动提取关键样式参数

**使用方法**:
```bash
# 安装依赖（首次使用）
pip install PyMuPDF

# 分析 Word PDF 基准
python3 scripts/analyze_pdf.py projects/NSFC_Young/template/word_baseline.pdf
```

**输出内容**:
- 📐 **页面布局**: 页面尺寸、边距（左/右/上/下，单位：cm）
- 🔤 **字体统计**: 字体名称、使用频率、字号列表、颜色（RGB）
- 📏 **行距分析**: 平均行距（pt）
- 💾 **详细分析结果**: 自动保存为 `*_analysis.json`

**使用场景**:
- Word 模板更新时，自动提取新的样式参数
- 对比不同年份模板的样式差异
- 验证 LaTeX 样式配置是否正确

**依赖**: `PyMuPDF` (fitz)

---

### 2. validate.sh - 自动化验证脚本

**功能**: 自动检查技能状态和项目配置

**使用方法**:
```bash
cd skills/make_latex_model
./scripts/validate.sh
```

**检查项**:
- ✅ 第一优先级: 基础编译检查 (项目目录、配置文件、编译状态、版本号一致性)
- ✅ 第二优先级: 样式参数一致性 (行距、颜色、边距、标题格式、**标题文字一致性**)
- ℹ️ 第三优先级: 视觉相似度 (需人工验证)
- ℹ️ 第四优先级: 像素对比 (需 Word 打印 PDF 基准)

**输出示例**:
```
=========================================
  make_latex_model 验证报告
=========================================

第一优先级：基础编译检查
✅ 项目目录存在
✅ 配置文件存在: @config.tex
✅ 编译成功: main.pdf 存在
✅ 版本号一致: v1.4.0

第二优先级：样式参数一致性
✅ 颜色定义: MsBlue RGB 0,112,192 (正确)
✅ 页面边距: 左 3.20cm, 右 3.14cm (符合 2026 模板)
✅ 标题文字完全匹配 (14 个)

总检查项: 10
  通过: 8
  警告: 2
  失败: 0
```

---

### 3. benchmark.sh - 性能基准测试

**功能**: 测量 LaTeX 编译性能

**使用方法**:
```bash
cd skills/make_latex_model
./scripts/benchmark.sh
```

**输出**:
- ⏱️ 平均编译时间（秒）
- 📄 PDF 文件大小（MB）
- 📊 JSON 格式性能报告

**输出示例**:
```json
{
  "test_info": {
    "test_time": "2026-01-05T13:14:12Z",
    "platform": "Darwin 25.2.0",
    "machine": "arm64"
  },
  "compilation": {
    "times": 3,
    "total_time_ms": 2372,
    "average_time_ms": 790,
    "average_time_sec": 0.79
  },
  "pdf": {
    "size_bytes": 1164515,
    "size_mb": 1.11
  }
}
```

---

### 4. extract_headings.py - 标题文字提取工具

**功能**: 从 Word 或 LaTeX 文件中提取标题文字结构

**使用方法**:
```bash
# 从 LaTeX 文件提取
python3 scripts/extract_headings.py latex --file projects/NSFC_Young/main.tex

# 从 Word 文档提取
python3 scripts/extract_headings.py word --file projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.docx

# 输出为 JSON
python3 scripts/extract_headings.py latex --file main.tex --format json --output headings.json
```

**输出示例**:
```
# 标题文字提取结果
# 源文件: main.tex

section_1: （一）立项依据与研究内容
subsection_1_1: 1. 项目的立项依据
subsection_1_2: 2. 项目的研究内容、研究目标，以及拟解决的关键科学问题
...
```

---

### 5. compare_headings.py - 标题文字对比工具

**功能**: 对比 Word 模板和 LaTeX 文件的标题文字差异

**使用方法**:
```bash
# 对比两个文件（输出文本报告）
python3 scripts/compare_headings.py word.docx main.tex

# 生成 HTML 可视化报告
python3 scripts/compare_headings.py word.docx main.tex --report heading_report.html

# 生成 Markdown 报告
python3 scripts/compare_headings.py word.docx main.tex --report heading_report.md
```

**输出示例**:
```
============================================================
  标题文字对比报告
============================================================

总标题数: 14
✅ 完全匹配: 12
⚠️  有差异: 2
❌ 仅在一方: 0

# 完全匹配的标题
✅ section_1: （一）立项依据与研究内容
✅ subsection_1_1: 1. 项目的立项依据
...

# 有差异的标题
⚠️  subsection_1_3:
   Word:  3. 拟采取的研究方案及可行性分析
   LaTeX: 3. 拟采取的研究方案及可行性
```

**HTML 报告特性**:
- 🎨 美观的可视化界面
- 📊 统计卡片（匹配/差异/仅在一方）
- 🎯 颜色编码（绿色=匹配，黄色=差异，红色=仅在一方）
- 📱 响应式设计

---

## 工作流集成

### 标准优化流程

1. **修改样式配置**
   ```bash
   # 编辑 projects/NSFC_Young/extraTex/@config.tex
   vim projects/NSFC_Young/extraTex/@config.tex
   ```

2. **快速验证**
   ```bash
   cd skills/make_latex_model
   ./scripts/validate.sh
   ```

3. **性能测试**（可选）
   ```bash
   ./scripts/benchmark.sh
   ```

4. **人工验证**（如需）
   - 对比 Word PDF 和 LaTeX PDF
   - 检查视觉相似度
   - 验证像素对齐（如有 Word PDF 基准）

---

## 测试会话管理

### 创建新的测试会话

```bash
# 使用时间戳命名
TIMESTAMP=$(date +%Y%m%d%H%M)
mkdir -p skills/make_latex_model/tests/v${TIMESTAMP}/{scripts,output}

# 复制测试工具
cp skills/make_latex_model/scripts/*.sh skills/make_latex_model/tests/v${TIMESTAMP}/scripts/
```

### 测试会话结构

```
tests/v{TIMESTAMP}/
├── BUG_REPORT.md           # 问题报告
├── OPTIMIZATION_PLAN.md   # 优化计划
├── TEST_REPORT.md          # 测试报告
├── scripts/                # 测试工具
│   ├── validate.sh
│   └── benchmark.sh
└── output/                 # 测试输出
    └── benchmark_results.json
```

---

## 常见问题

### Q: 验证脚本提示"行距设置: 未找到 baselinestretch 定义"?

A: 这是正常的。当前项目使用 `\linespread` 而非 `\baselinestretch`,两者都是有效的行距设置方式。

### Q: 如何使用标题对比工具？

A: 首先安装依赖：
```bash
pip install python-docx
```

然后运行对比：
```bash
python3 scripts/compare_headings.py word.docx main.tex --report report.html
```

### Q: Word 文档是 .doc 格式，如何处理？

A: 使用 LibreOffice 转换为 .docx：
```bash
soffice --headless --convert-to docx template.doc
```

### Q: 性能测试中的编译时间波动很大?

A: 编译时间受系统负载影响。benchmark.sh 会运行 3 次取平均值,减少波动影响。

### Q: 如何在 Windows 上运行这些脚本?

A: 需要 Git Bash 或 WSL (Windows Subsystem for Linux)。在 Git Bash 中直接运行即可。

---

## 维护指南

### 更新验证脚本

当添加新的检查项时:
1. 编辑 `scripts/validate.sh`
2. 添加新的 `pass/fail/warn` 检查
3. 更新本文档的"检查项"列表

### 更新性能基准

当项目结构变化导致编译时间变化时:
1. 运行 `benchmark.sh` 获取新的基准数据
2. 更新 `config.yaml` 中的性能目标
3. 记录在 CHANGELOG 中

---

## 版本历史

- v1.4.0 (2026-01-05): 新增标题文字工具
  - 新增 `extract_headings.py`：从 Word/LaTeX 提取标题文字
  - 新增 `compare_headings.py`：对比标题文字差异，生成 HTML 可视化报告
  - 更新 `validate.sh`：集成自动标题文字一致性检查
  - 更新工作流：支持标题对齐自动化

- v1.3.0 (2026-01-05): 初始版本
  - 集成到 make_latex_model 技能
  - 自动化验证脚本
  - 性能基准测试脚本
