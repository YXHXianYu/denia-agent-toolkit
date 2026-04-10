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
```

### Unity Auto Play

自动激活Unity窗口、等待编译、点击Play、等待10秒捕获日志、去重后打印到终端，并自动关闭Play模式。

```powershell
uv run python scripts/unity-auto-play.py --debug
```

输出示例

```
[UnityAutoPlay] 策略 激活=评分选窗+多策略+任务栏兜底
[UnityAutoPlay] 策略 空闲=log静默1.0s+状态5次+按钮3次
[UnityAutoPlay] 策略 验证=点Play后检测按钮变化/蓝高亮
[UnityAutoPlay] 策略 日志=Play后观察10s+前5行去重+自动停Play
[UnityAutoPlay] 监控日志: C:\Users\xianhao.yu\AppData\Local\Unity\Editor\Editor.log
[UnityAutoPlay] 激活Unity: UnityFFTBloom - Environment_Free - Windows, Mac, Linux - Unity 2022.3.6f1 <DX12>
[UnityAutoPlay] 激活策略: show_restore_activate
[UnityAutoPlay] Unity已激活
[UnityAutoPlay] 等待空闲: 分=112.9 按钮=1/3 状态=0/5 静默=N
[UnityAutoPlay] 已空闲: log静默+状态稳定+按钮稳定
[UnityAutoPlay] 激活Unity: UnityFFTBloom - Environment_Free - Windows, Mac, Linux - Unity 2022.3.6f1 <DX12>
[UnityAutoPlay] Unity已激活
[UnityAutoPlay] 已点Play: (931, 66) 启发式识别
[UnityAutoPlay] 已进入Play
[UnityAutoPlay] Play已进入, 观察日志10s
[UnityAutoPlay] Play后关键日志 10s。因为Editor.log不足以判断具体输出日志是哪些，所以脚本会向前包含5行。如果你发现日志被截断，请调整参数
[UnityAutoPlay][日志 1][x1]
Integration:            271.234 ms
Integration of assets:  0.014 ms
Thread Wait Time:       0.000 ms
Total Operation Time:   285.540 ms
OnRenderImage() possibly didn't write anything to the destination texture!

[UnityAutoPlay] 激活Unity: UnityFFTBloom - Environment_Free - Windows, Mac, Linux - Unity 2022.3.6f1 <DX12>
[UnityAutoPlay] Unity已激活
[UnityAutoPlay] 10s到, 停Play: (931, 66) 启发式识别
[UnityAutoPlay] 已停Play
```

## 开发

详细实现约定、行为说明和维护边界见 `AGENTS.md`。
