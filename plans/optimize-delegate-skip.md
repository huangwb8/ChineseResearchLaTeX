# 优化计划：统一委托包安装器的跳过速度

## 背景

根级安装器 `scripts/install.py` 对两种安装模式采用不同策略：

- **texmfhome 模式**（当前仅 `bensz-fonts`）：根级直接处理，先仅下载远程 `package.json`（~1KB）比对版本，命中跳过后立即返回，不下载完整 zip。开销极小。
- **delegate 模式**（`bensz-nsfc`、`bensz-paper`、`bensz-thesis`、`bensz-cv`）：即使最终会跳过，也必须先下载安装器脚本 + 辅助模块（2-3 次 HTTP 请求），再启动子 Python 进程，子进程内才做版本比对。命中跳过时的额外开销明显。

**目标**：让 delegate 模式的四个包在版本匹配时，跳过速度与 bensz-fonts 一致——一次轻量 HTTP 请求即完成。

## 现状分析

### 根级安装器调用链

```
cmd_install()
  ├─ texmfhome → _install_texmf_package()
  │     ├─ _fetch_remote_package_metadata()   # 仅拿 package.json
  │     ├─ should_skip_reinstall()             # 比对版本
  │     ├─ [跳过返回] 或
  │     └─ _download_repo_snapshot() + 复制文件
  │
  └─ delegate → _install_delegated_package()
        ├─ 下载安装器脚本（install.py）
        ├─ 下载辅助模块（package_version_manager.py 等）
        ├─ subprocess.run() 启动子进程
        └─ 子进程内：版本比对 → [跳过] 或 下载 zip + 安装
```

### 可复用的现有基础设施

1. `_fetch_remote_package_metadata(package_name, ref, mirror)`（install.py 约第 527 行）：已能从远程仅抓取 `package.json` 并解析 version
2. `_installed_package_version(package_name, texmfhome_override)`（install.py）：已能读取已安装包的版本
3. `should_skip_reinstall(installed, target, force)`（install.py）：已实现版本比对 + force 覆盖逻辑
4. `SUPPORTED_PACKAGES` 字典（install.py）：每个包的元信息，含 `install_mode`、`installer_path`、`delegate_support_files`

### 约束

- 不能破坏现有的 delegate 子进程安装能力（版本不一致时仍需完整安装流程）
- 不能影响各包自带安装器的独立运行能力（用户可能单独调用各包的 install.py）
- 不能引入新的重复代码，应复用已有函数

## 实施方案

### 改动范围：仅 `scripts/install.py` 一个文件

### 改动步骤

#### 步骤 1：在 `_install_delegated_package` 入口增加前置版本检查

在 `_install_delegated_package` 函数体开头（下载安装器脚本之前），插入与 `_install_texmf_package` 相同的轻量版本检查逻辑：

```python
def _install_delegated_package(
    package_name: str,
    ref: str,
    extra: list[str],
    mirror: str,
    texmfhome: str | None = None,
    force: bool = False,
) -> None:
    # --- 新增：前置版本检查 ---
    remote_metadata_result = _fetch_remote_package_metadata(package_name, ref, mirror)
    if remote_metadata_result is not None:
        remote_metadata, metadata_mirror = remote_metadata_result
        target_version = remote_metadata.get("version")
        installed_version = _installed_package_version(package_name, texmfhome)
        if should_skip_reinstall(installed_version, target_version, force=force):
            print(
                "  ⏭️  检测到已安装相同版本："
                f"{package_name} {installed_version}（ref={ref}, source={metadata_mirror}），跳过重复安装"
            )
            return
    # --- 新增结束 ---

    # 原有逻辑：下载安装器脚本 → subprocess.run() ...
```

#### 步骤 2：提取公共版本检查为独立函数（可选，推荐）

将 `_install_texmf_package` 和 `_install_delegated_package` 中重复的版本检查逻辑提取为一个公共函数：

