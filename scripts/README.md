# Scripts - LaTeX 模板项目脚本

本目录存放用于辅助 LaTeX 模板项目开发和维护的脚本工具。

## 脚本列表

### build_all.py
编译所有项目的主文档（NSFC_Young, NSFC_General, NSFC_Local）。

**用法**：
```bash
python3 scripts/build_all.py
```

### clean_auxiliary.py
清理所有项目的辅助文件（.aux, .log, .out 等）。

**用法**：
```bash
python3 scripts/clean_auxiliary.py
```

### check_references.py
检查参考文献文件的有效性和格式。

**用法**：
```bash
python3 scripts/check_references.py
```

## 添加新脚本

1. 在本目录创建脚本文件
2. 在本 README.md 中添加说明
3. 确保脚本具有可执行权限：`chmod +x scripts/your_script.py`
