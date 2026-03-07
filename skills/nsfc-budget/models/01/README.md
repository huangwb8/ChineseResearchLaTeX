# Budget Justification

基于 `projects/NSFC_Young` 的项目骨架整理的“国家自然科学基金项目预算说明书”LaTeX 模板。

## 基准来源

- 官方基准 PDF：`template/国家自然科学基金项目项目预算说明书（除重大项目、国家重大科研仪器研制项目以外）.pdf`
- 对齐副本：`template/baseline.pdf`

## 目录说明

- `budget.tex`：主模板文件
- `extraTex/@config.tex`：页面、字体、标题等样式配置
- `extraTex/*.tex`：各预算科目的可编辑内容区

## 编译

```bash
cd skills/nsfc-budget/models/01
xelatex budget.tex
```

当前 `template/baseline.pdf` 仅作为 `make_latex_model` 的样式对齐基准；最终交付仍为可编辑的 LaTeX 模板与其编译得到的 `budget.pdf`。

## 使用方式

- 直接编辑各 `extraTex/*.tex` 文件，替换默认空白占位区域
- 若仅需保留空模板样式，可不修改占位文件内容
