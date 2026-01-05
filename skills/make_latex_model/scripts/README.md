# make_latex_model 测试工具

本目录包含 `make_latex_model` 技能的测试工具,用于自动化验证和性能基准测试。

## 工具清单

### 1. validate.sh - 自动化验证脚本

**功能**: 自动检查技能状态和项目配置

**使用方法**:
```bash
cd skills/make_latex_model
./scripts/validate.sh
```

**检查项**:
- ✅ 第一优先级: 基础编译检查 (项目目录、配置文件、编译状态、版本号一致性)
- ✅ 第二优先级: 样式参数一致性 (行距、颜色、边距、标题格式)
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
✅ 版本号一致: v1.3.0

第二优先级：样式参数一致性
✅ 颜色定义: MsBlue RGB 0,112,192 (正确)
✅ 页面边距: 左 3.20cm, 右 3.14cm (符合 2026 模板)

总检查项: 9
  通过: 6
  警告: 2
  失败: 1
```

---

### 2. benchmark.sh - 性能基准测试

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

A: 这是正常的。当前项目使用 `\linespread` 而非 `\baselinestretch`,两者都是有效的行距设置方式。验证脚本未来会支持这两种方式。

### Q: 性能测试中的编译时间波动很大?

A: 编译时间受系统负载影响。benchmark.sh 会运行 3 次取平均值,减少波动影响。如需更精确测量,可增加测试次数:
```bash
# 编辑 benchmark.sh
TIMES=5  # 改为 5 次
```

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

- v1.3.0 (2026-01-05): 初始版本
  - 集成到 make_latex_model 技能
  - 自动化验证脚本
  - 性能基准测试脚本
