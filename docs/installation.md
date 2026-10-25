# 安装说明

本仓库是一个由六个 Skill 组成的整体套件。建议完整获取仓库，再按目标 Agent 的 Skill 发现机制安装六个子目录。

## 套件内容

```text
skills/
├─ ai-necessity-audit/
├─ avoiding-project-pitfalls/
├─ confirm-before-work/
├─ evidence-discipline/
├─ grounding-project-knowledge/
└─ manual-e2e-test-handbook/
```

不要只复制某一个 `SKILL.md`：部分 Skill 需要同目录下的 `agents/`、`references/`、`scripts/` 或 `evals/`。

## 安装原则

1. 保持每个 Skill 的目录名不变。
2. 将每个完整 Skill 目录复制到目标宿主支持的 Skill 根目录。
3. 保留该 Skill 的配套目录；不要只复制入口文件。
4. 安装后重新加载宿主的 Skill 列表，再通过 Skill 名称验证发现结果。

不同 Agent 宿主的安装目录可能不同。不要把本机绝对路径写进仓库或安装脚本；安装路径应由使用者根据宿主配置决定。

## 运行时资料

以下内容属于本地运行时资料，不应从其他项目复制到本仓库：

- `knowledge/`：项目知识和避坑记录；
- `workspace/`：本地测试手册、运行状态和经验；
- `runs/`、`evidence/`、日志、视频和数据库导出；
- 任何凭据、Token、个人信息、客户资料、生产数据或内部地址。

这些资料应保留在本地 Skill workspace，并遵守对应 Skill 的授权和脱敏规则。仓库中的 `.gitignore` 已排除常见运行时目录和敏感文件类型。

## 更新套件

更新时替换完整的六个 Skill 目录，并检查：

- `SKILL.md` 的 frontmatter 是否完整；
- `agents/openai.yaml` 是否仍与 Skill 名称一致；
- 配套 `references/`、`scripts/` 和 `evals/` 是否完整；
- 本地运行时资料是否未被纳入 Git；
- 变更是否通过仓库提供的脚本测试和策略评估。

不要用运行时生成的项目数据覆盖静态 Skill 文件，也不要把单个项目的修复经验直接写成跨项目规则。

## 验证

仓库维护者应至少运行：

- `grounding-project-knowledge` 的脚本测试；
- `avoiding-project-pitfalls` 的脚本测试；
- `confirm-before-work` 的策略评估；
- 敏感信息扫描和 `git diff --check`。

测试命令和 Python 路径由本地环境决定，不在文档中固定个人机器路径。
