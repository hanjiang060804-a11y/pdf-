import io
import subprocess
import threading
from unittest.mock import MagicMock

from pdf_tra.adapters.subprocess import run_command_streaming


def test_streaming_handles_carriage_return_progress(monkeypatch):
    calls: list[str] = []

    class FakeProc:
        returncode = 0

        def __init__(self):
            self.stdout = io.StringIO("")
            self.stderr = io.StringIO(
                "  0%|          | 0/57 [00:00<?, ?it/s]\r"
                "  4%|▍         | 2/57 [00:01<00:40,  1.36it/s]\r"
                "  7%|▋         | 4/57 [00:02<00:35,  1.50it/s]\n"
            )

        def wait(self, timeout=None):
            return 0

        def kill(self):
            return None

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: FakeProc())

    def on_line(line: str) -> None:
        calls.append(line)

    result = run_command_streaming(["pdf2zh", "in.pdf"], on_stderr_line=on_line)
    assert result.returncode == 0
    assert any("2/57" in line for line in calls)
    assert any("4/57" in line for line in calls)
