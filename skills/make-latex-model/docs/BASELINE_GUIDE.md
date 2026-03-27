# PDF 基线制作指南

本指南说明如何为 `make-latex-model` 准备可靠的 PDF baseline。

## 适用范围

可用于：

- NSFC 官方模板对齐
- thesis / paper / cv 的学校、期刊、既有样例 PDF 对齐
- 任意需要像素级或视觉级回归的模板任务

## 基线优先级

推荐按下面的优先级选择：

1. 官方直接提供的 PDF
2. 用 Microsoft Word 导出的 PDF
3. 用 LibreOffice 导出的 PDF
4. 其他可信渲染链路生成的 PDF

如果你需要做像素级比对，尽量不要使用 QuickLook、截图或预览器导出的伪 PDF。

## 方法 1：直接使用官方 PDF

如果用户已经提供：

- 学校官方 PDF
- 期刊官方 PDF
- 既有验收版 PDF
- Release 包里的 baseline PDF

那么它通常就是最好的 baseline，不必再绕回 Word 转 PDF。

## 方法 2：用 Microsoft Word 导出 PDF

### 步骤

1. 打开 Word 模板
2. 选择“文件 -> 导出 -> 创建 PDF”
3. 把导出的 PDF 保存到便于引用的位置

推荐保存方式：

- 项目内长期保留的基线：放到项目自己的 `template/`、`assets/source/`、`tests/baselines/` 等真实目录
- 一次性调试基线：放到本轮测试目录或 `.make_latex_model/` 工作区

## 方法 3：用 LibreOffice 导出 PDF

### 转换命令

```bash
soffice --headless --convert-to pdf --outdir <输出目录> <word-file>
```

例如：

```bash
soffice --headless --convert-to pdf \
  --outdir tests/baselines \
  projects/thesis-nju-master/assets/source/nju_mem_2023_2.docx
```

## 如何检查 PDF 是否靠谱

可以用 `pdfinfo` 看元信息：

```bash
pdfinfo <baseline.pdf>
```

重点关注：

- 页面大小是否正确（通常是 A4）
- 是否存在加密
- Creator / Producer 是否来自可信渲染链路

## 不推荐的做法

- 用 QuickLook 预览截图代替 PDF
- 用预览器的缩略图或截图代替 baseline
- 用不明来源的在线工具处理敏感模板

## 与当前 skill 的关系

基线准备好后，`make-latex-model` 会优先：

1. 判断这次修改该落在 `projects/*` 还是 `packages/bensz-*`
2. 用对应产品线的官方构建脚本验证
3. 仅在需要时再做标题比对、像素比对或参数提取

也就是说，baseline 很重要，但它只决定验收参照物，不决定你必须走哪一套实现路径。
