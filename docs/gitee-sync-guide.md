# GitHub 最新 Commit 自动同步到 Gitee 指南

本文面向仓库维护者，说明如何在 **GitHub 默认分支出现新 commit 时**，自动把最新状态推送到 Gitee 镜像仓库，并通过定时巡检补偿偶发漏触发场景。

当前自动化入口：

- GitHub Actions 工作流：[.github/workflows/sync-gitee-mirror.yml](../.github/workflows/sync-gitee-mirror.yml)
- 同步脚本：[scripts/sync_gitee_mirror.py](../scripts/sync_gitee_mirror.py)

## 同步内容

当 GitHub 默认分支有新的 commit，或定时巡检发现 Gitee 落后时，工作流会自动：

- 将当前默认分支的最新提交推送到 Gitee 对应分支
- 推送后比对 GitHub / Gitee 两端分支 commit，只有完全一致才视为成功

只有在手动触发 `workflow_dispatch` 且显式填写 `tag` 时，工作流才会顺带同步该 tag。

这条链路的目标是“自动同步仓库状态到 Gitee 镜像”，不是在 Gitee 上额外创建 Release 页面或上传 Release Assets。

## 生效前提

要让自动化真正生效，至少满足以下条件：

1. 当前仓库已经把同步脚本和工作流提交到 GitHub 默认分支。
2. Gitee 上已经存在目标仓库，并且你拥有写权限。
3. GitHub Actions 已配置可写入 Gitee 的认证信息。

## 一次性配置步骤

### 1. 提交并推送自动化文件

确认以下文件已经进入 GitHub 默认分支：

- [.github/workflows/sync-gitee-mirror.yml](../.github/workflows/sync-gitee-mirror.yml)
- [scripts/sync_gitee_mirror.py](../scripts/sync_gitee_mirror.py)
- [scripts/test_sync_gitee_mirror.py](../scripts/test_sync_gitee_mirror.py)

如果这些文件还只在本地，先正常 `git add`、`git commit`、`git push`。

### 2. 在 Gitee 准备目标仓库

例如：

```text
huangwb8/ChineseResearchLaTeX
```

后文把它称为“Gitee 镜像仓库”。

### 3. 生成专用于 GitHub Actions 的 SSH 密钥

建议不要复用日常开发机器的主密钥，而是单独生成一对自动化专用密钥。

重要限制：

- **当前这条自动化链路不能使用带 passphrase 的私钥**
- GitHub Actions 在 `webfactory/ssh-agent` 这一步无法交互式输入口令
- 如果私钥带口令，工作流会在 `Start SSH agent` 阶段直接失败

因此，这里应显式生成一把**不带 passphrase** 的专用密钥：

```bash
ssh-keygen -t ed25519 -C "github-actions-gitee-sync" -f ~/.ssh/gitee_github_actions -N ""
```

生成后会得到两份文件：

- 私钥：`~/.ssh/gitee_github_actions`
- 公钥：`~/.ssh/gitee_github_actions.pub`

### 4. 把公钥加到 Gitee

把 `~/.ssh/gitee_github_actions.pub` 的内容加入 Gitee。

常见做法有两种，任选其一：

- 加到拥有该仓库写权限的 Gitee 账号 SSH 公钥中
- 加到目标仓库可写的 Deploy Key 中

只要最终结果是：这把私钥能够 `git push` 到目标 Gitee 仓库即可。

### 5. 在 GitHub 仓库配置 Secret

进入：

```text
GitHub 仓库 -> Settings -> Secrets and variables -> Actions
```

新建 Repository secret：

- `GITEE_SSH_PRIVATE_KEY`

它的值填写 `~/.ssh/gitee_github_actions` 私钥全文。

注意：

- 要粘贴完整私钥内容，包括开头和结尾行
- 不要填 `.pub` 公钥内容
- 这里填入的私钥必须是**不带 passphrase** 的版本，否则工作流会在加载 SSH key 时失败

### 6. 在 GitHub 仓库配置 Variable

同样进入：

```text
GitHub 仓库 -> Settings -> Secrets and variables -> Actions
```

至少配置以下二选一：

方案 A，推荐：

