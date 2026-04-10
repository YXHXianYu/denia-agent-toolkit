# denia-agent-toolkit

> 达妮娅(Denia)可爱捏😋😋

一个面向图形与引擎研发的本地 agent 工具集

功能涵盖：Unity、UE、RenderDoc

使用方式支持：直接运行python脚本、Skill、MCP

## 环境

默认使用 `uv` 管理项目环境与依赖。

```powershell
# 进入你的项目目录
git clone git@github.com:YXHXianYu/denia-agent-toolkit.git .claude/skills/

cd .claude/skills/denia-agent-toolkit
uv venv
uv sync
```

### Unity Auto Play

功能包括：
- 自动唤起窗口、等待编译、完成后最小化窗口
- 进入与退出Play模式
- 自动截图Scene/Game，并打印截图保存路径
- 自动捕获日志
- 自动点击RenderDoc截帧按钮

```powershell
# 当前目录是 .claude/skills/denia-agent-toolkit
uv run python scripts/unity-auto-play.py

# 当前目录是宿主项目根目录
uv run python .claude/skills/denia-agent-toolkit/scripts/unity-auto-play.py

# 如果需要点击RenderDoc截帧按钮，可以添加 --renderdoc-capture
# 如果要查看完整运行十日至，可以添加 -v / --verbose
```

输出示例

```
[UnityAutoPlay] Unity已激活
[UnityAutoPlay] Unity已激活
[UnityAutoPlay] 已进入Play
[UnityAutoPlay] RenderDoc已截帧
[UnityAutoPlay] Play后关键日志 10s。因为Editor.log不足以判断具体输出日志是哪些，所以脚本会向前包含5行。如果你发现日志被截断，请调整参数
[UnityAutoPlay][日志 1][x1]
OnRenderImage() possibly didn't write anything to the destination texture!
[UnityAutoPlay] Unity已激活
[UnityAutoPlay] 已停Play
[UnityAutoPlay] 脚本执行完毕, 已最小化Unity, 请回到IDE
```

### MCP Server

当前已实现最小 FastMCP server，封装现有 Unity workflow。

```powershell
# 当前目录是 .claude/skills/denia-agent-toolkit
uv run python server.py
uv run mcp dev server.py

# 当前目录是宿主项目根目录
uv run python .claude/skills/denia-agent-toolkit/server.py
uv run mcp dev .claude/skills/denia-agent-toolkit/server.py
```

## 开发

详细实现约定、行为说明和维护边界见 `AGENTS.md`。
