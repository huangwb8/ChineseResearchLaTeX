# 测试实例 v202601052142 - 文档索引

## 📚 核心文档

### 快速导航

| 文档 | 用途 | 适合人群 |
|------|------|----------|
| [README.md](./README.md) | 测试实例概述和快速开始 | 所有人 |
| [TEST_PLAN.md](./TEST_PLAN.md) | 详细测试计划和测试用例 | 测试人员 |
| [exec_guide.md](./exec_guide.md) | 执行指南和常见问题 | 执行测试的人 |
| [SUMMARY.md](./SUMMARY.md) | 测试框架创建总结 | 了解框架设计的人 |
| [.test_summary.txt](./.test_summary.txt) | 测试总结（文本格式） | 快速浏览 |

### 配置文件

| 文件 | 说明 |
|------|------|
| [config.yaml](./config.yaml) | 测试配置（优先级、权重、验收标准） |

### 脚本文件

| 文件 | 语言 | 说明 |
|------|------|------|
| [run_test.sh](./run_test.sh) | Bash | 测试执行脚本（主入口） |
| [validate.py](./validate.py) | Python | 验证脚本（四级优先级验证） |

## 🚀 快速开始

### 1. 了解测试
阅读 [README.md](./README.md) 了解测试目标和范围

### 2. 执行测试
```bash
./run_test.sh
```

### 3. 查看结果
```bash
cat REPORT.md
cat validation/style_check.json | python3 -m json.tool
```

## 📖 阅读路径

### 路径 A：快速执行（5分钟）
1. [README.md](./README.md) - 了解测试
2. [run_test.sh](./run_test.sh) - 执行测试
3. [REPORT.md](./REPORT.md) - 查看结果

### 路径 B：深入理解（30分钟）
1. [README.md](./README.md) - 测试概述
2. [TEST_PLAN.md](./TEST_PLAN.md) - 测试计划
3. [exec_guide.md](./exec_guide.md) - 执行指南
4. [SUMMARY.md](./SUMMARY.md) - 框架总结
5. [config.yaml](./config.yaml) - 配置说明
6. [validate.py](./validate.py) - 验证逻辑

### 路径 C：框架开发（60分钟）
完整阅读所有文档，理解框架设计和实现细节

## 📁 目录结构说明

### input/ - 测试输入材料
- `word_template/` - Word 模板文件
- `project_backup/` - 项目原始状态备份

### output/ - 测试输出结果
- `latex_project/` - 生成的 LaTeX 项目
- `artifacts/` - 编译产物（PDF、日志等）
- `changes/` - 代码变更记录

### expected/ - 预期结果定义
- `README.md` - 预期结果说明
- `style_params.yaml` - 预期样式参数
- `word_baseline.pdf` - Word 打印 PDF 基准

### validation/ - 验证结果
- `compilation_log.txt` - 编译日志
- `style_check.json` - 样式检查结果
- `pixel_diff.json` - 像素对比结果

## 🔍 常见问题快速查找

### Q: 如何开始测试？
**A**: 阅读 [README.md](./README.md) 的"快速开始"部分

### Q: 测试如何评估？
**A**: 阅读 [TEST_PLAN.md](./TEST_PLAN.md) 的"测试用例"部分

### Q: 如何执行测试？
**A**: 阅读 [exec_guide.md](./exec_guide.md) 的"快速开始"部分

### Q: 测试结果如何解读？
**A**: 阅读 [exec_guide.md](./exec_guide.md) 的"测试结果解读"部分

### Q: 如何配置测试？
**A**: 修改 [config.yaml](./config.yaml) 中的参数

### Q: 测试失败怎么办？
**A**: 查看 [exec_guide.md](./exec_guide.md) 的"常见问题"部分

## 🔗 外部参考

- [技能定义](../../SKILL.md) - make_latex_model 技能完整定义
- [优化计划](../../OPTIMIZATION_PLAN.md) - 技能优化和改进计划
- [项目 CLAUDE.md](../../../../CLAUDE.md) - 项目整体规范
- [验证脚本说明](../../scripts/README.md) - 验证工具使用说明

## 📝 更新日志

- 2026-01-05: 创建测试框架 v1.0.0
  - 创建测试目录结构
  - 编写测试文档
  - 实现测试脚本
  - 定义验证标准

---

**测试实例**: v202601052142
**创建日期**: 2026-01-05
**框架版本**: 1.0.0