```python
def _check_skip_reinstall(
    package_name: str,
    ref: str,
    mirror: str,
    texmfhome_override: str | None = None,
    force: bool = False,
) -> bool:
    """检查是否应跳过重复安装。返回 True 表示应跳过。"""
    remote_metadata_result = _fetch_remote_package_metadata(package_name, ref, mirror)
    if remote_metadata_result is None:
        return False
    remote_metadata, metadata_mirror = remote_metadata_result
    target_version = remote_metadata.get("version")
    installed_version = _installed_package_version(package_name, texmfhome_override)
    return should_skip_reinstall(installed_version, target_version, force=force)
```

然后在 `_install_texmf_package` 和 `_install_delegated_package` 中统一调用。

#### 步骤 3：处理远程 metadata 获取失败的降级

当 `_fetch_remote_package_metadata` 返回 `None`（网络异常、远程 package.json 不可达）时，不跳过，继续走完整 delegate 流程。这与 `_install_texmf_package` 现有行为一致——拿不到远程版本就老老实实下载。

## 改动前后对比

### 改动前（delegate 模式，版本一致时）

```
HTTP GET package.json      ← _fetch_remote_package_metadata（无，缺失此步）
HTTP GET install.py        ← 下载安装器脚本
HTTP GET pkg_ver_mgr.py    ← 下载辅助模块
subprocess.run()           ← 启动子进程
  HTTP GET package.json    ← 子进程内版本检查
  [跳过]                   ← 子进程返回
清理临时文件
```

总计：3-4 次 HTTP 请求 + 子进程开销

### 改动后（delegate 模式，版本一致时）

```
HTTP GET package.json      ← 前置版本检查
[跳过]                     ← 命中，直接返回
```

总计：1 次 HTTP 请求，无子进程

### 版本不一致时（无论改不改，都一样）

```
HTTP GET package.json      ← 前置版本检查（版本不匹配，继续）
HTTP GET install.py        ← 下载安装器脚本
HTTP GET pkg_ver_mgr.py    ← 下载辅助模块
subprocess.run()           ← 启动子进程
  HTTP GET package.json    ← 子进程内版本检查（冗余但无害）
  下载 zip + 安装
```

多了一次 package.json 请求，但相对于完整 zip 下载可忽略不计。

## 验证方法

1. **版本一致跳过验证**：先安装一次某包，再执行 `python scripts/install.py install --packages bensz-nsfc`，确认输出直接显示跳过信息，不出现"下载安装器"字样
2. **版本不一致安装验证**：用 `--ref` 指定一个不同版本，确认仍能正常走完完整安装流程
3. **force 覆盖验证**：版本一致时加 `--force`，确认不跳过、正常重装
4. **网络异常降级验证**：断网或指定不存在的 ref，确认降级到 delegate 子进程流程（或报出合理错误）
5. **全包安装验证**：`python scripts/install.py install` 不带 `--packages`，确认所有五个包按依赖顺序正常安装或跳过
6. **texmfhome 模式回归**：确认 bensz-fonts 的 texmfhome 安装路径不受影响

## 风险评估

| 风险 | 可能性 | 影响 | 缓解 |
|------|--------|------|------|
| 远程 package.json 路径与实际不一致 | 低 | 前置检查失效，退化到旧行为 | 现有 `_fetch_remote_package_metadata` 已在各包验证过 |
| 前置检查拿到版本后，子进程内又检查一次造成冗余 | 确定 | 多一次 HTTP 请求（~1KB） | 可接受，不优化也不影响正确性 |
| 子进程内安装器未来可能做更多前置检查逻辑被绕过 | 低 | 仅影响 skip 路径 | 前置检查只管 skip，安装逻辑仍由子进程全权负责 |

## 不做的事情

- 不修改各包自带的 `scripts/package/install.py` 或 `scripts/package_version_manager.py`
- 不改变 `SUPPORTED_PACKAGES` 字典结构
- 不引入新的依赖或配置文件
- 不改变用户可见的命令行接口
