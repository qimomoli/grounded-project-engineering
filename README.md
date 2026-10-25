# Grounded Project Engineering

一组面向 AI 辅助项目开发的可验证工程 Skill。它们共同约束需求判断、项目上下文、历史风险、变更授权和本地端到端验证。

## 设计目标

这不是一个把所有规则塞进单一文件的“大 Skill”，而是一个需要整体下载、由宿主按任务相关性自动触发并按职责协同工作的 Skill 集合：

### 轻量级指导

本套 Skill 不是强制接管所有任务的重型流程。在支持隐式调用的宿主中，每个 Skill 都会根据任务相关性按需自动触发；没有匹配场景时不介入。它们提供最小必要的上下文和检查清单，帮助 AI 更稳定、更可验证地工作，同时尽量减少无关规则、额外上下文和流程噪音。

1. `ai-necessity-audit`：判断问题是否真实、AI 是否必要，以及非 AI 基线是什么。
2. `evidence-discipline`：区分事实、用户输入、推断和未知信息。
3. `grounding-project-knowledge`：从当前代码和项目规则恢复可复用的项目事实。
4. `avoiding-project-pitfalls`：将历史踩坑作为检查线索，并重新验证当前代码。
5. `confirm-before-work`：在写文件、改数据、启动服务或发布代码前确认边界。
6. `manual-e2e-test-handbook`：在本地环境完成隔离、链路和回归验证后生成测试手册。

## 推荐协同顺序

```text
需求判断
  -> 证据约束
  -> 项目知识定位
  -> 历史坑位复核
  -> 变更前确认
  -> 实现与验证
  -> 本地 E2E 与回归手册
```

并非每次都需要触发全部 Skill：

- 只有涉及 AI 功能、AI 产品或 Agent 价值判断时才触发 `ai-necessity-audit`。
- 只要任务依赖项目代码、路由、规则、依赖或数据流，就优先触发 `grounding-project-knowledge`。
- 设计、开发、调试、测试或评审中存在历史风险线索时触发 `avoiding-project-pitfalls`。
- 任何可能产生本地或外部副作用的动作都需要 `confirm-before-work`。
- 涉及本地 Docker、跨服务验证或人工测试手册时触发 `manual-e2e-test-handbook`。

## 安装

建议把整个仓库下载，再将 `skills/` 下的六个 Skill 目录整体安装到目标 Agent 的 Skill 根目录。不要只安装其中一个目录，因为：

- Skill 之间共享证据、授权和项目上下文边界；
- `grounding-project-knowledge` 与 `avoiding-project-pitfalls` 依赖配套脚本和 schema；
- `manual-e2e-test-handbook` 依赖 references 中的运行状态、范围清单和手册模板；
- `confirm-before-work` 附带独立评估用例。

安装时只复制静态定义、references、scripts、agents 和 evals。不要把本地运行产生的 `knowledge/`、`workspace/`、日志、视频或测试证据提交到公共仓库。

## CLI 与验证

仓库提供一个只依赖 Python 标准库的 CLI。安装开发入口后，可以使用：

```text
python -m pip install -e .
python -m gpe --version
python -m gpe validate
python -m gpe test
python -m gpe install --source . --target <SKILL_ROOT>
```

`install` 默认拒绝覆盖已有 Skill；需要更新时显式追加 `--force`。CI 会在 Windows 和 POSIX runner 上执行结构校验、测试、策略评估和 whitespace 检查。

## 隐私与安全边界

本仓库不应包含：

- 用户名、个人路径、访问令牌、密码或私钥；
- 业务项目名称、客户数据、生产数据和内部服务地址；
- 未脱敏日志、运行状态、数据库导出、Redis 内容或测试视频。

本仓库的运行时资料应保留在本地 Skill workspace，并由 `.gitignore` 排除。跨项目经验只能保存经过脱敏、可复核且不含业务专用标识的通用结论。

## 目录

- `skills/`：六个可独立触发但建议整体安装的 Skill。
- `docs/workflow.md`：六个 Skill 的协同关系、触发边界和维护流程。
- `docs/installation.md`：跨宿主安装、更新和运行时资料边界。
- `skills/*/references/`：schema、运行状态和手册模板。
- `skills/*/scripts/`：项目知识和避坑记录的校验/维护脚本。
- `skills/*/evals/`：`confirm-before-work` 的策略评估用例。
- `gpe/`：版本、结构校验、测试编排和 Skill 安装 CLI。
- `.github/workflows/ci.yml`：Windows/POSIX 跨平台验证。

## GitHub 仓库文件

- `README.md`：仓库定位、快速入口和公开边界。
- `docs/workflow.md`：Skill 之间的协同关系，不要求每次任务触发全部 Skill。
- `docs/installation.md`：整套安装和升级说明。
- `LICENSE`：MIT 授权文本。

## 当前限制

- 各 Skill 的运行时知识库和测试证据不随仓库分发。
- 某些 Agent 宿主可能需要把六个子目录分别注册到 Skill 根目录。
- 若宿主不支持批量发现 Skill，应按 `docs/installation.md` 注册六个子目录。

