# 优化计划: make_latex_model 技能 v1.3.2

## 计划概述
- **迭代目标**: 修复验证脚本问题，完善跨项目支持
- **预期成果**:
  - `validate.sh` 能正确验证 NSFC_General 和 NSFC_Young 项目
  - `config.yaml` 包含多项目的样式参考配置
  - 文档更新，说明不同项目的配置差异
- **时间估算**: 30 分钟
- **风险评估**: 低风险，仅修改验证脚本和配置文件

## 迭代范围

### 本次迭代修复的问题
- [ ] 问题 #1 (P1) - 修复 validate.sh 行距检查正则表达式
- [ ] 问题 #2 (P2) - 更新 config.yaml 添加 NSFC_General 样式参考
- [ ] 问题 #3 (P3) - 在 SKILL.md 中添加项目差异说明

### 本次迭代暂缓的问题
- 无

## Step-by-Step 修复步骤

### 步骤 1: 修复问题 #1 - validate.sh 行距检查
**文件**: `skills/make_latex_model/scripts/validate.sh`
**方法**: 行距检查逻辑
**行号**: 118-120

**修改内容**:
```bash
# 修改前
if grep -q "\\renewcommand{\\baselinestretch}{1.0}" "$CONFIG"; then
  pass "行距设置: baselinestretch{1.0}"
elif grep -q "\\renewcommand{\\baselinestretch}" "$CONFIG"; then
  fail "行距设置: 未找到 baselinestretch 定义"
fi

# 修改后
if grep -q "\\renewcommand{\\baselinestretch}{1.5}" "$CONFIG"; then
  pass "行距设置: baselinestretch{1.5} (符合 2026 Word 模板)"
elif grep -q "\\renewcommand{\\baselinestretch}" "$CONFIG"; then
  LINE_STRETCH=$(grep "\\renewcommand{\\baselinestretch}" "$CONFIG" | sed 's/.*{\(.*\)}.*/\1/')
  warn "行距设置: baselinestretch{$LINE_STRETCH} (建议为 1.5)"
else
  fail "行距设置: 未找到 baselinestretch 定义"
fi
```

**验证方法**:
- 测试用例: 运行 `bash skills/make_latex_model/scripts/validate.sh`
- 预期结果: "行距设置"项显示通过
- 验证点: 脚本应正确识别 1.5 倍行距

---

### 步骤 2: 修复问题 #2 - 更新 config.yaml
**文件**: `skills/make_latex_model/config.yaml`
**方法**: 添加多项目样式参考配置
**行号**: 62-126

**修改内容**:
```yaml
# 修改前
style_reference:
  # 页面设置
  page:
    margin_left: "3.20cm"
    margin_right: "3.14cm"
    ...

# 修改后
style_reference:
  # 默认样式参考（适用于 NSFC_Young）
  default:
    page:
      margin_left: "3.20cm"
      margin_right: "3.14cm"
      margin_top: "2.54cm"
      margin_bottom: "2.54cm"
      line_spacing: 1.5
    ...

  # NSFC_General 专用配置
  NSFC_General:
    page:
      margin_left: "3.00cm"   # 面上项目左边距
      margin_right: "3.07cm"  # 面上项目右边距
      margin_top: "2.50cm"
      margin_bottom: "2.50cm"
      line_spacing: 1.5
    # 其他样式与 default 相同
    colors:
      MsBlue: "RGB 0,112,192"
    fonts:
      chinese_main: "KaiTi"
      english_main: "Times New Roman"
    # ... 其他配置

  # NSFC_Local 专用配置（如有差异）
  NSFC_Local:
    # 可以添加地区项目的特殊配置
    ...
```

**验证方法**:
- 测试用例: 读取 config.yaml，验证 NSFC_General 配置存在
- 预期结果: config.yaml 包含 NSFC_General 的独立配置
- 验证点: 配置结构清晰，易于扩展

---

### 步骤 3: 修复问题 #3 - 更新 SKILL.md
**文件**: `skills/make_latex_model/SKILL.md`
**方法**: 添加项目差异说明章节
**位置**: 在"2) 输入参数"章节后添加