- `GITEE_REPO`：例如 `huangwb8/ChineseResearchLaTeX`

方案 B：

- `GITEE_REMOTE_URL`：例如 `git@gitee.com:huangwb8/ChineseResearchLaTeX.git`

说明：

- 如果你只配置 `GITEE_REPO`，脚本会自动拼出默认 SSH remote URL
- 如果你的 Gitee 地址不是标准形式，或想显式固定 remote，可直接配置 `GITEE_REMOTE_URL`

## 首次验证

推荐先手动跑一次工作流，确认配置无误，而不是等下次默认分支更新时再发现问题。

进入 GitHub：

```text
Actions -> Sync Gitee Mirror -> Run workflow
```

默认参数说明：

- `branch`：默认同步默认分支，通常是 `main`
- `tag`：默认留空；只有需要手动补推某个 tag 时才填写
- `dry_run`：`true` 时只打印计划，不真正推送；首次排查时可先用它

建议验证顺序：

1. 先运行一次 `dry_run=true`
2. 再运行一次真实同步
3. 到 Gitee 检查目标分支是否已更新到和 GitHub 同一 commit

## 日常使用方式

完成一次性配置后，后续只需要照常向默认分支推送 commit。

默认情况下：

- `push` 到 `main` 时会立即触发 [sync-gitee-mirror.yml](../.github/workflows/sync-gitee-mirror.yml)
- 工作流还会每小时自动巡检一次，发现 Gitee 落后时补推
- 工作流会执行 [scripts/sync_gitee_mirror.py](../scripts/sync_gitee_mirror.py)
- 默认分支最新状态会被推到 Gitee，并在推送后做远端 commit 校验

换句话说，日常维护流程不需要再手动登录 Gitee 执行“拉取 GitHub 仓库”的操作。

## 失败排查

如果工作流没有按预期生效，优先检查下面几项。

### 1. 缺少认证信息

典型报错：

```text
Missing secret: GITEE_SSH_PRIVATE_KEY
```

处理方式：

- 检查 GitHub Actions Secret 是否已配置
- 检查私钥内容是否完整

### 2. 没有配置目标仓库

典型报错：

```text
Missing repository target: configure GITEE_REPO or GITEE_REMOTE_URL
```

处理方式：

- 配置 `GITEE_REPO`
- 或配置 `GITEE_REMOTE_URL`

### 3. SSH 公钥没有真正获得写权限

典型表现：

- 工作流能连上 Gitee，但 `git push` 被拒绝

处理方式：

- 确认公钥绑定到了正确的 Gitee 账号或正确的仓库
- 确认该账号或 Deploy Key 具备目标仓库写权限

### 4. 私钥带有 passphrase

典型报错：

```text
Command failed: ssh-add -
Enter passphrase for (stdin):
```

处理方式：

- 不要把带口令的私钥直接存入 `GITEE_SSH_PRIVATE_KEY`
- 重新生成一把**不带 passphrase** 的自动化专用 SSH key
- 把新的公钥重新加到 Gitee
- 用新的无口令私钥覆盖 GitHub 中的 `GITEE_SSH_PRIVATE_KEY`

### 5. 这次没有进入默认分支

当前工作流触发条件是：

```yaml
on:
  push:
    branches:
      - main
  schedule:
    - cron: "17 * * * *"
```

处理方式：

- 确认目标提交已经进入默认分支 `main`
- 或等待下一次定时巡检
- 如需立即补推，可手动触发 `workflow_dispatch`

### 6. 历史 Release 不会自动补跑

如果这套自动化是在若干个 Release 之后才加上的，那么旧 Release 不会自动重新触发。

处理方式：

- 手动运行一次 `Sync Gitee Mirror` workflow

## 建议的最小维护流程

推荐把维护动作固定为以下顺序：

1. 提交并推送代码到 GitHub 默认分支
2. 等待 `Sync Gitee Mirror` workflow 成功
3. 如需确认，到 Gitee 检查分支 commit 是否同步
4. 只有需要补推 tag 时，再手动触发 `workflow_dispatch` 并填写 `tag`

这样就能把“GitHub 为源站、Gitee 为镜像”的维护动作稳定固定下来。
