# denia-agent-toolkit

> 达妮娅可爱捏😋😋

一个面向图形与引擎研发的本地 agent 工具集

功能涵盖：Unity、UE、RenderDoc

使用方式支持：直接运行python脚本、Skill、MCP

## 使用

默认使用 `uv` 管理项目环境与依赖，无需手动维护 `venv` 激活状态。

```powershell
git clone git@github.com:YXHXianYu/denia-agent-toolkit.git
cd denia-agent-toolkit

uv venv
uv sync
uv run python server.py
uv run python scripts/unity-auto-play.py
```

`uv run` 会自动使用项目环境；首次使用前建议显式执行一次 `uv sync`。

### Unity Auto Play

当前的 `unity-auto-play.py` 按如下流程工作：

1. 查找并激活 Unity Editor 窗口；Windows 上如果常规窗口激活失败，会回退到任务栏里的 Unity 运行中应用按钮。
2. 监听 Unity `Editor.log`，把它作为错误监控主信号。
3. 轮询 Unity 窗口右下角状态区，把视觉稳定性和疑似红色错误提示作为补充信号。
4. 在顶部工具栏中心区域搜索 Play 按钮的三角形图标。
5. 等待“日志安静 + 状态区稳定 + Play 按钮稳定出现”后再点击 Play。
6. 点击后对按钮局部区域做一次视觉校验，确认状态发生变化。

### 运行示例

```powershell
uv run python scripts/unity-auto-play.py --debug
```

常用参数：

- `--timeout`：等待编译/导入完成的最长时间。
- `--activation-timeout`：激活 Unity 窗口时的超时时间。
- `--verify-timeout`：点击 Play 后验证状态变化的超时时间。
- `--editor-log`：手动指定 `Editor.log` 路径。
- `--debug`：保存工具栏和右下角状态区截图，便于调试，默认输出到 `logs/unity-auto-play/`。
