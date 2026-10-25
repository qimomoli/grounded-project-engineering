---
name: ai-necessity-audit
description: Use when reviewing an AI feature, product proposal, release note, workflow, or business idea for real user need, AI necessity, pseudo-innovation, AI rebranding, hidden process complexity, or agent risk.
---

# AI Necessity Audit

Use this skill to judge the necessity and substance of AI in a proposed product, feature, workflow, or business plan. The goal is not to praise or attack AI. The goal is to determine whether AI creates material value after comparing it with the current state and the strongest credible non-AI alternative.

## First-Principles Requirement

First-principles reasoning is mandatory. Do not begin with the proposed AI feature, model, vendor, or marketing claim. Begin with the outcome that must exist even if the feature, product, and AI label are removed.

Reduce the proposal in this order:

1. **Minimum useful outcome**: State the smallest observable result the user or business actually needs, using an outcome verb such as submit, decide, find, classify, repair, or complete.
2. **Necessary operations**: Decompose that outcome into only the operations that must happen. Mark convenience, presentation, and status-signaling steps as non-essential unless evidence shows otherwise.
3. **Real constraints**: Identify the facts that make the task difficult, such as unstructured input, missing information, ambiguity, scale, latency, safety, or a need for judgment. Separate real constraints from poor interface design, bad data, weak search, unnecessary approvals, or organizational habits.
4. **Cheapest sufficient mechanism**: For each necessary operation, test removal, process redesign, better UI, validation, rules, formulas, database queries, search, conventional automation, and targeted human review before AI.
5. **Irreducible AI contribution**: Name the exact operation that AI performs better and why a simpler mechanism cannot meet the required outcome. If removing AI leaves the outcome and quality essentially unchanged, AI is not necessary.
6. **Counterfactual comparison**: Compare the same user, data, constraints, budget, and success criteria with and without AI. Derive the verdict from the difference, not from the presence of an AI feature.

Do not use "AI is capable of doing this" as a first-principles argument. Capability is not necessity. The question is whether the underlying problem requires probabilistic interpretation or generation after simpler causes of difficulty have been removed.

## Scope and Unit of Analysis

First decide whether the input describes:

- **One atomic capability**: evaluate it directly.
- **A composite product, release, or feature list**: split it into independently judgeable capability units before making an overall judgment.

For a composite input, evaluate each unit separately, then summarize the portfolio. Do not let legitimate AI value in one feature validate unrelated platform, security, collaboration, or marketing claims. Do not let one weak feature invalidate the entire product.

## Core Standard

Always separate these questions:

1. Is there a real user or business problem?
2. Does the current workflow actually fail or cost too much?
3. Does AI solve the problem better than rules, search, templates, scripts, conventional automation, or human work?
4. Are the gains large enough to justify model cost, latency, uncertainty, verification, privacy risk, integration work, and operational complexity?
5. Is the proposal genuinely new, or is an existing capability being renamed as AI?

Do not treat "AI can help" as evidence that "AI is necessary." A proposal must show meaningful incremental value over both the current state and a credible non-AI baseline.

## Four Independent Judgments

These are different dimensions. Report all four instead of forcing them into one mutually exclusive label.

### 1. Problem Reality

Choose one:

- **Real**: a material user or business problem exists.
- **Weak**: the problem exists but is infrequent, low-impact, or poorly evidenced.
- **Self-created**: the proposed feature mainly compensates for an avoidable process, data, or interface defect.
- **Unknown**: essential demand or impact evidence is missing.

### 2. AI Necessity

Choose one:

- **Necessary**: AI provides material value that simpler mechanisms cannot provide at acceptable cost and risk.
- **Useful but not necessary**: AI may improve the experience, but most value comes from process, information architecture, search, rules, or automation.
- **Unnecessary**: the problem is weak, or a simpler mechanism already solves it adequately.
- **Unknown**: the AI contribution or baseline is too underspecified to judge.

### 3. Innovation Substance

Choose one:

- **Capability innovation**: users can accomplish something materially new or previously impractical.
- **Process innovation**: the workflow becomes materially shorter, more reliable, or more accessible.
- **Integration innovation**: existing capabilities are combined in a way that creates a defensible new outcome.
- **Packaging innovation**: distribution, interface, or positioning improves adoption without a fundamentally new capability.
- **No meaningful innovation**: the feature is mainly a renamed or repackaged existing capability.
- **Unknown**: novelty cannot be judged from the available evidence.

### 4. Cost and Risk

Choose one:

- **Acceptable**: expected gains clearly outweigh implementation, operation, review, governance, and failure costs.
- **Borderline**: the benefit may be real, but costs, error handling, or governance are not yet justified.
- **Unacceptable**: complexity, risk, or operational burden outweighs the likely gain.
- **Unknown**: material cost or risk information is missing.

After these four judgments, give one **decision recommendation**:

- **Keep and expand AI**
- **Keep AI but narrow its scope**
- **Prefer the non-AI solution**
- **Fix the underlying workflow first**
- **Run a bounded experiment**
- **Reject or defer**

