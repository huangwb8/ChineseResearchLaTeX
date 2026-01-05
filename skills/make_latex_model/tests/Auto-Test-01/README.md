# Auto-Test-01: 自动化测试套件

## 测试目标

自动化评估和优化 `make_latex_model` skill 的能力，确保能够准确地将 NSFC_Young 项目对齐到 2026 年 Word 模板。

## 测试参数

- **目标 skill**: `make_latex_model`
- **测试项目**: `NSFC_Young`
- **Word 模板**: `2026年最新word模板-青年科学基金项目（C类）-正文.doc`
- **最大轮次**: 10 轮
- **成功标准**: 目标 skill 完全正常工作

## 目录结构

```
Auto-Test-01/
├── README.md              # 本文件
├── TEST_PLAN.md           # 测试计划
├── config.yaml            # 测试配置
├── artifacts/             # 测试产物
│   ├── baseline/          # Word PDF 基准
│   │   ├── word.pdf       # Word 导出的 PDF
│   │   └── word.png       # 转换的 PNG（用于像素对比）
│   └── output/            # LaTeX 生成的输出
│       ├── round-01/      # 第 1 轮输出
│       ├── round-02/      # 第 2 轮输出
│       └── ...
├── workspace/             # 工作空间（每轮清理重建）
│   ├── NSFC_Young/        # 复制的项目文件
│   └── temp/              # 临时文件
└── logs/                  # 测试日志
    ├── round-01.log       # 第 1 轮日志
    ├── round-02.log       # 第 2 轮日志
    └── summary.log        # 汇总日志
```

## 测试流程

### 第 N 轮测试（N = 1 ~ 10）

1. **环境准备**
   - 清空 `workspace/` 目录
   - 从原始 `projects/NSFC_Young/` 复制文件到 `workspace/NSFC_Young/`
   - 确保不修改原始项目文件

2. **生成基准**
   - 使用 LibreOffice 将 Word 模板转换为 PDF
   - 将 PDF 转换为高分辨率 PNG

3. **执行测试**
   - 调用 `auto-test-skill` 执行测试
   - 运行 `make_latex_model` skill 优化项目
   - 编译 LaTeX 生成 PDF
   - 进行像素对比和样式验证

4. **结果分析**
   - 记录测试结果到 `logs/round-N.log`
   - 识别成功项和失败项

5. **优化决策**
   - 如果完全通过：结束测试
   - 如果有失败项：分析原因，优化 `make_latex_model` skill
   - 更新 skill 文件

6. **下一轮准备**
   - 清空 `workspace/` 目录
   - 开始第 N+1 轮测试

## 验收标准

### 第一优先级：基础编译
- [ ] 编译无错误和警告
- [ ] 字体加载正常

### 第二优先级：样式参数一致性
- [ ] 行距与 Word 一致（1.5 倍）
- [ ] 字号与 Word 一致
- [ ] 颜色与 Word 一致（MsBlue RGB 0,112,192）
- [ ] 页边距一致
- [ ] 标题样式一致

### 第三优先级：视觉相似度
- [ ] PDF 与 Word 模板视觉高度相似
- [ ] 每行字数与 Word 接近
- [ ] 换行位置与 Word 大致对齐

### 第四优先级：像素对比
- [ ] 像素对比指标 changed_ratio < 0.20

## 测试日志格式

```
# Round N 测试日志 (YYYY-MM-DD HH:MM:SS)

## 测试环境
- Skill 版本: vX.X.X
- 测试时间: YYYY-MM-DD HH:MM:SS
- 工作目录: workspace/NSFC_Young

## 测试结果

### 第一优先级：基础编译
- [✅/❌] 编译成功
- [✅/❌] 无警告

### 第二优先级：样式参数一致性
- [✅/❌] 行距一致
- [✅/❌] 字号一致
- ...

## 失败分析
(如果有失败项，分析原因)

## 优化计划
(基于失败分析的优化计划)
```

## 快速命令

```bash
# 运行单轮测试
cd skills/make_latex_model/tests/Auto-Test-01
./run_test.sh

# 查看最新日志
tail -f logs/summary.log

# 清理测试环境
./clean.sh
```
