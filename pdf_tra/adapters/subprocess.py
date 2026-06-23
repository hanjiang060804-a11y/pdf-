from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    argv: list[str]


def _venv_scripts_dir() -> Path | None:
    scripts = Path(sys.executable).resolve().parent
    if scripts.is_dir() and scripts.name.lower() in {"scripts", "bin"}:
        return scripts
    return None


def _subprocess_env() -> dict[str, str]:
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    scripts = _venv_scripts_dir()
    if scripts is not None:
        prefix = str(scripts)
        current = env.get("PATH", "")
        if not current.lower().startswith(prefix.lower()):
            env["PATH"] = prefix + os.pathsep + current
    return env


def which_tool(name: str) -> Path | None:
    path = shutil.which(name)
    if path:
        return Path(path)
    scripts = _venv_scripts_dir()
    if scripts is None:
        return None
    for candidate in (scripts / name, scripts / f"{name}.exe"):
        if candidate.is_file():
            return candidate
    return None


def run_command(
    argv: list[str],
    *,
    timeout: int | None = None,
    cwd: Path | None = None,
) -> CommandResult:
    completed = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=str(cwd) if cwd else None,
        env=_subprocess_env(),
        check=False,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        argv=argv,
    )


def run_command_streaming(
    argv: list[str],
    *,
    on_stderr_line: Callable[[str], None] | None = None,
    on_stdout_line: Callable[[str], None] | None = None,
    timeout: int | None = None,
    cwd: Path | None = None,
) -> CommandResult:
    if on_stderr_line is None and on_stdout_line is None:
        return run_command(argv, timeout=timeout, cwd=cwd)

    proc = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd) if cwd else None,
        env=_subprocess_env(),
    )
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    def _drain(stream, collector: list[str], handler: Callable[[str], None] | None) -> None:
        if stream is None:
            return
        chunks: list[str] = []
        pending = ""
        while True:
            data = stream.read(256)
            if not data:
                break
            chunks.append(data)
            pending += data
            while pending:
                split_at = next((i for i, ch in enumerate(pending) if ch in "\r\n"), None)
                if split_at is None:
                    break
                segment = pending[:split_at]
                pending = pending[split_at + 1 :]
                if pending.startswith("\n"):
                    pending = pending[1:]
                if handler is not None and segment:
                    handler(segment)
        if handler is not None and pending.strip():
            handler(pending)
        collector.append("".join(chunks))

    threads = []
    if proc.stdout is not None:
        threads.append(
            threading.Thread(
                target=_drain,
                args=(proc.stdout, stdout_lines, on_stdout_line),
                daemon=True,
            )
        )
    if proc.stderr is not None:
        threads.append(
            threading.Thread(
                target=_drain,
                args=(proc.stderr, stderr_lines, on_stderr_line),
                daemon=True,
            )
        )
    for thread in threads:
        thread.start()
    try:
        returncode = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise
    finally:
        for thread in threads:
            thread.join(timeout=1)

    return CommandResult(
        returncode=returncode,
        stdout="".join(stdout_lines),
        stderr="".join(stderr_lines),
        argv=argv,
    )