### Legacy Diagnostic Tags

Use these as tags, not as substitutes for the four judgments:

- **Pseudo-need**: the problem is weak, self-created, or not worth solving.
- **Pseudo-innovation**: the claimed innovation does not materially change outcomes or capabilities.
- **AI rebranding**: the AI label materially exceeds the demonstrated AI contribution.

Only mark **AI rebranding: yes** when all of these are supported:

1. The core mechanism and user outcome remain substantially unchanged.
2. The AI label is more prominent than the measurable AI contribution.
3. The material claims rely mainly on model, Agent, or intelligence language without outcome evidence.
4. Removing the AI label leaves the feature description and value proposition essentially intact.

If product positioning looks inflated but motive is unproven, write **"存在贴牌表现，但动机证据不足"** rather than asserting intent.

## Required Reasoning Process

### Step 1: Establish scope and evidence status

State whether the input is atomic or composite. For each material claim, classify the evidence as:

- **Measured result**: a baseline, sample, metric, and comparison are available.
- **User evidence**: concrete user feedback or observed usage exists, but measurement is incomplete.
- **Product claim**: a release note, PRD, demo, press statement, or vendor claim.
- **Inference**: a conclusion derived from the described mechanism.
- **Unknown**: no usable evidence is provided.

Treat release notes, launch copy, and demos as product claims by default, not as proof of user value.

### Step 2: Reduce the proposal to first principles

Write down the minimum useful outcome, the necessary operations, the real constraints, the cheapest sufficient mechanism, and the irreducible AI contribution. Use the six-part reduction in **First-Principles Requirement**. Do not accept "AI assistant," "intelligent diagnosis," or similar labels as problem statements.

### Step 3: State the proposal neutrally

Restate what the feature or product does in one or two sentences after stripping promotional language. Do not repeat claims such as "intelligent," "revolutionary," or "next-generation" unless analyzing those claims.

### Step 4: Compare three states

Compare the same users, data, constraints, budget, and success criteria across:

1. **Current state**: what happens if nothing changes, including existing time, errors, and friction.
2. **Best non-AI option**: remove unnecessary steps, redesign the process, improve the UI or data, then use validation, rules, formulas, search, templates, conventional automation, or targeted human review.
3. **Proposed AI option**: include model cost, latency, review, integration, governance, and failure recovery.

Never compare AI against an intentionally bad baseline. If any state is missing, mark the assumption and explain how it affects confidence.

### Step 5: Test the actual pain

Assess:

- Who experiences the problem?
- How often does it occur?
- What does it cost in time, money, errors, delays, or missed opportunities?
- Is the pain caused by missing intelligence, or by poor process, bad data, weak search, or unnecessary steps?
- What evidence would show that users want the proposed change?

If the pain is not quantified, say so. Do not invent demand.

### Step 6: Identify AI-specific value

Credit AI only for capabilities that depend on its distinctive strengths, such as interpreting unstructured inputs, generating useful drafts, matching ambiguous requests to information, adapting to varied context, or handling long-tail cases.

Do not credit AI for:

- A faster button click caused by a redesigned interface.
- A fixed mapping that rules or a database query can perform.
- A workflow improvement that does not require a model.
- Output that users must completely verify or rewrite.
- A demo that works only on ideal examples.

### Step 7: Apply Agent and tool-use safeguards

Apply this step whenever the proposal includes Agents, MCP, connectors, local files, command execution, document editing, automatic sending, external side effects, or multi-step tool use.

Check:

- **Action scope**: read-only, reversible write, irreversible write, or external communication.
- **Authority**: what data, files, systems, and permissions can the Agent access?
- **Confirmation**: which actions require explicit user approval before execution?
- **Auditability**: are tool calls, files changed, messages sent, and decisions logged?
- **Recovery**: can the action be undone, rolled back, or safely resumed after partial failure?
- **Failure boundary**: does the Agent stop clearly when confidence, permissions, or required information is insufficient?
- **Data safety**: are sensitive files, credentials, prompts, and outputs protected?

Default rule: read-only exploration may be automated; external communication, high-privilege access, destructive changes, sensitive-file handling, and irreversible actions require explicit confirmation or a narrowly defined policy exception. Capability to execute an action is not evidence that autonomous execution is valuable.

### Step 8: Account for AI costs and failure modes

Evaluate:

- Accuracy and consistency.
- False positives and false negatives.
- Review and correction effort.
- Latency and availability.
- Inference and integration cost.
- Privacy, security, and data-retention concerns.
- Explainability and auditability.
- Vendor or model dependency.
- User trust and the cost of a wrong answer.

For high-risk workflows, require a much stronger benefit and an explicit fallback path.

### Step 9: Test novelty separately from usefulness

A feature can be useful without being innovative. A feature can be novel without being useful. Judge both:

- Is there a new capability or only a new label?
- Does the proposed method change what users can accomplish?
- Is the novelty defensible, or can an incumbent product copy it with ordinary automation?
- Does the innovation survive removal of the AI branding?

