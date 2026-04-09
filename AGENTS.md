# AGENTS

这个文件记录 `denia-agent-toolkit` 当前已经落地的实现约定，后续 agent 或维护者应以这里为基线继续演进。

## 项目管理

- 依赖管理采用 `pyproject.toml + uv.lock`。
- 不再维护 `requirements.txt`。
- 新增依赖时优先使用 `uv add <package>`，不要手写改 `uv.lock`。
- 运行脚本和做本地验证时优先使用 `uv run ...`。

## Unity Auto Play 约定

- `scripts/unity-active-and-play.py` 保持为核心单文件实现脚本。
- 脚本职责固定为：激活 Unity Editor、等待空闲、搜索 Play、点击 Play、持续监控错误。
- 错误监控以 Unity `Editor.log` 为主信号，右下角状态区监控为补充信号。
- “等待编译完成”当前不是通过 Unity 内部 API 判断，而是通过以下外部信号组合判断：
  - `Editor.log` 在一段时间内没有新增输出。
  - 右下角状态区连续多个采样保持稳定。
  - 顶部工具栏的 Play 按钮候选连续稳定出现。

## 技术选择

- 不直接使用 Win32 API，也不要在这个脚本里手写 `pywin32` 级别调用。
- 窗口激活优先使用 `PyWinCtl`，不要把 `PyAutoGUI` 当成首选窗口管理方案。
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