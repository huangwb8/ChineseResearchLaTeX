# Issue #54 西安电子科技大学本科模板验证

验证日期：2026-10-03。范围为新增 `thesis-xdu-bachelor` 及其所需的构建、安装和打包接口；没有修改既有学校 style/profile、其他产品包或 Skill 源码。

## 新模板

| 检查 | 结果 |
| --- | --- |
| 公共 Python wrapper 构建、项目 wrapper 构建 | 均通过，示例 PDF 21 页，含双面排版所需空白页 |
| 官方安装器安装到隔离 TEXMFHOME 后，标准 ZIP 独立构建 | 通过 |
| Overleaf ZIP 在无仓库公共包、无已安装字体包的隔离环境构建 | 通过 |
| 仓库、标准 ZIP、Overleaf ZIP 的输出比较 | 全部页面在 72 dpi 下像素完全一致 |
| 文献后端、GB/T 7714—2005、引用与交叉引用 | Biber 成功，最终无未解析引用 |
| 中英文各四作者的测试书目、反序数据库 | 正确保留前三位作者与“等”/“et al.”，按首次引用顺序输出 |
| 封面、正文、参考文献页面渲染检查 | 校徽、文字、上标引用和版式正常，无溢出或缺字 |
| 包结构检查 | 通过，固定上游类、源码与许可证齐全 |

当前示例保留 XDUTS 的 Computer Modern 数学字体；日志存在 `cmex` 从 10.53937 pt 到可用尺寸的字体替代提示。封面定高盒子也有 Underfull 提示，已核对对应页面，没有版式溢出。Overleaf 路径改写还会产生 `styles/bensz-thesis` 与原包声明名不同的提示，三种输出的像素比较证明其未改变排版。未声称与尚未提供的学院最新本科 Word 样稿逐页一致。

## 回归

以下定向测试共 **64 项通过**：

```bash
python -m pytest scripts/test_thesis_project_tool.py \
  scripts/test_install_architecture.py \
  scripts/test_update_readme_template_list.py \
  tests/bensz-thesis/test_thesis_docx_tool.py -q
python packages/bensz-thesis/scripts/validate_package.py --skip-compile
```

既有 13 个论文项目均在隔离副本中构建，12 个通过；UCAS 的 wrapper 保持原有成功返回，但其日志仍存在原有 minted/catchfile 错误，不能视为完整代码块渲染通过。江西理工本科、南方医科大学硕士和 UCAS 博士的修改前后输出已逐页比较，像素完全一致。UCAS 缺口通过 `bensz-collect-bugs` 本地脱敏记录，未公开上报；未以本次新模板开发扩大修改其专属构建链路。

## 证据与状态

原始附件、渲染图、安装日志、构建日志、比较结果和测试缓存保存在唯一任务目录 `.bensz-api/task-20261003-2305-issue54/`；公开项目不携带这些原始材料。

标准 ZIP 与 Overleaf ZIP 使用 `scripts/pack_release.py` 的正式打包函数生成并实际解包验证，仍为本地产物，未上传或发布。未创建分支、Git commit 或修改 GitHub issue 状态。BAC 账本记录维护与验证证据。
