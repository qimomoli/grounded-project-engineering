# Skill 套件工程化加固

## Why

修复 Skill 套件缺少可执行验证闭环、宿主清单不完整、安装与版本入口依赖手工操作，以及人工 E2E 手册命令过度绑定 Windows `cmd.exe` 的问题。

## What changes

- 增加标准库实现的统一 `gpe` CLI，提供版本、结构校验、测试编排和 Skill 安装入口。
- 增加仓库结构校验与跨平台 GitHub Actions 验证。
- 补齐 `ai-necessity-audit` 的 `agents/openai.yaml`。
- 将 E2E 手册命令规则改为按当前/目标操作系统选择；Windows 继续使用 `cmd.exe`。
- 同步更新本地 `.codex/skills` 中受影响的 E2E Skill 与 AI Necessity 宿主清单。

## Non-goals

- 不改变六个 Skill 的核心判断规则。
- 不修改 `.idea/`、运行时知识、workspace、日志或测试证据。
- 不创建 GitHub Release、Tag、PR、提交或推送。

## Active scope

- `gpe/`
- `tests/`
- `.github/workflows/ci.yml`
- `pyproject.toml`
- `README.md`
- `docs/installation.md`
- `docs/workflow.md`
- `skills/ai-necessity-audit/agents/openai.yaml`
- `skills/manual-e2e-test-handbook/SKILL.md`
- `.gitignore`
- 本地 `.codex/skills` 中本次确认的两个运行时文件

## Acceptance criteria

1. `python -m gpe validate` 检查六个 Skill、frontmatter 和宿主清单，并在当前仓库通过。
2. `python -m gpe test` 可编排现有测试、策略评估和结构校验。
3. `python -m gpe install` 可在显式目标目录安全复制完整 Skill 目录。
4. `python -m gpe --version` 返回单一版本号。
5. CI 在 Windows 与 POSIX runner 上运行上述验证。
6. Windows E2E 手册仍输出 `cmd.exe` 命令；POSIX 目标输出 POSIX shell 命令；不匹配时要求显式目标系统。
7. 仓库与本地已安装 Skill 的受影响文件内容一致；本地无关定制保留。

## Verification plan

- 先新增 CLI 与结构校验测试并确认其在实现前失败。
- 实现 CLI、安装器和结构验证。
- 运行 CLI、两套既有单元测试、策略评估和 diff 检查。
- 检查仓库与本地受影响 Skill 文件的 SHA-256 一致性。

## Flow Record

| Stage | Status | Evidence |
|---|---|---|
| Requirement | Confirmed | User confirmation in current conversation |
| Design | Confirmed | Four-problem repair scope and local sync boundary |
| Development | Complete | `gpe/`, CI, docs, manifest, E2E platform rules, local Skill sync |
| Testing | In Progress | Local Windows verification and wheel/sdist smoke checks pass; GitHub Actions must rerun the Windows matrix before completion |
| Finish | Blocked | The previous CI run failed on Windows; no new commit/push/release performed |
