---
name: denia-agent-toolkit
description: "Use this skill when the user wants to use or extend this repository's automation workflow, especially the implemented Unity Editor external automation and its FastMCP wrapper: 激活Unity, 等待编译或导入完成, 点击Play, 观察Editor.log, 去重关键日志, 10秒后自动退出Play, or debug/modify the unity-auto-play and server.py flow. Also use it when deciding whether a task should be handled by the existing local script or the current MCP wrapper. Do not use this skill for Unreal Engine or RenderDoc workflows, because those parts are not implemented in this repository."
user-invocable: true
---

# Denia Agent Toolkit

## Purpose

This skill packages the current workflow knowledge for this repository.

Today, the implemented surfaces are the external Unity workflow in [scripts/unity-auto-play.py](scripts/unity-auto-play.py) and the FastMCP wrapper in [server.py](server.py). There is still no implemented UE or RenderDoc automation yet.

Do not overclaim repo capabilities. If the user asks for UE, RenderDoc, or MCP functionality, treat that as new implementation work rather than an existing ready-to-run feature.

## When To Use This Skill

Use this skill when the request is about one of these tasks:

- Running the existing Unity auto-play workflow.
- Debugging why the Unity auto-play workflow failed.
- Modifying how the Unity auto-play workflow detects idle/compile completion.
- Modifying how Play is entered, observed, logged, or closed.
- Explaining the current external Unity automation strategy in this repository.
- Deciding whether to solve a task with the existing local script or by adding new toolkit capabilities.

Typical trigger phrases include:

- "激活Unity并自动Play"
- "等待Unity编译完成后点击Play"
- "观察Editor.log并输出关键日志"
- "10秒后自动退出Play"
- "unity-auto-play 为什么没工作"
- "should this use the local script or MCP"

## Do Not Use This Skill

Do not use this skill for:

- Unreal Engine automation that is not yet implemented in this repo.
- RenderDoc capture or analysis workflows that are not yet implemented in this repo.
- General Unity gameplay code, shader authoring, or in-project rendering implementation that is unrelated to this toolkit's external automation.

## Current Implemented Surface

### Implemented

- [scripts/unity-auto-play.py](scripts/unity-auto-play.py): external Unity Editor automation on Windows.
- [server.py](server.py): FastMCP server that exposes toolkit status and wraps the Unity auto-play workflow.

### Not Implemented Yet

- UE automation workflow.
- RenderDoc workflow.

## Workflow

When this skill is active, follow this process:

1. Match the user's request against the actually implemented surface.
2. If the request is covered by the Unity workflow, prefer using the existing script before inventing a new flow.
3. If the request requires code changes, read [AGENTS.md](AGENTS.md) first and preserve the repo's conventions.
4. If the request is only about behavior explanation, explain the real implemented heuristics rather than an idealized design.
5. If the request falls outside the implemented surface, say so clearly and treat it as a new feature request.

## Unity Workflow Reference

For the current Unity automation, the expected high-level behavior is:

1. Find and activate the Unity Editor window.
2. Wait until Unity looks idle enough to click Play.
3. Click Play and verify that Play actually entered.
4. Observe `Editor.log` for 10 seconds after entering Play.
5. Extract key log blocks from the lines before `UnityEngine.StackTraceUtility:ExtractStackTrace ()`.
6. Keep at most the nearest `KEY_MESSAGE_LINE_LIMIT` lines per log block, then deduplicate and print them.
7. Automatically stop Play after the observation window.

If `Editor.log` reports an error immediately after clicking Play, describe the real behavior accurately: the script does not abort at once. It still tries to finish Play verification, the 10-second observation window, and automatic stop-Play cleanup before reporting the error.

When explaining "how compile completion is detected", describe the real heuristic:

- `Editor.log` has been quiet for a short window.
- The bottom-right status area is stable for multiple samples.
- The Play button candidate stays stable for multiple samples.

Do not describe this as a Unity internal API signal. It is an external heuristic.

## Tool And Script Selection

Use the existing script as a black-box workflow when the request is already supported.

Preferred commands:

```powershell
# 当前目录是 denia-agent-toolkit 仓库根目录
uv run python scripts/unity-auto-play.py --help
uv run python scripts/unity-auto-play.py --debug

# 当前目录是宿主项目根目录，toolkit 安装在 .claude/skills/denia-agent-toolkit
uv run python .claude/skills/denia-agent-toolkit/scripts/unity-auto-play.py --help
uv run python .claude/skills/denia-agent-toolkit/scripts/unity-auto-play.py --debug
```

If the user asks about MCP routing or tool registration, explain that [server.py](server.py) is implemented as a minimal wrapper server today, and that broader MCP tool coverage is still pending.

## Output Expectations

When using this skill:

- Keep terminal-oriented explanations concise.
- Surface the actual current strategy, not just the outcome.
- Preserve important implementation limits and heuristics.
- Do not hide missing functionality.
- When behavior changes, update [AGENTS.md](AGENTS.md) and the relevant user-facing docs.

## Key References

- [scripts/unity-auto-play.py](scripts/unity-auto-play.py): main implemented workflow.
- [AGENTS.md](AGENTS.md): repo conventions and current behavior contract.
- [README.md](README.md): concise project overview.
- [server.py](server.py): current FastMCP server entry.

## Example Requests

- "帮我直接跑这个仓库里的 Unity auto play。"
- "解释一下它现在是怎么判断 Unity 编译完成的。"
- "把 Play 后 10 秒观察日志再自动退出的逻辑改一下。"
- "判断这个需求应该复用现有脚本，还是该开始做 MCP。"
- "为什么 unity-auto-play 没点到 Play 按钮？"