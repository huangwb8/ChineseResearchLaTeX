# Bug报告: make_latex_model 技能 - NSFC_General 项目测试

## 问题概述
- **测试时间**: 2026-01-05 21:33
- **测试环境**: macOS Darwin 25.2.0, arm64
- **测试项目**: NSFC_General (面上项目模板)
- **问题总数**: 3
- **严重程度分布**: High: 1, Medium: 1, Low: 1

## 问题清单

### 问题 #1: validate.sh 脚本中的行距检查正则表达式错误
**严重程度**: Medium
**优先级**: P1
**状态**: Open

**问题描述**:
- 现象描述: `validate.sh` 脚本在检查行距设置时使用了硬编码的值 `1.0`，但 NSFC_Young 和 NSFC_General 项目的实际配置都是 `1.5` 倍行距
- 复现步骤:
  1. 运行 `bash skills/make_latex_model/scripts/validate.sh`
  2. 观察第二优先级检查中的"行距设置"项
  3. 显示失败: "行距设置: 未找到 baselinestretch 定义"
- 实际行为: 脚本检查 `\\renewcommand{\\baselinestretch}{1.0}`，但配置文件中实际是 `\\renewcommand{\\baselinestretch}{1.5}`
- 期望行为: 脚本应正确识别 1.5 倍行距并显示通过
- 影响范围: 所有 NSFC 项目的验证检查

**根因分析**:
- 问题根源: `validate.sh` 第 118 行使用了硬编码的值 1.0，未考虑不同项目可能有不同的行距设置
- 相关代码/文件: `skills/make_latex_model/scripts/validate.sh:118`
- 为什么会出现: 2026 年 Word 模板要求 1.5 倍行距，但验证脚本未及时更新

**修复建议**:
- 推荐方案: 修改验证脚本的正则表达式，改为匹配 `.*1\.5` 或更通用的模式
- 替代方案: 在 `config.yaml` 中添加行距配置项，验证脚本读取配置进行验证
- 预期效果: 验证脚本能正确识别 1.5 倍行距，显示检查通过

**验证方法**:
- 运行验证脚本
- 检查输出中"行距设置"项显示通过
- 测试用例: `bash skills/make_latex_model/scripts/validate.sh`

---

### 问题 #2: config.yaml 中 NSFC_General 项目样式参考基准不完整
**严重程度**: Medium
**优先级**: P2
**状态**: Open

**问题描述**:
- 现象描述: `config.yaml` 中的 `style_reference` 部分只列出了通用的样式参数，但 NSFC_General 项目的实际页边距与配置不完全一致
- 实际行为:
  - 配置中: `margin_left: "3.20cm"`
  - NSFC_General 实际: `margin_left: "3.00cm"`
- 期望行为: `config.yaml` 应明确标注不同项目的差异，或为每个项目单独配置
- 影响范围: 跨项目验证的准确性

**根因分析**:
- 问题根源: `config.yaml` 使用了统一的样式参考基准，未考虑 NSFC_General、NSFC_Young、NSFC_Local 三个项目之间的差异
- 相关代码/文件: `skills/make_latex_model/config.yaml:64-70`
- 为什么会出现: 技能最初设计时可能只考虑了 NSFC_Young 项目

**修复建议**:
- 推荐方案: 重构 `config.yaml`，为每个项目添加独立的样式参考配置
- 替代方案: 在文档中明确说明不同项目的差异，要求用户手动调整
- 预期效果: 每个项目都有准确的样式参考基准

**验证方法**:
- 读取 NSFC_General 的 `@config.tex`
- 对比 `config.yaml` 中的配置
- 验证页面设置参数一致性

---

### 问题 #3: NSFC_General 与 NSFC_Young 的配置差异未在文档中说明
**严重程度**: Low
**优先级**: P3
**状态**: Open

**问题描述**:
- 现象描述: `SKILL.md` 中未明确说明 NSFC_General 和 NSFC_Young 两个项目的配置差异
- 实际行为: 用户需要手动对比两个项目的 `@config.tex` 才能发现差异
- 期望行为: `SKILL.md` 或相关文档应列出不同项目的配置差异
- 影响范围: 用户使用体验

**根因分析**:
- 问题根源: 技能文档主要关注 NSFC_Young 项目，未系统性地考虑多项目支持
- 相关代码/文件: `skills/make_latex_model/SKILL.md`
- 为什么会出现: 技能逐步扩展支持更多项目，但文档未同步更新

**修复建议**:
- 推荐方案: 在 `SKILL.md` 中添加"项目差异说明"章节
- 替代方案: 创建独立的 `PROJECT_DIFFERENCES.md` 文档
- 预期效果: 用户能快速了解不同项目的配置差异

**验证方法**:
- 对比 NSFC_General 和 NSFC_Young 的 `@config.tex`
- 提取关键差异点
- 验证文档中是否包含这些差异说明

---

## 问题统计

| 优先级 | 数量 | 状态 |
|--------|------|------|
| P0 | 0 | - |
| P1 | 1 | 待修复 |
| P2 | 1 | 待修复 |
| P3 | 1 | 待修复 |

## 测试环境详情

```
操作系统: macOS Darwin 25.2.0
架构: arm64 (Apple Silicon)
Shell: bash
Python: 3.x
XeLaTeX: TeX Live 2024
```

## 相关文件

- `skills/make_latex_model/SKILL.md`
- `skills/make_latex_model/config.yaml`
- `skills/make_latex_model/scripts/validate.sh`
- `projects/NSFC_General/extraTex/@config.tex`
- `projects/NSFC_Young/extraTex/@config.tex`
