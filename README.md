# denia-agent-toolkit

> 达妮娅(Denia)可爱捏😋😋

一个面向图形与引擎研发的本地 agent 工具集

功能涵盖：Unity、UE、RenderDoc

使用方式支持：直接运行python脚本、Skill、MCP

## 环境

默认使用 `uv` 管理项目环境与依赖。

```powershell
git clone git@github.com:YXHXianYu/denia-agent-toolkit.git
cd denia-agent-toolkit

uv venv
uv sync
uv run python server.py
uv run python scripts/unity-auto-play.py --help
```

### Unity Auto Play

自动激活Unity窗口、等待编译、点击Play、等待10秒捕获日志、去重后打印到终端，并自动关闭Play模式。

```powershell
uv run python scripts/unity-auto-play.py --debug
```

详细实现约定、行为说明和维护边界见 `AGENTS.md`。