### Step 10: Deliver a decisive verdict

Report the four independent judgments and one decision recommendation. Do not end with "it depends" unless the proposal genuinely lacks essential facts. When facts are missing, give a provisional judgment based on explicit assumptions and name the exact evidence that could change it.

Use confidence levels:

- **High**: The baseline and outcome are clear, and the evidence strongly supports the verdict.
- **Medium**: The mechanism is clear but demand, metrics, or operating constraints are uncertain.
- **Low**: The proposal is underspecified; the verdict is provisional.

## Two-Sided Evidence, One-Sided Decision

Be fair before being decisive:

- Present the strongest case for introducing AI.
- Present the strongest case against introducing AI.
- Compare both cases against the baseline.
- Decide which case is stronger and why.

Do not manufacture balance by assigning equal weight to weak and strong evidence. "Both sides have merit" is not a conclusion.

## Default Output Format

Unless the user requests another format, answer in Chinese using a concise structure. The default answer should be decisive and readable, usually about 20-35 lines. Preserve the verdict, first-principles reasoning, diagnostic tags, and action recommendation; compress supporting evidence instead of expanding every audit dimension.

### 结论

Use this shape:

- `问题真实性：<真实/弱/人为制造/未知>`
- `AI 必要性：<必须/有益但非必要/不需要/未知>`
- `创新实质：<能力创新/流程创新/整合创新/包装创新/无实质创新/未知>`
- `成本与风险：<可接受/临界/不可接受/未知>`
- `建议：<保留并扩大 AI/保留但缩小范围/优先非 AI/先修流程/有限实验/拒绝或暂缓>`
- `置信度：<高/中/低>`

一句话：<直接说明为什么，不要写空泛套话>

### 第一性原理

- `最小目标：<用户真正需要的可观察结果>`
- `必要步骤：<完成目标必须发生的关键步骤>`
- `非 AI 基线：<最便宜且足够的非 AI 机制>`
- `AI 增量：<AI 具体多解决了什么；若没有则写“没有明确增量”>`

### 判断依据

- `支持保留 AI：<最强的 1-3 个具体理由>`
- `反对/收缩理由：<最强的 1-3 个具体理由>`

If Agent, MCP, local files, command execution, document editing, automatic sending, or external side effects are present, include one compact safety line:

- `安全边界：<必须确认的动作 / 不应自动执行的动作 / 主要误用风险>`

### 伪需求 / 伪创新 / AI 贴牌

- `伪需求：<是/否/证据不足>，<一句原因>`
- `伪创新：<是/否/证据不足>，<一句原因>`
- `AI 贴牌：<是/否/证据不足>，<一句原因>`

### 建议

Give one clear action recommendation in 1-3 sentences. Include 2-3 verification metrics or evidence gates only when they materially affect the decision.

## Detailed Output Format

Use the detailed format only when the user asks for "详细", "完整审计", "展开", "full audit", "deep analysis", or a similar request. Expand the concise answer with the sections needed for the case:

- 第一性原理完整拆解: minimum useful outcome, necessary operations, real constraints, cheapest sufficient mechanism, irreducible AI contribution, and no-AI counterfactual.
- 证据分层: measured result, user evidence, product claim, inference, and unknown.
- 三状态比较: current state, best non-AI option, and proposed AI option.
- 不用 AI 的基线: whether the non-AI option solves most of the problem and what gap remains.
- 支持引入 AI 的理由 and 反对引入 AI 的理由: strongest concrete cases, not generic claims.
- Agent 与安全边界: allowed actions, actions requiring confirmation, permissions, sensitive-data boundaries, logging, rollback, and unsafe failure mode.
- 关键假设 and 什么证据会改变结论.
- 验证指标: 2-5 metrics such as completion time, error rate, correction rate, adoption, cost per task, escalation rate, or successful outcome rate. Include comparison against the non-AI baseline and a stop condition.

## Evidence Discipline

- Distinguish observed facts, user claims, assumptions, and inferences.
- Treat release notes, marketing copy, demos, and model capability statements as product claims unless independent outcome evidence is provided.
- Do not infer demand from a demo, press release, executive enthusiasm, or model capability.
- Do not infer value from token count, number of AI calls, or feature count.
- For composite inputs, do not generalize from one feature to the whole product.
- For Agent actions, do not treat execution capability as proof of value or permission.
- If the proposal lacks baseline data, say the verdict is based on assumptions.
- Ask for more information only when it could materially change the verdict. Otherwise proceed with a provisional judgment.
- When the user asks for a quick opinion, preserve the primary verdict and compress the evidence rather than becoming vague.

## Common Traps

Reject these arguments unless supported by outcome evidence:

- "Everyone is adding AI, so we must."
- "The model can do it, so users need it."
- "It is more innovative because it uses a larger model."
- "Automation is bad only because it is not AI."
- "The user can always check the answer."
- "The demo feels impressive."
- "It saves time" without specifying whose time, how much, and compared with what.

The best answer may be: the problem is real, but the proposed AI solution is the wrong tool. State that directly.


