from __future__ import annotations

import argparse
import os
import platform
import re
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterator

import pyautogui
import psutil
import pywinctl
from PIL import Image, ImageChops, ImageDraw, ImageGrab, ImageStat


pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


ERROR_PATTERNS = (
    re.compile(r"\berror\s+CS\d+\b", re.IGNORECASE),
    re.compile(r"^\s*(?:Assets|Packages|Library)[/\\].*:\s*error\b", re.IGNORECASE),
    re.compile(r"\bCompilation failed\b", re.IGNORECASE),
    re.compile(r"\bUnhandled\s+Exception\b", re.IGNORECASE),
    re.compile(r"\b(?:[A-Za-z_][\w]*\.)*[A-Za-z_][\w]*Exception:\s", re.IGNORECASE),
    re.compile(r"\berror\b:\s", re.IGNORECASE),
)

IGNORE_ERROR_PATTERNS = (
    re.compile(r"\b0 errors?\b", re.IGNORECASE),
    re.compile(r"\bwithout errors\b", re.IGNORECASE),
)


class UnityAutomationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    activation_timeout: float
    compile_timeout: float
    verify_timeout: float
    poll_interval: float
    log_quiet_seconds: float
    required_play_stability: int
    required_status_stability: int
    status_hash_distance: int
    status_red_ratio_threshold: float
    status_red_samples: int
    debug: bool
    debug_dir: Path
    editor_log_path: Path | None


@dataclass(frozen=True)
class Box:
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def as_bbox(self) -> tuple[int, int, int, int]:
        return (self.left, self.top, self.right, self.bottom)


@dataclass(frozen=True)
class PlayCandidate:
    center_x: int
    center_y: int
    size: int
    score: float
    sample_box: Box
    source: str


@dataclass
class StatusCornerState:
    last_hash: str | None = None
    stable_samples: int = 0
    red_samples: int = 0
    last_distance: int = 64
    last_red_ratio: float = 0.0


@dataclass(frozen=True)
class WindowInfo:
    window: Any
    title: str
    app_name: str
    box: Box
    handle: int | None
    parent_handle: int | None
    is_active: bool


class EditorLogMonitor(threading.Thread):
    def __init__(self, log_path: Path) -> None:
        super().__init__(daemon=True)
        self.log_path = log_path
        self._stop_event = threading.Event()
        self._error_event = threading.Event()
        self._recent_lines: deque[str] = deque(maxlen=40)
        self._error_lines: deque[str] = deque(maxlen=20)
        self._error_context_remaining = 0
        self._last_activity = time.monotonic()

    def run(self) -> None:
        while not self._stop_event.is_set():
            if not self.log_path.exists():
                time.sleep(0.4)
                continue

            try:
                with self.log_path.open("r", encoding="utf-8", errors="replace") as handle:
                    handle.seek(0, os.SEEK_END)
                    while not self._stop_event.is_set():
                        line = handle.readline()
                        if not line:
                            try:
                                if handle.tell() > self.log_path.stat().st_size:
                                    break
                            except OSError:
                                break
                            time.sleep(0.2)
                            continue

                        stripped = line.rstrip()
                        if not stripped:
                            continue

                        self._last_activity = time.monotonic()
                        self._recent_lines.append(stripped)
                        if self._matches_error(stripped):
                            self._error_lines.append(stripped)
                            self._error_event.set()
                            self._error_context_remaining = 6
                        elif self._error_context_remaining > 0:
                            self._error_lines.append(stripped)
                            self._error_context_remaining -= 1
            except OSError as exc:
                self._recent_lines.append(f"[日志监控] {exc}")
                time.sleep(0.5)

    def stop(self) -> None:
        self._stop_event.set()

    def has_error(self) -> bool:
        return self._error_event.is_set()

    def seconds_since_activity(self) -> float:
        return time.monotonic() - self._last_activity

    def format_recent_activity(self) -> str:
        if not self._recent_lines:
            return "开始监控后，Editor.log 暂时没有新增内容。"
        return "最近的 Editor.log 输出:\n" + "\n".join(self._recent_lines)

    def format_recent_errors(self) -> str:
        if not self._error_lines:
            return self.format_recent_activity()
        return "检测到的 Editor.log 错误:\n" + "\n".join(self._error_lines)

    def _matches_error(self, line: str) -> bool:
        if any(pattern.search(line) for pattern in IGNORE_ERROR_PATTERNS):
            return False
        return any(pattern.search(line) for pattern in ERROR_PATTERNS)