**修改内容**:
```markdown
## 2.1) 项目差异说明

本技能支持三种 NSFC 项目类型，它们在样式配置上存在以下差异：

### 页面设置差异

| 配置项 | NSFC_Young | NSFC_General | NSFC_Local |
|--------|------------|--------------|------------|
| 左边距 | 3.20 cm | 3.00 cm | 3.20 cm |
| 右边距 | 3.14 cm | 3.07 cm | 3.14 cm |
| 上边距 | 2.54 cm | 2.50 cm | 2.54 cm |
| 下边距 | 2.54 cm | 2.50 cm | 2.54 cm |

### 其他样式

以下样式在所有项目类型中保持一致：
- **行距**: 1.5 倍
- **颜色**: MsBlue (RGB 0,112,192)
- **字体**: 中文楷体 + 英文 Times New Roman
- **字号**: 四号 14pt，小四 12pt
- **标题格式**: 四级标题，编号格式一致
- **列表样式**: 编号（1），缩进 4em

### 使用建议

1. **首次使用**: 建议先运行 `validate.sh` 检查当前配置是否符合所选项目类型
2. **跨项目切换**: 切换项目类型时，注意检查页面边距设置
3. **自定义修改**: 如需自定义样式，建议在 `@config.tex` 中添加注释说明修改原因
```

**验证方法**:
- 测试用例: 阅读 SKILL.md，查找"项目差异说明"章节
- 预期结果: 文档包含完整的项目差异对比表
- 验证点: 用户能快速了解不同项目的配置差异

---

## 测试计划

### 测试用例 1: 验证 validate.sh 行距检查修复
**测试场景**: 运行验证脚本，检查行距验证是否正确

**输入**:
```bash
cd skills/make_latex_model
bash scripts/validate.sh
```

**预期输出**:
```
第二优先级：样式参数一致性
=========================================
✅ 行距设置: baselinestretch{1.5} (符合 2026 Word 模板)
```

**验证点**:
- [ ] 脚本执行无错误
- [ ] 行距检查显示通过
- [ ] 输出信息明确说明符合 2026 Word 模板

---

### 测试用例 2: 验证 config.yaml 多项目配置
**测试场景**: 读取 config.yaml，验证多项目配置结构

**输入**: 读取 `skills/make_latex_model/config.yaml`

**预期结果**:
- config.yaml 包含 `style_reference.default` 配置
- config.yaml 包含 `style_reference.NSFC_General` 配置
- NSFC_General 的左边距为 3.00cm，右边距为 3.07cm

**验证点**:
- [ ] 配置结构清晰
- [ ] NSFC_General 配置与实际 @config.tex 一致
- [ ] 易于扩展新的项目类型

---

### 测试用例 3: 验证 SKILL.md 文档更新
**测试场景**: 阅读 SKILL.md，查找项目差异说明

**输入**: 阅读 `skills/make_latex_model/SKILL.md`

**预期结果**:
- 文档包含"2.1) 项目差异说明"章节
- 章节包含完整的对比表
- 说明文字清晰易懂

**验证点**:
- [ ] 文档章节存在
- [ ] 对比表包含所有关键差异
- [ ] 使用建议部分有帮助

---

### 测试用例 4: 跨项目验证测试
**测试场景**: 分别验证 NSFC_Young 和 NSFC_General 项目

**输入**:
```bash
# 测试 NSFC_Young
cd projects/NSFC_Young
bash ../../skills/make_latex_model/scripts/validate.sh

# 测试 NSFC_General
cd ../NSFC_General
bash ../../skills/make_latex_model/scripts/validate.sh
```

**预期结果**:
- NSFC_Young: 边距 3.20cm / 3.14cm 检查通过
- NSFC_General: 边距 3.00cm / 3.07cm 检查通过

**验证点**:
- [ ] 两个项目的验证都通过
- [ ] 验证脚本正确识别不同项目的配置差异

---

## 验收标准
- [ ] 问题 #1 (P1) 已修复: validate.sh 行距检查正确识别 1.5 倍
- [ ] 问题 #2 (P2) 已修复: config.yaml 包含 NSFC_General 配置
- [ ] 问题 #3 (P3) 已修复: SKILL.md 包含项目差异说明
- [ ] 测试用例 100% 通过
- [ ] 无回归问题
- [ ] 文档已更新

---

## 风险评估

### 低风险
- 修改仅涉及验证脚本和配置文件
- 不影响核心编译功能
- 不改变现有样式定义

### 注意事项
1. 修改 validate.sh 时注意正则表达式的转义
2. config.yaml 结构修改后需验证语法正确
3. SKILL.md 更新后需检查格式和链接

---

## 后续行动

### 如果本次测试通过
1. 更新 SKILL.md 版本号为 v1.3.2
2. 更新 config.yaml 版本号为 v1.3.2
3. 在 CHANGELOG.md 中记录变更
4. 提交代码到主分支

### 如果本次测试失败
1. 分析失败原因
2. 更新优化计划
3. 进入下一轮迭代
4. 创建新的测试会话目录

---

**优化计划版本**: 1.0
**最后更新**: 2026-01-05 21:33
