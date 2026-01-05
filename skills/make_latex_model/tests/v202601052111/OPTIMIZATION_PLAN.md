# 优化计划: make_latex_model v202601052111

## 计划概述
- **迭代目标**: 修复文档一致性问题,建立性能基准,创建测试工具
- **预期成果**:
  - 修复 SKILL.md 版本号不一致问题
  - 建立性能基准测试框架
  - 创建验证自动化脚本
  - 生成性能评估报告
- **时间估算**: 约 20 分钟（修复 + 测试 + 文档）
- **风险评估**:
  - **低风险**: 主要是文档修复和工具创建,不影响核心功能
  - **兼容性**: 新增脚本向后兼容
  - **回滚**: 通过 Git 可轻松回滚

## 迭代范围

### 本次迭代修复的问题
- [x] **问题 #1** (P1): SKILL.md 版本号不一致 - 更新 frontmatter
- [ ] **问题 #2** (P2): 缺少性能基准测试 - 创建性能测试脚本
- [ ] **问题 #3** (P2): 验证流程缺少自动化 - 创建验证脚本

### 本次迭代暂缓的问题
- **问题 #4** (P3): 性能优化建议文档 - 下次迭代
- **问题 #5** (P3): 测试实例模板 - 下次迭代

## Step-by-Step 修复步骤

### 步骤 1: 修复问题 #1 - SKILL.md 版本号不一致

**文件**: `skills/make_latex_model/SKILL.md`
**行号**: 3

**修改内容**:
```yaml
# 修改前
---
name: make_latex_model
version: 1.0.0
description: 基于 NSFC 最新 Word 模板高保真优化 LaTeX 模板样式（仅修改 @config.tex；不改 main.tex 正文）
category: normal
---

# 修改后
---
name: make_latex_model
version: 1.2.0
description: 基于 NSFC 最新 Word 模板高保真优化 LaTeX 模板样式（优先级分层验证机制）
category: normal
---
```

**理由**:
- 确保文档一致性
- 与 config.yaml 和版本历史保持同步

**验证方法**:
- 检查 SKILL.md frontmatter
- 对比 config.yaml 版本号
- 预期: 版本号一致

---

### 步骤 2: 创建性能测试脚本（问题 #2）

**文件**: `skills/make_latex_model/tests/v202601052111/scripts/benchmark.sh`

**创建内容**:
```bash
#!/bin/bash
# 性能基准测试脚本

PROJECT="../projects/NSFC_Young"
TIMES=3
OUTPUT="output/benchmark_results.json"

echo "{" > $OUTPUT
echo "  \"test_time\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"," >> $OUTPUT
echo "  \"platform\": \"$(uname -s)\"," >> $OUTPUT
echo "  \"compiler\": \"$(xelatex --version | head -n 1)\"," >> $OUTPUT

# 编译时间测试
echo "  \"compilation_times\": [" >> $OUTPUT
for i in $(seq 1 $TIMES); do
  cd $PROJECT
  START=$(date +%s%N)
  xelatex -interaction=nonstopmode main.tex > /dev/null 2>&1
  END=$(date +%s%N)
  DURATION=$(( ($END - $START) / 1000000 ))
  echo "    $DURATION," >> ../$OUTPUT
  cd -
done
echo "    0" >> $OUTPUT
echo "  ]," >> $OUTPUT

echo "  \"average_time\": \"calc...\"," >> $OUTPUT
echo "  \"memory_usage\": \"tbd\"" >> $OUTPUT
echo "}" >> $OUTPUT

cat $OUTPUT
```

**理由**:
- 建立性能基准
- 可量化的性能评估

**验证方法**:
- 运行脚本
- 检查输出 JSON
- 预期: 生成性能数据

---

### 步骤 3: 创建验证自动化脚本（问题 #3）

**文件**: `skills/make_latex_model/tests/v202601052111/scripts/validate.sh`

