---
name: denia-agent-toolkit
description: "Use this skill when the user wants to use or extend this repository's automation workflow, especially the implemented Unity Editor external automation: 激活Unity, 等待编译或导入完成, 点击Play, 观察Editor.log, 去重关键日志, 10秒后自动退出Play, optionally template-match the Unity-window RenderDoc capture button, or debug/modify the unity-auto-play flow. Do not use this skill for Unreal Engine workflows or standalone RenderDoc analysis workflows, because those parts are not implemented in this repository."
user-invocable: true
---

# Denia Agent Toolkit

## Purpose

This skill packages the current workflow knowledge for this repository.

Today, the implemented surface is the external Unity workflow in [scripts/unity-auto-play.py](scripts/unity-auto-play.py). There is still no implemented UE automation or standalone RenderDoc workflow yet.

Do not overclaim repo capabilities. If the user asks for UE, standalone RenderDoc analysis, or any new external integration surface beyond the current script workflow, treat that as new implementation work rather than an existing ready-to-run feature.

## When To Use This Skill

Use this skill when the request is about one of these tasks:

- Running the existing Unity auto-play workflow.
- Running or modifying the optional RenderDoc capture step inside the Unity auto-play workflow.
- Debugging why the Unity auto-play workflow failed.
- Modifying how the Unity auto-play workflow detects idle/compile completion.
- Modifying how Play is entered, observed, logged, or closed.
- Explaining the current external Unity automation strategy in this repository.
- Deciding whether to solve a task with the existing local script or by extending the current toolkit.

Typical trigger phrases include:

- "激活Unity并自动Play"
- "等待Unity编译完成后点击Play"
- "观察Editor.log并输出关键日志"
- "10秒后自动退出Play"
- "unity-auto-play 为什么没工作"
- "should this use the local script or a new integration layer"

## Do Not Use This Skill

Do not use this skill for:

- Unreal Engine automation that is not yet implemented in this repo.
- Standalone RenderDoc capture or analysis workflows that are not yet implemented in this repo.
- General Unity gameplay code, shader authoring, or in-project rendering implementation that is unrelated to this toolkit's external automation.

## Current Implemented Surface

### Implemented

- [scripts/unity-auto-play.py](scripts/unity-auto-play.py): external Unity Editor automation on Windows.
- [scripts/unity-auto-play.py](scripts/unity-auto-play.py): optional RenderDoc capture-button click via Unity-window template matching when `--renderdoc-capture` is enabled.
### Not Implemented Yet

- UE automation workflow.
- Standalone RenderDoc workflow.

## Workflow

When this skill is active, follow this process:

1. Match the user's request against the actually implemented surface.
2. If the request is covered by the Unity workflow, prefer using the existing script before inventing a new flow.
3. If the request requires code changes, read [AGENTS.md](AGENTS.md) first and preserve the repo's conventions.
4. If the request is only about behavior explanation, explain the real implemented detection logic rather than an idealized design.
5. If the request falls outside the implemented surface, say so clearly and treat it as a new feature request.

## Unity Workflow Reference

For the current Unity automation, the expected high-level behavior is:

1. Find and activate the Unity Editor window.
2. Wait until Unity looks idle enough to click Play.
3. Click Play and verify that Play actually entered.
4. Observe `Editor.log` for 10 seconds after entering Play.
5. If `--renderdoc-capture` is enabled, template-match the RenderDoc Capture button shortly before Play stops.
6. Extract key log blocks from the lines before `UnityEngine.StackTraceUtility:ExtractStackTrace ()`.
7. Keep at most the nearest `KEY_MESSAGE_LINE_LIMIT` lines per log block, then deduplicate and print them.
8. Automatically stop Play after the observation window.
9. Best-effort capture a Scene/Game display-window screenshot if that pane can be found, and print the absolute saved path. The default timing is 7 seconds after entering Play, and it is independent from RenderDoc capture timing.
10. Minimize the Unity window after Play exits so the user can return to the IDE.

Today, the Play button uses template matching against `templates/play-button-idle.png` and `templates/play-button-active.png`; RenderDoc Capture uses template matching against `templates/renderdoc-capture-button.png` on the Unity window screenshot. The script also best-effort captures the Scene/Game display window when it can find a matching Unity pane title; the default screenshot timing is 7 seconds after entering Play and is independent from RenderDoc timing. Default output is concise state logging, and `-v`/`--verbose` enables detailed recognition logs.

If `Editor.log` reports an error immediately after clicking Play, describe the real behavior accurately: the script does not abort at once. It still tries to finish Play verification, the 10-second observation window, and automatic stop-Play cleanup before reporting the error.

When explaining "how compile completion is detected", describe the real heuristic:

- `Editor.log` has been quiet for a short window.
- The bottom-right status area is stable for multiple samples.
- The idle Play template candidate stays stable for multiple samples.

Do not describe this as a Unity internal API signal. It is an external heuristic.

## Tool And Script Selection

Use the existing script as a black-box workflow when the request is already supported.

When the toolkit is installed under `.claude/skills/denia-agent-toolkit` inside a host project, prefer switching into that directory first and then running `uv` commands there. Do not keep running `uv run` or `uv sync` from the host-project root unless the user explicitly wants that form.

Preferred commands:

```powershell
# 当前目录是 denia-agent-toolkit 仓库根目录
uv run python scripts/unity-auto-play.py --help
uv run python scripts/unity-auto-play.py
uv run python scripts/unity-auto-play.py --renderdoc-capture -v

# 当前目录是宿主项目根目录，toolkit 安装在 .claude/skills/denia-agent-toolkit
cd .claude/skills/denia-agent-toolkit
uv run python scripts/unity-auto-play.py --help
uv run python scripts/unity-auto-play.py
uv run python scripts/unity-auto-play.py --renderdoc-capture -v
```

If `uv run` fails with a missing-module error such as `ModuleNotFoundError: No module named '...'`, treat that as an environment-sync problem first:

```powershell
cd .claude/skills/denia-agent-toolkit
uv sync
```

Then retry the original `uv run ...` command.

If there is no `.venv` yet, `uv run` will normally create it automatically instead of asking you to create it manually first. The terminal output typically includes lines like:

```text
Using CPython <version>
Creating virtual environment at: .venv
```

If the project has dependencies, it may then continue with install progress output such as `Installing wheels...` before running the script.

If the user asks about adding a new integration layer, explain that the repository currently keeps a single script-first surface and does not maintain an MCP wrapper anymore.

## Output Expectations

When using this skill:

- Keep terminal-oriented explanations concise.
- Surface the actual current strategy, not just the outcome.
- Preserve important implementation limits, matching rules, and heuristics.
- Do not hide missing functionality.
- When behavior changes, update [AGENTS.md](AGENTS.md) and the relevant user-facing docs.

## Key References

- [scripts/unity-auto-play.py](scripts/unity-auto-play.py): main implemented workflow.
- [AGENTS.md](AGENTS.md): repo conventions and current behavior contract.
- [README.md](README.md): concise project overview.
## Example Requests

- "帮我直接跑这个仓库里的 Unity auto play。"
- "解释一下它现在是怎么判断 Unity 编译完成的。"
- "把 Play 后 10 秒观察日志再自动退出的逻辑改一下。"
- "判断这个需求应该复用现有脚本，还是该开始做新的集成层。"
- "为什么 unity-auto-play 没点到 Play 按钮？"