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
- 脚本职责固定为：激活 Unity Editor、等待空闲、搜索 Play、点击 Play、进入 Play 后继续观察日志、提取关键日志并去重打印、持续监控错误。
- 运行时要把核心策略直接打印到终端，文案尽量短，优先输出“当前判断方式”和“当前阶段结果”。
- 错误监控以 Unity `Editor.log` 为主信号，右下角状态区监控为补充信号。
- 当前默认行为是在确认进入 Play 后继续观察 `Editor.log` 10 秒，并从这段时间内捕获到的新增日志里提取关键日志；当前关键日志定义为 `UnityEngine.StackTraceUtility:ExtractStackTrace ()` 前面的有效消息块，但最多只保留离该标记最近的 5 行，这个限制由脚本顶部的 `KEY_MESSAGE_LINE_LIMIT` 控制；保留 `Debug.Log` 自带的换行和空行，再按这 5 行内容首次出现的顺序聚合统计输出次数。
- `--debug` 调试截图默认输出到 `logs/unity-auto-play/`。
- “等待编译完成”当前不是通过 Unity 内部 API 判断，而是通过以下外部信号组合判断：
  - `Editor.log` 在一段时间内没有新增输出。
  - 右下角状态区连续多个采样保持稳定。
  - 顶部工具栏的 Play 按钮候选连续稳定出现。

## 技术选择

- 不直接使用 Win32 API，也不要在这个脚本里手写 `pywin32` 级别调用。
- 窗口激活优先使用 `PyWinCtl`，不要把 `PyAutoGUI` 当成首选窗口管理方案。
- 窗口所属应用名优先通过进程 PID + `psutil` 获取，不再调用 `PyWinCtl.getAppName()`，避免在 Windows 上卡进 WMI 查询。
- Windows 上如果 `PyWinCtl` 常规激活失败，可回退到 `pywinauto` 的 UI Automation 路径，点击任务栏里的 Unity 运行中应用按钮；这属于高层外部自动化兜底，不是手写 Win32。
- Unity 窗口筛选优先参考窗口所属应用名，不要只根据标题里是否包含 `Unity` 判断，否则项目名或路径里带 `Unity` 时容易误选到 VS Code。
- 窗口尚未确认切到前台前，不要通过屏幕坐标盲点标题栏，否则可能误点到 VS Code 或其他前台程序。
- 输入和点击当前使用 `PyAutoGUI`。
- 截图和局部图像比较当前使用 `Pillow`。
- Play 按钮识别当前使用“顶部工具栏中心区域三角形启发式搜索”，并保留了几何中心兜底。

## 当前支持矩阵

- 当前优先支持 Windows。
- 当前实现按 Unity 2022 LTS、中文界面、Pro-Dark 主题做首版适配。
- 运行时建议让 Unity Editor 窗口保持可见，并尽量放在主显示器。

## 后续扩展边界

- 如果后续要提高主题无关性或语言无关性，优先考虑增强状态获取方式，不要先堆更多硬编码截图模板。
- 如果后续要提高稳定性，优先考虑给 Unity 工程侧增加轻量 Editor 扩展暴露状态，而不是继续增加 UI 猜测逻辑。
- 如果行为、依赖、支持范围或限制发生变化，必须同时更新 `README.md` 和 `AGENTS.md`。