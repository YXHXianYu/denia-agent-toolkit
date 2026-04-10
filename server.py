from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from pydantic import BaseModel, Field


REPO_ROOT = Path(__file__).resolve().parent
UNITY_AUTO_PLAY_SCRIPT = REPO_ROOT / "scripts" / "unity-auto-play.py"
SERVER_VERSION = "0.1.0"


class CommandResult(BaseModel):
    success: bool = Field(description="Whether the command exited with code 0.")
    exit_code: int = Field(description="Process exit code.")
    command: list[str] = Field(description="Executed command arguments.")
    cwd: str = Field(description="Working directory used for the command.")
    stdout: str = Field(description="Captured standard output.")
    stderr: str = Field(description="Captured standard error.")


class ToolkitStatus(BaseModel):
    repo_root: str = Field(description="Repository root directory.")
    mcp_server: str = Field(description="MCP server entry file.")
    unity_auto_play_script: str = Field(description="Implemented Unity automation script.")
    supported_platforms: list[str] = Field(description="Platforms currently targeted by this toolkit.")
    implemented_workflows: list[str] = Field(description="Workflows that are implemented today.")
    pending_workflows: list[str] = Field(description="Workflows planned but not implemented yet.")


mcp = FastMCP(
    "denia-agent-toolkit",
    instructions=(
        "Local graphics and engine automation toolkit. Current implemented surface: "
        "external Unity Editor automation via scripts/unity-auto-play.py. "
        "Use the provided tools to inspect current capabilities, show the Unity auto-play CLI help, "
        "or run the Unity auto-play workflow. UE, RenderDoc, and broader MCP toolsets are not "
        "implemented yet."
    ),
)


def build_unity_auto_play_command(
    *,
    renderdoc_capture: bool,
    debug_dir: str,
) -> list[str]:
    command = [sys.executable, str(UNITY_AUTO_PLAY_SCRIPT)]

    if renderdoc_capture:
        command.append("--renderdoc-capture")
    command.extend(["--debug-dir", debug_dir])
    return command


async def run_command(
    command: list[str],
    *,
    ctx: Context[ServerSession, None] | None = None,
) -> CommandResult:
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(REPO_ROOT),
        env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await process.communicate()

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")
    exit_code = process.returncode or 0

    return CommandResult(
        success=exit_code == 0,
        exit_code=exit_code,
        command=command,
        cwd=str(REPO_ROOT),
        stdout=stdout,
        stderr=stderr,
    )


@mcp.resource("toolkit://capabilities")
def toolkit_capabilities() -> str:
    """Describe the currently implemented capabilities of this repository."""
    return (
        "# Denia Agent Toolkit\n\n"
        "## Implemented\n"
        "- Unity external automation via scripts/unity-auto-play.py\n"
        "- Unity window activation, idle detection, Play enter/exit, optional template-matched RenderDoc capture-button click 1 second before Play stops, Editor.log observation, and post-run window minimization\n"
        "- MCP wrapper tools for capability inspection and running the Unity workflow\n\n"
        "## Not Implemented Yet\n"
        "- UE automation\n"
        "- Standalone RenderDoc workflow\n"
        "- Additional MCP tools beyond the Unity wrapper\n"
    )


@mcp.tool()
def toolkit_status() -> ToolkitStatus:
    """Return the current implemented scope of this repository."""
    return ToolkitStatus(
        repo_root=str(REPO_ROOT),
        mcp_server=str(REPO_ROOT / "server.py"),
        unity_auto_play_script=str(UNITY_AUTO_PLAY_SCRIPT),
        supported_platforms=["Windows"],
        implemented_workflows=[
            "Unity external auto-play workflow",
            "Optional template-matched RenderDoc capture button click 1 second before Play stops during Unity auto-play",
            "Editor.log key log capture and deduplication",
            "Automatic Play stop after the observation window",
            "Automatic Unity window minimization after Play exits",
        ],
        pending_workflows=[
            "UE automation",
            "Standalone RenderDoc workflow",
            "Additional MCP-native tools",
        ],
    )


@mcp.tool()
async def unity_auto_play_help(ctx: Context[ServerSession, None]) -> CommandResult:
    """Show the CLI help for the implemented Unity auto-play script."""
    return await run_command([sys.executable, str(UNITY_AUTO_PLAY_SCRIPT), "--help"], ctx=ctx)


@mcp.tool()
async def unity_auto_play_run(
    ctx: Context[ServerSession, None],
    renderdoc_capture: bool = False,
    debug_dir: str = "logs/unity-auto-play",
) -> CommandResult:
    """Run the external Unity auto-play workflow that activates Unity, enters Play, optionally triggers a template-matched RenderDoc capture 1 second before Play stops, captures logs, and exits Play."""
    command = build_unity_auto_play_command(
        renderdoc_capture=renderdoc_capture,
        debug_dir=debug_dir,
    )
    return await run_command(command, ctx=ctx)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the denia-agent-toolkit MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="Transport to use for the MCP server.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for streamable HTTP transport.")
    parser.add_argument("--port", type=int, default=8000, help="Port for streamable HTTP transport.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.transport == "streamable-http":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())