def log(message: str) -> None:
    print(f"[Unity自动Play] {message}", flush=True)


def save_debug_image(config: Config, image: Image.Image, stem: str) -> Path | None:
    if not config.debug:
        return None

    config.debug_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    safe_stem = stem.replace(" ", "-").replace("/", "-")
    path = config.debug_dir / f"{timestamp}-{safe_stem}.png"
    image.save(path)
    return path


def resolve_editor_log_path(override: Path | None) -> Path:
    if override is not None:
        return override.expanduser()

    system = platform.system()
    if system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise UnityAutomationError("环境变量 LOCALAPPDATA 未定义，无法定位 Unity Editor.log。")
        return Path(local_app_data) / "Unity" / "Editor" / "Editor.log"
    if system == "Darwin":
        return Path.home() / "Library" / "Logs" / "Unity" / "Editor.log"
    if system == "Linux":
        return Path.home() / ".config" / "unity3d" / "Editor.log"
    raise UnityAutomationError(f"当前平台暂不支持: {system}")


def wait_for_path(path: Path, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.3)
    raise UnityAutomationError(f"没有找到 Unity Editor.log: {path}")


def window_box(window: Any) -> Box:
    width = int(round(window.width))
    height = int(round(window.height))
    return Box(
        left=int(round(window.left)),
        top=int(round(window.top)),
        width=width,
        height=height,
    )


def get_window_pid(window: Any | None) -> int | None:
    if window is None:
        return None

    try:
        return int(window.getPID())
    except Exception:
        return None


def get_process_name(pid: int | None) -> str:
    if pid is None:
        return ""

    try:
        return str(psutil.Process(pid).name()).strip()
    except Exception:
        return ""


def get_window_app_name(window: Any) -> str:
    return get_process_name(get_window_pid(window))


def get_window_handle(window: Any | None) -> int | None:
    if window is None:
        return None

    try:
        return int(window.getHandle())
    except Exception:
        return None


def get_window_parent_handle(window: Any | None) -> int | None:
    if window is None:
        return None

    try:
        parent = window.getParent()
    except Exception:
        return None

    try:
        return int(parent)
    except Exception:
        return None


def get_window_info(window: Any) -> WindowInfo | None:
    try:
        title = str(window.title).strip()
        return WindowInfo(
            window=window,
            title=title,
            app_name=get_window_app_name(window),
            box=window_box(window),
            handle=get_window_handle(window),
            parent_handle=get_window_parent_handle(window),
            is_active=bool(getattr(window, "isActive", False)),
        )
    except Exception:
        return None


def iter_window_info() -> Iterator[WindowInfo]:
    for window in pywinctl.getAllWindows():
        info = get_window_info(window)
        if info is not None:
            yield info


def format_window_description(info: WindowInfo) -> str:
    if info.app_name:
        return f"- {info.title} [{info.app_name}]"
    return f"- {info.title}"


def list_visible_windows() -> list[str]:
    return [format_window_description(info) for info in iter_window_info() if info.title]


def get_window_by_handle(handle: int | None) -> Any | None:
    if handle in (None, 0):
        return None

    for info in iter_window_info():
        if info.handle == handle:
            return info.window
    return None


def is_same_window_or_descendant(window: Any | None, ancestor_handle: int | None) -> bool:
    if window is None or ancestor_handle in (None, 0):
        return False

    visited: set[int] = set()
    current: Any | None = window
    while current is not None:
        current_handle = get_window_handle(current)
        if current_handle == ancestor_handle:
            return True

        parent_handle = get_window_parent_handle(current)
        if parent_handle in (None, 0) or parent_handle in visited:
            return False
        if parent_handle == ancestor_handle:
            return True

        visited.add(parent_handle)
        current = get_window_by_handle(parent_handle)

    return False


def is_window_active(window: Any) -> bool:
    target_handle = get_window_handle(window)
    try:
        active_window = pywinctl.getActiveWindow()
    except Exception:
        active_window = None

    if is_same_window_or_descendant(active_window, target_handle):
        return True

    try:
        return bool(window.isActive)
    except Exception:
        return False


