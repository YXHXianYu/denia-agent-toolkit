# AGENTS

这个文件记录 `denia-agent-toolkit` 当前已经落地的实现约定，后续 agent 或维护者应以这里为基线继续演进。

## 项目管理

- 依赖管理采用 `pyproject.toml + uv.lock`。
- 不再维护 `requirements.txt`。
- 新增依赖时优先使用 `uv add <package>`，不要手写改 `uv.lock`。
- 运行脚本和做本地验证时优先使用 `uv run ...`。

## 文档约定

- README.md要尽可能简洁，把详细描述写在AGENTS.md中。

## Unity Auto Play 约定

- `scripts/unity-auto-play.py` 保持为核心单文件实现脚本。
- 脚本职责固定为：激活 Unity Editor、等待空闲、搜索 Play、点击 Play、进入 Play 后继续观察日志、按需触发 RenderDoc 截帧、提取关键日志并去重打印、持续监控错误、退出 Play 后最小化 Unity 窗口。
- 运行时要把核心策略直接打印到终端，文案尽量短，优先输出“当前判断方式”和“当前阶段结果”。
- 错误监控以 Unity `Editor.log` 为主信号，右下角状态区监控为补充信号。
- 如果点击 Play 后立即在 `Editor.log` 中发现错误，当前行为是不立刻中断，而是继续完成 Play 验证、10 秒观察和自动停 Play，再统一把错误作为结果上报。
- 当前默认行为是在确认进入 Play 后继续观察 `Editor.log` 10 秒，并从这段时间内捕获到的新增日志里提取关键日志；当前关键日志定义为 `UnityEngine.StackTraceUtility:ExtractStackTrace ()` 前面的有效消息块，但最多只保留离该标记最近的 5 行，这个限制由脚本顶部的 `KEY_MESSAGE_LINE_LIMIT` 控制；保留 `Debug.Log` 自带的换行和空行，再按这 5 行内容首次出现的顺序聚合统计输出次数；观察结束后自动尝试关闭 Play。
- 如果启用 `--renderdoc-capture`，当前默认行为是在进入 Play 后的观察窗口内，等待到停止 Play 前 1 秒再截帧；按当前默认 10 秒观察期即第 9 秒。按钮直接在 Unity 窗口截图上用模板匹配定位，同时在终端打印计划触发时间、实际开始时间和实际点击时间。
- 当前默认行为是在成功关闭 Play 后，脚本会继续尝试最小化 Unity 窗口，并在终端提示“脚本执行完毕，请回到 IDE”；最小化属于收尾动作，失败时只记录提示，不覆盖主流程结果。
- 调试截图默认输出到 `logs/unity-auto-play/`，不再需要 `--debug` 开关。
- “等待编译完成”当前不是通过 Unity 内部 API 判断，而是通过以下外部信号组合判断：
  - `Editor.log` 在一段时间内没有新增输出。
  - 右下角状态区连续多个采样保持稳定。
  - 顶部工具栏的 Play 普通态模板候选连续稳定出现。

## MCP Server 约定

- `server.py` 当前已落地为最小 FastMCP server。
- 当前 MCP 工具只封装已有 Unity 能力，不要在 MCP 层再复制一套独立的 Unity UI 自动化实现。
- 当前已提供的工具名为：`toolkit_status`、`unity_auto_play_help`、`unity_auto_play_run`。
- 当前默认传输为 stdio；`streamable-http` 只作为调试或集成时的可选运行方式。
- 如果后续新增 MCP 工具，优先复用现有脚本或明确的工作流 helper，避免把复杂 UI 逻辑分散到多个入口。
- 如果 MCP 能力边界、工具名或运行方式发生变化，必须同时更新 `README.md`、`AGENTS.md` 和 `SKILL.md`。

## 技术选择

- 不直接使用 Win32 API，也不要在这个脚本里手写 `pywin32` 级别调用。
- 窗口激活优先使用 `PyWinCtl`，不要把 `PyAutoGUI` 当成首选窗口管理方案。
- 窗口所属应用名优先通过进程 PID + `psutil` 获取，不再调用 `PyWinCtl.getAppName()`，避免在 Windows 上卡进 WMI 查询。
- Windows 上如果 `PyWinCtl` 常规激活失败，可回退到 `pywinauto` 的 UI Automation 路径，点击任务栏里的 Unity 运行中应用按钮；这属于高层外部自动化兜底，不是手写 Win32。
- Unity 窗口筛选优先参考窗口所属应用名，不要只根据标题里是否包含 `Unity` 判断，否则项目名或路径里带 `Unity` 时容易误选到 VS Code。
- 窗口尚未确认切到前台前，不要通过屏幕坐标盲点标题栏，否则可能误点到 VS Code 或其他前台程序。
- 输入和点击当前使用 `PyAutoGUI`。
- 截图当前使用 `Pillow`；模板匹配当前使用 `OpenCV + NumPy`。
- Play 按钮当前使用顶部工具栏区域配合仓库根目录 `templates/play-button-idle.png` 和 `templates/play-button-active.png` 做模板匹配，不保留启发式兜底。
- RenderDoc Capture 按钮当前直接在 Unity 窗口截图上做模板匹配；不保留 UIA 边界框依赖，不保留启发式兜底，也不要先退化成固定坐标。

## 当前支持矩阵

- 当前优先支持 Windows。
- 当前实现按 Unity 2022 LTS、中文界面、Pro-Dark 主题做首版适配。
- 运行时建议让 Unity Editor 窗口保持可见，并尽量放在主显示器。

## 后续扩展边界

- 如果后续要提高主题无关性或语言无关性，优先考虑增强状态获取方式，不要先堆更多硬编码截图模板。
- 如果后续要提高稳定性，优先考虑给 Unity 工程侧增加轻量 Editor 扩展暴露状态，而不是继续增加 UI 猜测逻辑。
- 如果行为、依赖、支持范围或限制发生变化，必须同时更新 `README.md` 和 `AGENTS.md`。