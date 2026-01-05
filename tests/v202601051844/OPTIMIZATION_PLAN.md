# 优化计划: make_latex_model v202601051930

## 计划概述
- **迭代目标**: 修复行距系统冲突、页边距不对称、标题缩进不一致等关键问题，使 LaTeX PDF 与 Word 2026 模板达到更高的像素级对齐
- **预期成果**:
  - 行距从 1.8 倍修正为 1.2 倍（与 Word 一致）
  - 页边距从对称 3.175cm 调整为 3.20cm（左）+ 3.14cm（右）
  - Section 标题缩进从 2.5em 调整为 1.45em
  - changed_ratio 从 0.1652 降低到 < 0.05（考虑到 QuickLook 基准的局限性）
- **时间估算**: 约 30 分钟（修改 + 编译 + 验证）
- **风险评估**:
  - **低风险**: 修改仅涉及样式参数，不改变代码结构
  - **兼容性**: 保留跨平台支持（`\ifwindows`）
  - **回滚**: 通过 Git 可轻松回滚

## 迭代范围

### 本次迭代修复的问题
- [x] **问题 #1** (P0): 行距系统冲突 - 修改 `\baselinestretch` 为 1.0
- [x] **问题 #2** (P1): 页边距不对称 - 修改为 `left=3.20cm,right=3.14cm`
- [x] **问题 #3** (P1): Section 缩进 - 调整为 1.45em

### 本次迭代暂缓的问题
- **问题 #4** (P2): 字号微调 - 原因: 需要精确测量 Word 打印 PDF 的字号，当前 QuickLook 基准不够精确
- **问题 #5** (P2): 基准 PDF - 原因: 需要用户提供 Word 打印 PDF，或安装 LibreOffice
- **问题 #6** (P3): 列表样式 - 原因: 低优先级，可在后续迭代中优化

## Step-by-Step 修复步骤

### 步骤 1: 修复问题 #1 - 行距系统冲突

**文件**: `tests/v202601051844/NSFC_Young/extraTex/@config.tex`
**行号**: 91

**修改内容**:
```latex
% 修改前
\renewcommand{\baselinestretch}{1.5}

% 修改后
\renewcommand{\baselinestretch}{1.0} % 2026 Word 模板行距为 1.2 倍，由字号命令的 baselineskip 控制
```

**理由**:
- Word 2026 模板的行距为 120%（1.2 倍）
- 当前字号命令（如 `\sihao`）的 baselineskip 已设置为 `1.2x`（16.8pt）
- 全局 `\baselinestretch{1.5}` 会导致实际行距约为 `1.5 × 1.2 = 1.8` 倍，与 Word 严重不符
- 将 `\baselinestretch` 改为 `1.0` 后，行距将完全由字号命令的 baselineskip 控制，统一为 1.2 倍

**验证方法**:
- 编译 `compare_2026.tex`
- 测量 PDF 中 14pt 字号文本的行距（基线到基线）
- 预期结果: 16.8pt（14pt × 1.2）

---

### 步骤 2: 修复问题 #2 - 页边距不对称

**文件**: `tests/v202601051844/NSFC_Young/extraTex/@config.tex`
**行号**: 21

**修改内容**:
```latex
% 修改前
\geometry{left=3.175cm,right=3.175cm,top=2.54cm,bottom=2.54cm}

% 修改后
\geometry{left=3.20cm,right=3.14cm,top=2.54cm,bottom=2.54cm} % 2026 Word 模板边距
```

**理由**:
- Word 2026 模板的左边距为 3.20cm，右边距为 3.14cm（不对称）
- 当前配置使用对称的 3.175cm，与 Word 不完全匹配
- 根据 `config.yaml` 的定义（`margin_left: "3.20cm"`, `margin_right: "3.14cm"`）

**验证方法**:
- 编译 `compare_2026.tex`
- 测量 PDF 的左右边距
- 预期结果: 左边距 3.20cm ± 0.5mm，右边距 3.14cm ± 0.5mm

---

### 步骤 3: 修复问题 #3 - Section 标题缩进

**文件**: `tests/v202601051844/NSFC_Young/extraTex/@config.tex`
**行号**: 160

**修改内容**:
```latex
% 修改前
\titleformat{\section}
  {\color{MsBlue} \sectionzihao \templatefont \bfseries}
  {\hspace{2.5em}} % label
  {0pt} % separation
  {}   % before-code

% 修改后
\titleformat{\section}
  {\color{MsBlue} \sectionzihao \templatefont \bfseries}
  {\hspace{1.45em}} % label（2026 Word 模板缩进）
  {0pt} % separation
  {}   % before-code
```

**理由**:
- 根据 `config.yaml` 的定义（`indent: "1.45em"`）
- Word 2026 模板的 section 标题缩进约为 1.45em（约 20.3pt）
- 当前的 2.5em（约 35pt）可能过大

**验证方法**:
- 编译 `compare_2026.tex`
- 测量 Section 标题左侧到版心左边的距离
- 预期结果: 约 1.45em（14pt × 1.45 ≈ 20.3pt）

---

## 测试计划

### 测试用例 1: 验证行距修复（问题 #1）

**测试场景**: 测量正文的行距是否为 1.2 倍

**输入**:
- 修改后的 `@config.tex`（`\baselinestretch{1.0}`）
- 测试文件 `compare_2026.tex`

**预期输出**:
- 14pt 字号的行距为 16.8pt
- 12pt 字号的行距为 14.4pt