def list_taskbar_application_buttons() -> list[Any]:
    if platform.system() != "Windows":
        return []

    try:
        from pywinauto import Desktop
    except Exception:
        return []

    try:
        taskbar_root = Desktop(backend="uia").window(class_name="Shell_TrayWnd")
        buttons: list[Any] = []
        for item in taskbar_root.descendants():
            try:
                control_type = str(getattr(item.element_info, "control_type", "") or "")
                class_name = str(getattr(item.element_info, "class_name", "") or "")
                text = str(item.window_text()).strip()
            except Exception:
                continue

            if control_type != "Button":
                continue
            if class_name != "Taskbar.TaskListButtonAutomationPeer":
                continue
            if not text:
                continue

            buttons.append(item)
        return buttons
    except Exception:
        return []


def find_unity_taskbar_button(window: Any) -> Any | None:
    target_process = get_window_app_name(window).casefold()
    target_title = str(window.title).strip().casefold()
    best_button: Any | None = None
    best_score = -1.0

    for button in list_taskbar_application_buttons():
        try:
            text = str(button.window_text()).strip()
        except Exception:
            continue

        lowered = text.casefold()
        if "unity" not in lowered or "unity hub" in lowered:
            continue

        score = 0.0
        if lowered.startswith("unity"):
            score += 8.0
        elif " unity" in lowered:
            score += 6.0
        if target_process.startswith("unity"):
            score += 2.0
        if "running window" in lowered:
            score += 0.5
        if target_title and "unity" in target_title:
            score += 0.5

        if score > best_score:
            best_button = button
            best_score = score

    return best_button


def score_unity_window(info: WindowInfo) -> float | None:
    lowered = info.title.casefold()
    app_lowered = info.app_name.casefold()

    if not info.title:
        return None
    if info.parent_handle not in (None, 0):
        return None
    if lowered.startswith("unityeditor."):
        return None
    if any(token in lowered for token in ("visual studio code", "vs code", "unity hub")):
        return None
    if any(token in app_lowered for token in ("code", "cursor", "vscode", "unity hub")):
        return None
    if info.box.width < 120 or info.box.height < 20:
        return None

    if " - unity" in lowered or lowered.endswith(" - unity"):
        base_score = 7.0
    elif re.search(r"\bunity\s+20\d\d", lowered):
        base_score = 6.0
    elif lowered.endswith(" - unity personal") or lowered.endswith(" - unity pro"):
        base_score = 6.0
    elif "unity" in app_lowered:
        base_score = 4.0
    else:
        return None

    area_score = min(info.box.width * info.box.height, 8_000_000) / 8_000_000
    active_bonus = 2.0 if info.is_active else 0.0
    return base_score + active_bonus + area_score


def try_activate_window_via_taskbar(window: Any, config: Config) -> bool:
    button = find_unity_taskbar_button(window)
    if button is None:
        return False

    try:
        button_text = str(button.window_text()).strip()
    except Exception:
        button_text = "Unity"

    log(f"常规激活失败，尝试点击任务栏中的 Unity 按钮: {button_text}")

    try:
        button.click_input()
    except Exception:
        try:
            button.invoke()
        except Exception:
            return False

    deadline = time.monotonic() + max(1.5, config.poll_interval * 6)
    while time.monotonic() < deadline:
        if is_window_active(window):
            return True
        time.sleep(config.poll_interval)

    return False


def activate_show_restore(window: Any) -> None:
    window.show(wait=True)
    window.restore(wait=True, user=True)
    window.activate(wait=True, user=True)


def activate_raise(window: Any) -> None:
    window.raiseWindow()
    window.activate(wait=True, user=True)


def activate_always_on_top(window: Any) -> None:
    window.alwaysOnTop(True)
    time.sleep(0.12)
    window.alwaysOnTop(False)
    window.activate(wait=True, user=True)


def activate_minimize_restore(window: Any) -> None:
    window.minimize(wait=True)
    time.sleep(0.15)
    window.restore(wait=True, user=True)
    window.activate(wait=True, user=True)


ACTIVATION_STRATEGIES: tuple[tuple[str, Callable[[Any], None]], ...] = (
    ("show_restore_activate", activate_show_restore),
    ("raise_activate", activate_raise),
    ("always_on_top_toggle", activate_always_on_top),
    ("minimize_restore_activate", activate_minimize_restore),
)


def debug_log(config: Config, message: str) -> None:
    if config.debug:
        log(message)


