# Plan: Auto git commit + push on agent/skill/command updates

## Context

当前每次 Claude Code 更新 agent 配置（`agents/config/`）、skill 文件（`skills/`）或命令/agent 定义（`.claude/agents/`, `.claude/commands/`）后，需要手动 commit 和 push。需要通过 hook 系统自动化这一流程，在 session 结束时自动检测变更并同步到 remote。

## 设计概览

### 触发机制

使用 **SessionEnd** hook（`once: true`，每个 session 结束时触发一次），检查相关路径是否有 git 变更，如果有则自动 commit + push。

### 变更检测范围

检测以下路径在 git 中的变更（modified / added / deleted）：

| 路径 | 说明 |
|------|------|
| `agents/config/` | 项目级 agent 配置文件 |
| `skills/` | 项目级 skill 文件 |
| `.claude/agents/` | Claude Code agent 定义 |
| `.claude/skills/` | Claude Code skill 定义 |
| `.claude/commands/` | Claude Code 命令定义 |
| `.claude/settings.json` | 主设置（含 hooks 配置） |

> `.claude/settings.local.json` 被 gitignore，不纳入检测和提交。

### git 操作

- `git add` 仅上述路径中的变更文件
- `git commit -m "chore: auto-sync agent/skill/command updates"` + `Co-Authored-By: Claude`
- `git push origin main`

## 实现步骤

### Step 1: 创建 auto-git-sync hook 脚本

**文件**: `/team_work/qingyun/chip_design_groq/chip_design_agent/.claude/hooks/scripts/auto_git_sync.sh`

脚本逻辑：
1. 切换到 git 仓库根目录
2. 收集相关路径的变更（用 `git diff --name-only` + `git diff --name-only --cached` + `git ls-files --others --exclude-standard`）
3. 如果检测到变更路径在监控范围内：
   - `git add` 这些路径的变更
   - `git commit`（跳过 hooks: `--no-verify`，避免 hook 递归触发）
   - `git push origin main`（如果 remote 可达，失败不阻断）
4. 如果无变更，静默退出

### Step 2: 注册 SessionEnd hook

**文件**: `/team_work/qingyun/chip_design_groq/chip_design_agent/.claude/settings.json`

在 `SessionEnd` hook 数组中添加第二个条目：
```json
"SessionEnd": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/hooks.py",
        "timeout": 5000,
        "async": true,
        "statusMessage": "SessionEnd"
      }
    ]
  },
  {
    "hooks": [
      {
        "type": "command",
        "command": "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/auto_git_sync.sh",
        "timeout": 30000,
        "async": true,
        "once": true,
        "statusMessage": "Auto git sync"
      }
    ]
  }
]
```

- `async: true` → 不阻塞 session 关闭
- `timeout: 30000` → 给 git push 足够时间（30s）
- 独立 entry，与原 `hooks.py` 不冲突

### Step 3: 使用 `--no-verify` 避免递归

脚本中的 `git commit` 使用 `--no-verify` 避免触发 Claude Code 的 PreToolUse hook。`git push` 不需要特殊参数。

### Step 4: 测试验证

1. 在本地修改一个 agent 配置（如添加注释）
2. 正常退出 Claude Code session
3. 验证 `auto_git_sync.sh` 被触发
4. 验证 commit 已创建并 push 到 remote

## 边界处理

| 问题 | 解决方案 |
|------|---------|
| 无变更 | 脚本检测无变更后静默退出，不创建空 commit |
| git push 失败（网络问题） | 失败不阻断，脚本退出 0 |
| `--no-verify` 安全 | 仅 `git commit` 使用，避免 hook 递归 |
| settings.local.json 被 gitignore | 不纳入 `git add` 范围 |
| remote auth 失败 | push 失败不影响 git add/commit |

## 不采用方案

- **UserPromptSubmit hook**: 粒度太细，每次用户发消息都可能触发，产生过多 commit
- **PostToolUse hook**: 每个工具调用都触发，过度频繁
- **hooks.py 内嵌**: 混合声音系统和 git 逻辑，关注点分离更差

## Verification

1. 脚本正确检测 `agents/config/`、`skills/`、`.claude/agents/`、`.claude/skills/`、`.claude/commands/` 的变更
2. 脚本在无变更时不创建空 commit
3. SessionEnd hook 注册格式正确，与现有 hooks.py 不冲突
4. `--no-verify` 防止了 hook 递归
