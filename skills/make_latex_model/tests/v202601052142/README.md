# make_latex_model 能力测试实例 v202601052142

## 测试目标

本测试实例旨在全面评估 `make_latex_model` 技能将 Word 模板转换为 LaTeX 项目的能力。

## 测试场景

以 `projects/NSFC_Young` 为例，利用 2026 年最新 Word 模板进行 LaTeX 模板样式高保真优化。

## 测试范围

### 包含

- Word 模板样式提取（页面、字体、字号、颜色、间距、标题格式、列表样式）
- LaTeX 样式配置修改（`@config.tex`）
- 跨平台编译验证
- 样式参数一致性检查
- 视觉相似度评估
- 像素级 PDF 对比（辅助验证）

### 不包含

- `main.tex` 正文内容修改（除非用户明确要求）
- 宏包架构重构
- 新功能开发

## 测试流程

1. **准备阶段**：复制测试材料到 `input/` 目录
2. **执行阶段**：运行 `run_test.sh` 执行测试
3. **验证阶段**：使用 `validate.py` 进行自动化验证
4. **报告阶段**：生成测试报告 `REPORT.md`

## 目录结构

```
v202601052142/
├── README.md                   # 本文件
├── config.yaml                 # 测试配置
├── run_test.sh                 # 测试执行脚本
├── validate.py                 # 验证脚本
├── input/                      # 测试输入材料
│   ├── word_template/          # Word 模板文件
│   └── project_backup/         # 项目原始状态备份
├── output/                     # 测试输出结果
│   ├── latex_project/          # 生成的 LaTeX 项目
│   ├── artifacts/              # 编译产物
│   └── changes/                # 代码变更记录
├── expected/                   # 预期结果定义
│   ├── style_params.yaml       # 预期样式参数
│   └── word_baseline.pdf       # Word 打印 PDF 基准
└── validation/                 # 验证结果
    ├── pixel_diff.json         # 像素对比结果
    ├── style_check.json        # 样式检查结果
    └── compilation_log.txt     # 编译日志
```

## 执行测试

```bash
cd skills/make_latex_model/tests/v202601052142
./run_test.sh
```

## 测试评估标准

### 第一优先级：基础编译（权重 40%）
- [ ] 编译无错误
- [ ] 编译无警告
- [ ] 跨平台兼容性

### 第二优先级：样式参数（权重 30%）
- [ ] 页面设置一致（边距、版心）
- [ ] 字体字号一致
- [ ] 颜色值一致（MsBlue）
- [ ] 标题格式一致
- [ ] 间距参数一致（行距、段间距）

### 第三优先级：视觉相似度（权重 20%）
- [ ] PDF 整体布局相似
- [ ] 每行字数接近（±1 字）
- [ ] 换行位置对齐

### 第四优先级：像素对比（权重 10%）
- [ ] 像素差异率 < 20%
- [ ] 关键区域对齐

## 测试通过标准

- ✅ **必须通过**：第一优先级全部项目
- ✅ **推荐通过**：第二优先级 ≥ 80%
- ✅ **优秀**：第三优先级 ≥ 70%
- ⚠️ **可接受**：第四优先级仅供参考

## 预期结果

测试成功后，应生成：
1. 可编译的 LaTeX 项目（`output/latex_project/`）
2. 符合 Word 模板样式的 PDF（`output/artifacts/main.pdf`）
3. 详细的变更记录（`output/changes/`）
4. 完整的验证报告（`validation/`）
5. 测试总结报告（`REPORT.md`）

## 注意事项

1. ⚠️ **测试过程在沙箱目录中进行**，不会修改原始 `projects/NSFC_Young`
2. ⚠️ **需要准备 Word 打印 PDF 基准**（见 `expected/README.md`）
3. ⚠️ **像素对比仅作为辅助验证**，应以样式参数一致性为主

## 参考文档

- [技能定义](../../SKILL.md)
- [优化计划](../../OPTIMIZATION_PLAN.md)
- [验证脚本说明](../../scripts/README.md)