def find_unity_window() -> Any:
    best_window: Any | None = None
    best_score = -1.0

    for info in iter_window_info():
        score = score_unity_window(info)
        if score is None:
            continue
        if score > best_score:
            best_window = info.window
            best_score = score

    if best_window is None:
        visible = list_visible_windows()
        visible_text = "\n".join(visible[:20]) or "- <没有可见窗口标题>"
        raise UnityAutomationError(
            "没有找到已打开的 Unity Editor 窗口。当前可见窗口标题:\n" + visible_text
        )

    return best_window


def activate_window(window: Any, config: Config) -> Box:
    title = str(window.title).strip()
    log(f"正在激活 Unity 窗口: {title}")

    try:
        if bool(window.isMinimized):
            window.restore(wait=True, user=True)
            time.sleep(0.4)
    except Exception:
        pass

    deadline = time.monotonic() + config.activation_timeout
    strategy_index = 0
    taskbar_attempted = False

    while time.monotonic() < deadline:
        try:
            box = window_box(window)
            if is_window_active(window):
                debug_log(config, "Unity 窗口已成为前台窗口。")
                return box
        except Exception:
            break

        if strategy_index < len(ACTIVATION_STRATEGIES):
            strategy_name, strategy_action = ACTIVATION_STRATEGIES[strategy_index]
            strategy_index += 1
            debug_log(config, f"尝试激活策略: {strategy_name}")
            try:
                strategy_action(window)
            except Exception:
                pass
        elif not taskbar_attempted and try_activate_window_via_taskbar(window, config):
            taskbar_attempted = True
            try:
                debug_log(config, "任务栏兜底激活成功。")
                return window_box(window)
            except Exception:
                break
        else:
            taskbar_attempted = True
            debug_log(config, "重复尝试直接调用窗口 activate。")
            try:
                window.activate(wait=True, user=True)
            except Exception:
                pass

        time.sleep(0.2)

    raise UnityAutomationError(
        f"无法把 Unity 窗口切到前台: {title}。"
        "如果 Unity 以管理员权限运行，请用相同权限启动当前脚本。"
    )


