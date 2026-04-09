# denia-agent-toolkit

一个面向图形与引擎研发的本地 agent 工具集，后续统一收纳 Unity、UE、RenderDoc 等自动化能力。
仓库采用双入口：`server.py` 作为 MCP 入口，`SKILL.md` 作为高层工作流入口；具体动作下沉到 `scripts/` 独立脚本。
当前仓库仍然是轻量骨架，但 `scripts/unity-active-and-play.py` 已经具备首版可运行实现。

## 当前状态

- `server.py` 仍然是 MCP 入口占位。
- `SKILL.md` 仍然是高层工作流占位。
- `scripts/unity-active-and-play.py` 已实现 Unity Editor 自动激活、等待空闲、搜索 Play 按钮、点击 Play、以及运行期日志监控。

## 使用

默认使用 `uv` 管理项目环境与依赖，无需手动维护 `venv` 激活状态。

```powershell
git clone git@github.com:YXHXianYu/denia-agent-toolkit.git
cd denia-agent-toolkit

uv venv
uv sync
uv run python server.py
uv run python scripts/unity-active-and-play.py
```

`uv run` 会自动使用项目环境；首次使用前建议显式执行一次 `uv sync`。

## Unity Auto Play

当前的 `unity-active-and-play.py` 按如下流程工作：

1. 查找并激活 Unity Editor 窗口。
2. 监听 Unity `Editor.log`，把它作为错误监控主信号。
3. 轮询 Unity 窗口右下角状态区，把视觉稳定性和疑似红色错误提示作为补充信号。
4. 在顶部工具栏中心区域搜索 Play 按钮的三角形图标。
5. 等待“日志安静 + 状态区稳定 + Play 按钮稳定出现”后再点击 Play。
6. 点击后对按钮局部区域做一次视觉校验，确认状态发生变化。

## 运行示例

```powershell
uv run python scripts/unity-active-and-play.py --debug
```

常用参数：

- `--timeout`：等待编译/导入完成的最长时间。
- `--activation-timeout`：激活 Unity 窗口时的超时时间。
- `--verify-timeout`：点击 Play 后验证状态变化的超时时间。
- `--editor-log`：手动指定 `Editor.log` 路径。
- `--debug`：保存工具栏和右下角状态区截图，便于调试。

## 当前假设与限制

- 当前实现以 Windows 为优先目标。
- 当前验证目标环境是 Unity 2022 LTS、中文界面、Pro-Dark 主题。
- 代码避免直接使用 Win32 API；窗口激活依赖 `PyWinCtl`，输入与截图依赖 `PyAutoGUI` 和 `Pillow`。
- Play 按钮识别采用“顶部工具栏中心区域的三角形启发式搜索 + 几何兜底”，不是 Unity 内部 API 级别的精确状态查询。
- 为了降低误触发风险，建议运行脚本时让 Unity Editor 窗口保持可见，且尽量放在主显示器。

## 依赖管理

本仓库现在使用：

- `pyproject.toml`：声明项目依赖与元数据。
- `uv.lock`：锁定精确依赖版本。

不再维护 `requirements.txt`。