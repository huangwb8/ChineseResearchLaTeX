# 预期结果定义

本目录存放测试的预期结果定义和基准文件。

## Word PDF 基准

### 文件说明

`word_baseline.pdf` 是从 Word 模板导出的 PDF，作为样式对齐的基准。

### 生成方法

#### 方法 1：Microsoft Word（强烈推荐）

1. 在 Microsoft Word 中打开模板文件
2. 填充示例文本（与 `main.tex` 相同）
3. 选择"文件" → "导出" → "创建 PDF"
4. 保存为 `word_baseline.pdf`

**优点**：最精确，完全符合 Word 渲染效果
**缺点**：需要 Microsoft Word 许可证

#### 方法 2：LibreOffice（免费替代）

```bash
# 安装 LibreOffice
brew install --cask libreoffice

# 转换 .doc 为 PDF
soffice --headless --convert-to pdf \
  --outdir . \
  "input/word_template/2026年最新word模板-青年科学基金项目（C类）-正文.doc"

# 重命名
mv "2026年最新word模板-青年科学基金项目（C类）-正文.pdf" word_baseline.pdf
```

**优点**：免费、跨平台、命令行自动化
**缺点**：渲染效果与 Word 可能有细微差异（但远好于 QuickLook）

#### 方法 3：在线转换（临时方案）

- 使用 CloudConvert、Zamzar 等在线服务
- **注意**：不适合处理敏感内容

### 验证 PDF 质量

```bash
# 检查 PDF 信息
pdfinfo word_baseline.pdf

# 检查页面尺寸（应与 A4 纸一致：595 x 842 pt）
pdfinfo word_baseline.pdf | grep "Page size"
```

### ⚠️ 绝对禁止的做法

- ❌ 使用 `qlmanage -t` 生成 QuickLook 缩略图作为基准
- ❌ 使用 macOS 预览应用打开 .doc 文件截图
- ❌ 使用任何非 Word/LibreOffice 的渲染工具

**原因**：QuickLook 预览渲染引擎与 Word 本质不同（行距、字体渲染、断行算法都有差异），会导致像素对比失真。

## 样式参数定义

`style_params.yaml` 定义了从 Word 模板提取的预期样式参数。

### 参数来源

这些参数应通过以下方式获取：

1. **Word 内置样式检查器**：
   - 在 Word 中打开模板
   - 右键点击段落 → "段落"
   - 查看"缩进和间距"选项卡

2. **PDF 测量工具**：
   - 使用 Adobe Acrobat 的"测量工具"
   - 或将 PDF 导出为 PNG，使用图像编辑软件测量

3. **直接读取 Word 的 XML**（高级）：
   - 解压 .docx 文件
   - 读取 `word/styles.xml`

### 参数精度要求

- 页面边距：±0.5mm
- 字号：±0.5pt
- 行距：±0.1 倍
- 段间距：±0.5pt
- 颜色：RGB 误差 < 2

## 示例样式参数

```yaml
# Word 2026 青年基金模板样式参数

page:
  width: 210mm  # A4
  height: 297mm  # A4
  margin_top: 2.54cm
  margin_bottom: 2.54cm
  margin_left: 3.17cm
  margin_right: 3.17cm

font:
  chinese: 楷体
  english: Times New Roman
  base_size: 12pt

line_spacing:
  multiplier: 1.5
  exact_pt: null

title_level_1:
  font_size: 15pt
  font_weight: bold
  color: RGB(0, 112, 192)  # MsBlue
  spacing_before: 24pt
  spacing_after: 18pt
  indent: 0

title_level_2:
  font_size: 14pt
  font_weight: bold
  color: RGB(0, 112, 192)
  spacing_before: 18pt
  spacing_after: 12pt
  indent: 0

title_level_3:
  font_size: 13pt
  font_weight: bold
  color: black
  spacing_before: 12pt
  spacing_after: 6pt
  indent: 0

title_level_4:
  font_size: 12pt
  font_weight: normal
  color: black
  format: "（1）"
  indent: 0

list:
  numbering_format: "1.1.1"
  left_indent: 2em
  hanging_indent: 1em
  item_spacing: 0

colors:
  MsBlue: RGB(0, 112, 192)
```
