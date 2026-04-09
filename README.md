# denia-agent-toolkit

一个面向图形与引擎研发的本地 agent 工具集，后续统一收纳 Unity、UE、RenderDoc 等自动化能力。
仓库采用双入口：`server.py` 作为 MCP 入口，`SKILL.md` 作为高层工作流入口；具体动作下沉到 `scripts/` 独立脚本。
当前仓库只完成最小骨架，MCP、Skill 和 Unity Play 脚本均为 TODO 占位。

## 使用

默认使用 `uv` 管理本地 Python 环境，无需手动维护 `venv` 激活状态。

```powershell
git clone git@github.com:YXHXianYu/denia-agent-toolkit.git
cd denia-agent-toolkit

uv venv
uv pip install --python .venv -r requirements.txt
uv run python server.py
uv run python scripts/unity-active-and-play.py
```

当前 `requirements.txt` 仅保留占位说明；后续按真实依赖补充即可。