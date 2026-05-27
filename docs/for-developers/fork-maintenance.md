# Fork 维护说明

本文记录 `Tenstu/ChineseResearchLaTeX` fork 相对上游需要长期保留的 CI 适配。合并 `huangwb8/ChineseResearchLaTeX` 上游变更时，不要直接用上游文件整体覆盖这些配置。

## 需要保留的 CI 适配

### README 模板列表同步

文件：`.github/workflows/update-template-list.yml`

- `TARGET_REPO` 默认值必须保持为 `huangwb8/ChineseResearchLaTeX`。
- `actions/checkout` 使用 `@v6`。
- `actions/setup-python` 使用 `@v6`。

原因：`Tenstu/ChineseResearchLaTeX` fork 不一定发布 Release；定时任务如果默认读取 `github.repository` 的 latest Release，会在 fork 没有 Release 时得到 `HTTP 404 Not Found`。

### Gitee 镜像同步

文件：`.github/workflows/sync-gitee-mirror.yml`

- 未设置 `GITEE_REPO` 且未设置 `GITEE_REMOTE_URL` 时，workflow 必须输出 notice 并成功跳过同步。
- 未设置 `GITEE_SSH_PRIVATE_KEY` 时，非 dry-run 同步必须输出 notice 并成功跳过同步。
- `actions/checkout` 使用 `@v6`。
- `actions/setup-python` 使用 `@v6`。
- `webfactory/ssh-agent` 使用 `@v0.10.0`。

原因：fork 默认可以不配置 Gitee 镜像。未配置镜像时反复让 push / schedule 失败会制造噪声；真正需要同步到 Gitee 的仓库再配置对应 secret 和 variable。

## 合并上游后的检查

合并上游后运行：

```bash
python -m pytest -q scripts/test_fork_ci_adaptations.py
```

该测试会检查上述关键字段是否仍存在。若失败，优先恢复 fork 适配，而不是直接接受上游 workflow 的默认值。

## 恢复方式

建议保留一个恢复分支：

```bash
git push origin main:keep/fork-ci-adaptations
```

如果后续误覆盖，可从该分支查找或 cherry-pick fork 维护提交。