**验证点**:
- [ ] 编译成功，无错误和警告
- [ ] PDF 中相邻两行的基线距离为字号 × 1.2
- [ ] 视觉上文本密度与 Word 预览接近（行距更紧凑）

---

### 测试用例 2: 验证页边距修复（问题 #2）

**测试场景**: 测量页面边距是否匹配 Word 模板

**输入**:
- 修改后的 `@config.tex`（`left=3.20cm,right=3.14cm`）
- 测试文件 `compare_2026.tex`

**预期输出**:
- 左边距: 3.20cm ± 0.5mm
- 右边距: 3.14cm ± 0.5mm
- 上下边距: 2.54cm ± 0.5mm

**验证点**:
- [ ] 编译成功
- [ ] PDF 的版心位置与 Word 预览对齐
- [ ] 每行字数与 Word 接近

---

### 测试用例 3: 验证 Section 缩进修复（问题 #3）

**测试场景**: 测量 Section 标题的左缩进

**输入**:
- 修改后的 `@config.tex`（`\hspace{1.45em}`）
- 测试文件 `compare_2026.tex`

**预期输出**:
- Section 标题左侧到版心左边的距离约为 1.45em（20.3pt）

**验证点**:
- [ ] 编译成功
- [ ] Section 标题位置与 Word 预览对齐
- [ ] 视觉上缩进合理（不过大或过小）

---

### 测试用例 4: 像素对比验证

**测试场景**: 运行像素对比脚本，验证整体改进效果

**输入**:
- 修改后的 LaTeX PDF（`compare_2026.pdf`）
- Word 基准 PNG（`artifacts/baseline/word.png`）

**预期输出**:
- `changed_ratio` < 0.05（从 0.1652 降低）
- `mean_abs_diff` < 10（从 19.62 降低）

**验证点**:
- [ ] 像素对比脚本运行成功
- [ ] diff PNG 显示差异明显减少
- [ ] diff JSON 显示指标改善

---

## 验收标准

### 编译检查
- [ ] `xelatex compare_2026.tex` 编译成功，无错误
- [ ] 日志中无致命警告（如字体缺失）

### 样式对齐
- [ ] **行距**: 正文行距为 1.2 倍（与 Word 一致）
- [ ] **页边距**: 左 3.20cm，右 3.14cm（误差 < 0.5mm）
- [ ] **标题缩进**: Section 标题缩进约 1.45em

### 像素对比指标
- [ ] `changed_ratio` < 0.05（约 5% 以下）
- [ ] `mean_abs_diff` < 10
- [ ] 视觉上 LaTeX PDF 与 Word 预览更接近

### 兼容性
- [ ] 保留跨平台支持（`\ifwindows` 条件判断）
- [ ] 代码结构未改变（仅参数调整）
- [ ] 可通过 Git 回滚

### 文档更新
- [ ] 更新 `TEST_REPORT.md`
- [ ] 如有必要，更新 `@CHANGELOG.md`

---

## 执行流程

### 1. 备份当前状态
```bash
cd tests/v202601051844/NSFC_Young
git status  # 确认当前状态
```

### 2. 执行修改
按顺序修改 `@config.tex` 的三个位置：
- 行 91: `\baselinestretch`
- 行 21: `\geometry`
- 行 160: `\titleformat{\section}`

### 3. 编译测试
```bash
cd tests/v202601051844/NSFC_Young
xelatex -interaction=nonstopmode compare_2026.tex
xelatex -interaction=nonstopmode compare_2026.tex  # 第二次编译，确保交叉引用正确
```

### 4. 生成 PNG 并对比
```bash
cd tests/v202601051844
qlmanage -t -s 2000 -o artifacts/compare2026_iter3 NSFC_Young/compare_2026.pdf
python3 scripts/compare_images.py \
  --a artifacts/compare2026_iter3/latex.png \
  --b artifacts/baseline/word.png \
  --out artifacts/compare2026_iter3/diff.png \
  --report artifacts/compare2026_iter3/diff.json \
  --crop 0,0,1414,1200
```

### 5. 分析结果
- 查看 `artifacts/compare2026_iter3/diff.json`
- 对比 `iter2` 和 `iter3` 的指标变化
- 生成 `TEST_REPORT.md`

---

## 风险与应对

### 潜在风险
1. **行距过小**: 修改后行距从 1.8 倍变为 1.2 倍，可能导致文本密度增加，每页字数增加
2. **边距不对称**: 左右边距不对称可能导致视觉上的不平衡
3. **标题缩进过小**: 从 2.5em 改为 1.45em，可能导致标题看起来不够突出

### 应对措施
1. **行距**: 如果 1.2 倍过小，可以微调字号命令的 baselineskip（如 1.25x）
2. **边距**: 如果不对称导致视觉问题，可以微调为更接近的值（如 3.17cm / 3.17cm）
3. **缩进**: 如果 1.45em 过小，可以尝试中间值（如 1.8em 或 2.0em）

---

## 下一步行动

### 如果测试通过
1. 更新 `TEST_REPORT.md`，记录修复结果
2. 更新 `@CHANGELOG.md`，记录样式变更
3. 评估是否需要将修改应用到正式项目（`projects/NSFC_Young`）
4. 考虑进入下一轮迭代（问题 #4-6）

### 如果测试失败
1. 分析失败原因（查看 diff PNG 和日志）
2. 调整参数（如行距、边距、缩进）
3. 重新编译和验证
4. 创建新的测试会话（`v20260105XXXX`）
