# 方法学提取模式

本文档总结从科研论文中提取方法学信息的常见模式。

## Methods 章节结构

### 常见小节

1. **Study Design**
   - 研究类型
   - 对照设置
   - 随机化方法

2. **Data Collection**
   - 数据来源
   - 采集时间
   - 样本量计算

3. **Preprocessing**
   - 质量控制
   - 归一化
   - 异常值处理

4. **Statistical Analysis**
   - 主要分析方法
   - 多重比较校正
   - 效应量计算

5. **Software**
   - 软件名称
   - 版本信息
   - 参数设置

## 提取模式

### 统计方法识别

**常见关键词**：
- 检验: t-test, ANOVA, chi-square, Mann-Whitney
- 回归: linear regression, logistic regression, Cox regression
- 校正: Bonferroni, FDR, Benjamini-Hochberg
- 效应量: Cohen's d, odds ratio, hazard ratio

**提取模板**：
```
"We used [方法名称] to compare [比较对象]"
"[方法名称] was applied using [软件名称] version [版本号]"
"Multiple testing was corrected using [校正方法]"
```

### 软件工具识别

**R 包格式**：
```
"R (version X.Y.Z) with the [包名] package"
"analysis was performed in [包名] (version X.Y.Z)"
```

**Python 包格式**：
```
"Python (X.Y) using [包名] (version X.Y.Z)"
"[包名] library was used for..."
```

### 参数设置提取

**常见模式**：
```
"with a significance threshold of [数值]"
"using [参数名] = [数值]"
"[参数名] was set to [数值]"
```

## 验证方法识别

### 内部验证
- Cross-validation
- Bootstrap
- Split-sample validation

### 外部验证
- Independent cohort
- External dataset
- Prospective validation

## 质量控制指标

### 数据质量
- Missing data percentage
- Outlier detection method
- Data completeness criteria

### 统计质量
- Power calculation
- Confidence intervals
- Sensitivity analysis

## 常见陷阱

1. **补充材料**：重要细节常在 supplementary materials
2. **版本差异**：软件版本对结果可能有影响
3. **默认参数**：作者可能未明确说明使用的参数
4. **多方法组合**：可能需要结合多种方法

## AI 提取建议

### 高优先级信息
1. 主要统计方法
2. 软件名称和版本
3. 样本量计算
4. 校正方法

### 中优先级信息
1. 参数设置
2. 验证策略
3. 质量控制标准

### 低优先级信息
1. 可选分析
2. 探索性方法
3. 可视化工具（除非是研究重点）