**创建内容**:
```bash
#!/bin/bash
# 验证自动化脚本

PROJECT="../projects/NSFC_Young"
CONFIG="$PROJECT/extraTex/@config.tex"

echo "=== make_latex_model 验证报告 ==="
echo ""

# 第一优先级：编译检查
echo "✓ 第一优先级：基础编译检查"
if [ -f "$PROJECT/main.pdf" ]; then
  echo "  ✅ 编译成功: main.pdf 存在"
else
  echo "  ❌ 编译失败: main.pdf 不存在"
fi

# 第二优先级：样式参数检查
echo ""
echo "✓ 第二优先级：样式参数一致性"

# 检查行距设置
if grep -q "baselinestretch{1.0}" $CONFIG; then
  echo "  ✅ 行距设置: 1.0 (正确)"
else
  echo "  ⚠️  行距设置: 非 1.0 (需检查)"
fi

# 检查颜色定义
if grep -q "definecolor.*MsBlue.*RGB.*0,112,192" $CONFIG; then
  echo "  ✅ 颜色定义: MsBlue RGB 0,112,192 (正确)"
else
  echo "  ⚠️  颜色定义: MsBlue 值需检查"
fi

# 第三优先级：视觉相似度
echo ""
echo "✓ 第三优先级：视觉相似度"
echo "  ⚠️  需要人工检查: PDF 与 Word 模板视觉对比"

# 第四优先级：像素对比
echo ""
echo "✓ 第四优先级：像素对比"
echo "  ℹ️  仅当使用 Word 打印 PDF 基准时进行"

echo ""
echo "=== 验证完成 ==="
```

**理由**:
- 自动化大部分验证项
- 提升验证效率

**验证方法**:
- 运行脚本
- 检查输出
- 预期: 自动完成基础验证

---

### 步骤 4: 执行性能测试

**命令**:
```bash
cd skills/make_latex_model/tests/v202601052111
chmod +x scripts/benchmark.sh
./scripts/benchmark.sh
```

**预期输出**:
- 编译时间数据
- 内存使用情况
- 性能基准报告

---

## 测试计划

### 测试用例 1: 验证版本号修复（问题 #1）

**测试场景**: 检查 SKILL.md 版本号是否一致

**输入**:
- 修改后的 SKILL.md

**预期输出**:
- frontmatter 版本号: 1.2.0
- config.yaml 版本号: 1.2.0
- 版本历史: v1.2.0

**验证点**:
- [ ] SKILL.md frontmatter 版本号正确
- [ ] 所有文档版本号一致

---

### 测试用例 2: 性能基准测试（问题 #2）

**测试场景**: 测量编译性能

**输入**:
- NSFC_Young 项目
- 性能测试脚本

**预期输出**:
- 平均编译时间 < 30 秒
- 生成性能报告

**验证点**:
- [ ] 脚本运行成功
- [ ] 生成性能数据
- [ ] 编译时间在合理范围

---

### 测试用例 3: 验证自动化测试（问题 #3）

**测试场景**: 自动验证技能状态

**输入**:
- NSFC_Young 项目
- 验证脚本

**预期输出**:
- 自动完成基础验证
- 生成验证报告

**验证点**:
- [ ] 脚本运行成功
- [ ] 检测关键配置项
- [ ] 报告格式清晰

---

## 验收标准

### 文档修复
- [ ] SKILL.md 版本号与 config.yaml 一致
- [ ] 所有文档引用版本号统一

### 性能测试
- [ ] 性能测试脚本可运行
- [ ] 生成性能基准数据
- [ ] 编译时间 < 30 秒

### 验证自动化
- [ ] 验证脚本可运行
- [ ] 自动检查编译状态
- [ ] 自动检查样式参数

### 文档更新
- [ ] 更新 TEST_REPORT.md
- [ ] 记录性能基准

---

## 执行流程

### 1. 修复版本号
```bash
# 编辑 SKILL.md frontmatter
vim skills/make_latex_model/SKILL.md
```

### 2. 创建测试脚本
```bash
cd skills/make_latex_model/tests/v202601052111
# 创建 benchmark.sh 和 validate.sh
```

### 3. 执行性能测试
```bash
chmod +x scripts/*.sh
./scripts/benchmark.sh
./scripts/validate.sh
```

### 4. 生成测试报告
```bash
# 整理结果
# 生成 TEST_REPORT.md
```

---

## 风险与应对

### 潜在风险
1. **性能测试不稳定**: 每次编译时间可能波动
2. **验证脚本误报**: 自动检查可能漏报或误报
3. **环境差异**: 不同系统的性能差异

### 应对措施
1. **性能测试**: 多次测试取平均值
2. **验证脚本**: 逐步完善检查逻辑
3. **环境差异**: 记录测试环境信息

---

## 下一步行动

### 如果测试通过
1. 合并版本号修复到主分支
2. 将测试脚本添加到技能目录
3. 更新技能文档

### 如果测试失败
1. 分析失败原因
2. 调整脚本或修复方案
3. 创建新的测试会话