def build_toolbar_box(box: Box) -> Box:
    width = max(200, min(320, box.width // 3))
    height = max(56, min(84, box.height // 8))
    left = box.left + (box.width - width) // 2
    top = box.top + max(28, min(40, box.height // 20))
    return Box(left=left, top=top, width=width, height=height)


def build_status_box(box: Box) -> Box:
    width = max(180, min(300, box.width // 4))
    height = 84
    left = box.right - width - 24
    top = box.bottom - height - 24
    return Box(left=left, top=top, width=width, height=height)


def clamp_sample_box(sample_box: Box, outer_box: Box) -> Box:
    left = max(sample_box.left, outer_box.left)
    top = max(sample_box.top, outer_box.top)
    right = min(sample_box.right, outer_box.right)
    bottom = min(sample_box.bottom, outer_box.bottom)
    return Box(left=left, top=top, width=max(8, right - left), height=max(8, bottom - top))


def grab_box(box: Box) -> Image.Image:
    if box.width <= 0 or box.height <= 0:
        raise UnityAutomationError(f"截图区域无效: {box}")

    try:
        return ImageGrab.grab(bbox=box.as_bbox(), all_screens=True)
    except TypeError:
        return ImageGrab.grab(bbox=box.as_bbox())


def average_hash(image: Image.Image, hash_size: int = 8) -> str:
    sample = image.convert("L").resize((hash_size, hash_size), Image.Resampling.BILINEAR)
    pixels = list(sample.tobytes())
    threshold = sum(pixels) / len(pixels)
    return "".join("1" if pixel >= threshold else "0" for pixel in pixels)


def hamming_distance(left: str, right: str) -> int:
    return sum(1 for left_bit, right_bit in zip(left, right) if left_bit != right_bit)


def red_alert_ratio(image: Image.Image) -> float:
    rgb_image = image.convert("RGB")
    pixels = rgb_image.load()
    total = 0
    red_like = 0
    for y in range(rgb_image.height):
        for x in range(rgb_image.width):
            red, green, blue = pixels[x, y]
            total += 1
            if red >= 165 and red > green * 1.20 and red > blue * 1.45 and (red - min(green, blue)) >= 40:
                red_like += 1
    return red_like / total if total else 0.0


def update_status_corner_state(
    image: Image.Image,
    state: StatusCornerState,
    config: Config,
) -> StatusCornerState:
    current_hash = average_hash(image)
    current_red_ratio = red_alert_ratio(image)

    if state.last_hash is None:
        stable_samples = 0
        last_distance = 64
    else:
        last_distance = hamming_distance(state.last_hash, current_hash)
        stable_samples = state.stable_samples + 1 if last_distance <= config.status_hash_distance else 0

    red_samples = state.red_samples + 1 if current_red_ratio >= config.status_red_ratio_threshold else 0
    return StatusCornerState(
        last_hash=current_hash,
        stable_samples=stable_samples,
        red_samples=red_samples,
        last_distance=last_distance,
        last_red_ratio=current_red_ratio,
    )


@lru_cache(maxsize=None)
def triangle_mask(size: int) -> tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]:
    mask = Image.new("1", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(
        [(1, 1), (1, size - 2), (size - 2, size // 2)],
        fill=1,
    )

    inside: list[tuple[int, int]] = []
    outside: list[tuple[int, int]] = []
    for y in range(size):
        for x in range(size):
            if mask.getpixel((x, y)):
                inside.append((x, y))
            else:
                outside.append((x, y))
    return tuple(inside), tuple(outside)


def estimate_play_candidate(toolbar_box: Box, window_box_value: Box) -> PlayCandidate:
    center_x = window_box_value.left + window_box_value.width // 2
    center_y = toolbar_box.top + toolbar_box.height // 2
    sample_box = clamp_sample_box(
        Box(center_x - 18, center_y - 18, 36, 36),
        window_box_value,
    )
    return PlayCandidate(
        center_x=center_x,
        center_y=center_y,
        size=18,
        score=0.0,
        sample_box=sample_box,
        source="几何兜底",
    )


def find_play_candidate(toolbar_image: Image.Image, toolbar_box: Box, window_box_value: Box) -> PlayCandidate | None:
    gray = toolbar_image.convert("L")
    pixels = gray.load()
    width, height = gray.size
    target_x = width // 2
    target_y = height // 2
    best: PlayCandidate | None = None

    # 在工具栏中心附近搜索较亮的右向三角形。
    for size in (12, 14, 16, 18):
        inside, outside = triangle_mask(size)
        for y in range(0, max(1, height - size), 2):
            for x in range(0, max(1, width - size), 2):
                probe_x = x + max(1, size // 3)
                probe_y = y + size // 2
                if pixels[probe_x, probe_y] < 110:
                    continue

                inside_sum = 0
                for dx, dy in inside:
                    inside_sum += pixels[x + dx, y + dy]
                outside_sum = 0
                for dx, dy in outside:
                    outside_sum += pixels[x + dx, y + dy]

                inside_mean = inside_sum / len(inside)
                outside_mean = outside_sum / len(outside)
                contrast = inside_mean - outside_mean
                if contrast < 18:
                    continue

                center_x = x + size // 2
                center_y = y + size // 2
                distance_penalty = abs(center_x - target_x) * 0.18 + abs(center_y - target_y) * 0.12
                score = contrast - distance_penalty
                if score < 18:
                    continue

                global_center_x = toolbar_box.left + center_x
                global_center_y = toolbar_box.top + center_y
                sample_box = clamp_sample_box(
                    Box(global_center_x - 18, global_center_y - 18, 36, 36),
                    window_box_value,
                )

                candidate = PlayCandidate(
                    center_x=global_center_x,
                    center_y=global_center_y,
                    size=size,
                    score=score,
                    sample_box=sample_box,
                    source="启发式识别",
                )
                if best is None or candidate.score > best.score:
                    best = candidate

    if best is None:
        return None

    toolbar_center_x = window_box_value.left + window_box_value.width // 2
    if abs(best.center_x - toolbar_center_x) > 56:
        return None
    return best


def is_same_candidate(previous: PlayCandidate | None, current: PlayCandidate | None) -> bool:
    if previous is None or current is None:
        return False
    return (
        abs(previous.center_x - current.center_x) <= 6
        and abs(previous.center_y - current.center_y) <= 6
        and previous.source == current.source
    )


def image_difference_score(before: Image.Image, after: Image.Image) -> float:
    diff = ImageChops.difference(before.convert("RGB"), after.convert("RGB"))
    means = ImageStat.Stat(diff).mean
    return sum(means) / len(means)


def blue_ratio(image: Image.Image) -> float:
    rgb_image = image.convert("RGB")
    pixels = rgb_image.load()
    total = 0
    blue_like = 0
    for y in range(rgb_image.height):
        for x in range(rgb_image.width):
            red, green, blue = pixels[x, y]
            total += 1
            if blue >= 110 and blue > red + 12 and blue > green + 12:
                blue_like += 1
    return blue_like / total if total else 0.0


def parking_point(window_box_value: Box, avoid_box: Box) -> tuple[int, int]:
    candidates = (
        (window_box_value.left + 40, window_box_value.top + 40),
        (window_box_value.right - 40, window_box_value.top + 40),
        (window_box_value.left + 40, window_box_value.bottom - 40),
    )

    for x, y in candidates:
        if not (avoid_box.left <= x <= avoid_box.right and avoid_box.top <= y <= avoid_box.bottom):
            return (x, y)

    return (window_box_value.left + 16, window_box_value.top + 16)


def wait_for_ready_play_candidate(window: Any, log_monitor: EditorLogMonitor, config: Config) -> PlayCandidate:
    deadline = time.monotonic() + config.compile_timeout
    last_report = 0.0
    status_state = StatusCornerState()
    previous_candidate: PlayCandidate | None = None
    stable_candidate_count = 0
    fallback_since: float | None = None
    red_indicator_reported = False

    while time.monotonic() < deadline:
        if log_monitor.has_error():
            raise UnityAutomationError("等待进入 Play 前，Unity Editor.log 中出现了新的错误。")

        current_window_box = window_box(window)
        toolbar_box = build_toolbar_box(current_window_box)
        toolbar_image = grab_box(toolbar_box)
        candidate = find_play_candidate(toolbar_image, toolbar_box, current_window_box)
        if is_same_candidate(previous_candidate, candidate):
            stable_candidate_count += 1
        elif candidate is not None:
            stable_candidate_count = 1
        else:
            stable_candidate_count = 0
        previous_candidate = candidate

        status_box = build_status_box(current_window_box)
        status_image = grab_box(status_box)
        status_state = update_status_corner_state(status_image, status_state, config)

        if config.debug and status_state.red_samples == config.status_red_samples:
            saved_path = save_debug_image(config, status_image, "status-corner-warning")
            if saved_path is not None:
                log(f"已保存右下角可疑状态截图: {saved_path}")

        log_quiet = log_monitor.seconds_since_activity() >= config.log_quiet_seconds
        if status_state.red_samples >= config.status_red_samples and not red_indicator_reported:
            log(
                "检测到 Unity 右下角可能出现了警告或错误提示；"
                "当前仍以 Editor.log 作为主判断信号。"
            )
            red_indicator_reported = True

        if (
            candidate is not None
            and stable_candidate_count >= config.required_play_stability
            and status_state.stable_samples >= config.required_status_stability
            and log_quiet
        ):
            return candidate

        if candidate is None and status_state.stable_samples >= config.required_status_stability and log_quiet:
            if fallback_since is None:
                fallback_since = time.monotonic()
            elif time.monotonic() - fallback_since >= 1.0:
                log("Play 按钮启发式识别不够稳定，回退到工具栏中心估计位置。")
                return estimate_play_candidate(toolbar_box, current_window_box)
        else:
            fallback_since = None

        if time.monotonic() - last_report >= 2.5:
            score_text = f"{candidate.score:.1f}" if candidate is not None else "无"
            log(
                "正在等待 Unity 进入空闲状态: "
                f"按钮评分={score_text}, "
                f"按钮稳定次数={stable_candidate_count}/{config.required_play_stability}, "
                f"状态区稳定次数={status_state.stable_samples}/{config.required_status_stability}, "
                f"日志是否安静={log_quiet}"
            )
            last_report = time.monotonic()

        time.sleep(config.poll_interval)

    if config.debug:
        save_debug_image(config, toolbar_image, "toolbar-timeout")
        save_debug_image(config, status_image, "status-timeout")
    raise UnityAutomationError("等待 Unity 编译或导入完成超时。")


def click_play_button(window: Any, candidate: PlayCandidate, log_monitor: EditorLogMonitor, config: Config) -> None:
    current_window_box = window_box(window)
    verification_box = clamp_sample_box(
        Box(candidate.center_x - 32, candidate.center_y - 24, 64, 48),
        current_window_box,
    )
    mouse_park_x, mouse_park_y = parking_point(current_window_box, verification_box)

    activate_window(window, config)
    pyautogui.moveTo(mouse_park_x, mouse_park_y)
    time.sleep(config.poll_interval)

    before_image = grab_box(verification_box)
    before_blue_ratio = blue_ratio(before_image)
    pyautogui.click(candidate.center_x, candidate.center_y)
    log(
        f"已点击 Play 按钮，位置=({candidate.center_x}, {candidate.center_y})，来源={candidate.source}。"
    )

    time.sleep(0.08)
    pyautogui.moveTo(mouse_park_x, mouse_park_y)

    deadline = time.monotonic() + config.verify_timeout
    after_image = before_image
    stable_verifications = 0
    while time.monotonic() < deadline:
        if log_monitor.has_error():
            raise UnityAutomationError("点击 Play 后，Unity Editor.log 中立即出现了错误。")

        time.sleep(config.poll_interval)
        after_image = grab_box(verification_box)
        diff_score = image_difference_score(before_image, after_image)
        after_blue_ratio = blue_ratio(after_image)
        blue_gain = after_blue_ratio - before_blue_ratio
        if diff_score >= 8.0 or (blue_gain >= 0.025 and after_blue_ratio >= 0.03):
            stable_verifications += 1
        else:
            stable_verifications = 0

        if stable_verifications >= 2:
            if config.debug:
                save_debug_image(config, before_image, "play-before")
                save_debug_image(config, after_image, "play-verified")
            return

    if config.debug:
        save_debug_image(config, before_image, "play-before-timeout")
        save_debug_image(config, after_image, "play-after-timeout")
    raise UnityAutomationError("已点击 Play，但无法确认 Unity 真的进入了播放模式。")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="激活 Unity Editor，等待空闲，然后自动点击 Play。",
    )
    parser.add_argument(
        "--editor-log",
        type=Path,
        default=None,
        help="手动指定 Unity 的 Editor.log 路径。",
    )
    parser.add_argument(
        "--activation-timeout",
        type=float,
        default=12.0,
        help="激活 Unity 前台窗口时允许等待的秒数。",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="点击 Play 前，等待 Unity 编译或导入完成的最长秒数。",
    )
    parser.add_argument(
        "--verify-timeout",
        type=float,
        default=5.0,
        help="点击 Play 后，验证是否成功进入播放模式的最长秒数。",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.35,
        help="窗口、日志、状态区轮询间隔，单位为秒。",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="保存调试截图。",
    )
    parser.add_argument(
        "--debug-dir",
        type=Path,
        default=Path("logs/unity-auto-play"),
        help="调试截图输出目录。",
    )
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> Config:
    return Config(
        activation_timeout=args.activation_timeout,
        compile_timeout=args.timeout,
        verify_timeout=args.verify_timeout,
        poll_interval=args.poll_interval,
        log_quiet_seconds=max(args.poll_interval * 2.5, 1.0),
        required_play_stability=3,
        required_status_stability=5,
        status_hash_distance=3,
        status_red_ratio_threshold=0.0045,
        status_red_samples=3,
        debug=bool(args.debug),
        debug_dir=args.debug_dir,
        editor_log_path=args.editor_log,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = config_from_args(args)
    log_monitor: EditorLogMonitor | None = None

    try:
        editor_log_path = resolve_editor_log_path(config.editor_log_path)
        wait_for_path(editor_log_path, timeout=5.0)
        log(f"正在监控 Unity Editor.log: {editor_log_path}")

        log_monitor = EditorLogMonitor(editor_log_path)
        log_monitor.start()

        unity_window = find_unity_window()
        activate_window(unity_window, config)
        candidate = wait_for_ready_play_candidate(unity_window, log_monitor, config)
        click_play_button(unity_window, candidate, log_monitor, config)

        log("Unity 已进入播放模式。")
        return 0
    except UnityAutomationError as exc:
        print(f"[Unity自动Play] 错误: {exc}", file=sys.stderr)
        if log_monitor is not None:
            if log_monitor.has_error():
                print(log_monitor.format_recent_errors(), file=sys.stderr)
            else:
                print(log_monitor.format_recent_activity(), file=sys.stderr)
        return 1
    finally:
        if log_monitor is not None:
            log_monitor.stop()
            log_monitor.join(timeout=2.0)


if __name__ == "__main__":
    raise SystemExit(main())