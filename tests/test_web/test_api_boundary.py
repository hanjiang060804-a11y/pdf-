"""Web API 边缘情况测试（对应 web_server.md 边界表）。"""

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pdf_tra.core.errors import PdfTraError, ExitCode
from pdf_tra.core.models import InspectResult, PdfInfo
from pdf_tra.web.server import create_app


@pytest.fixture
def client(tmp_path: Path):
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps(
            {
                "threads": 4,
                "translators": [
                    {"name": "deepseek", "envs": {"DEEPSEEK_API_KEY": "sk-test-key-12345678"}},
                ],
            }
        ),
        encoding="utf-8",
    )
    uploads = tmp_path / "uploads"
    app = create_app(config_path=cfg, upload_dir=uploads)
    return TestClient(app), uploads


# ── inspect 上传 ──────────────────────────────────────────────


def test_inspect_upload_rejects_txt(client):
    c, _ = client
    r = c.post("/api/v1/inspect", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400
    assert "PDF" in r.json()["detail"]


def test_inspect_upload_rejects_no_extension(client):
    c, _ = client
    r = c.post("/api/v1/inspect", files={"file": ("document", b"%PDF-1.4\n", "application/pdf")})
    assert r.status_code == 400


def test_inspect_upload_accepts_uppercase_pdf(client, monkeypatch):
    c, uploads = client
    pdf_bytes = b"%PDF-1.4\n"

    monkeypatch.setattr(
        "pdf_tra.web.server.inspect_pdf",
        lambda path, **kw: InspectResult(
            input_path=path,
            pdf_info=PdfInfo(pages=1, encrypted=False),
            pdf_type="text",
            char_count=10,
            suggestion="ok",
            can_translate=True,
        ),
    )
    r = c.post("/api/v1/inspect", files={"file": ("Paper.PDF", pdf_bytes, "application/pdf")})
    assert r.status_code == 200
    assert (uploads / "Paper.PDF").exists()


def test_inspect_upload_sanitizes_path_traversal(client, monkeypatch):
    c, uploads = client

    monkeypatch.setattr(
        "pdf_tra.web.server.inspect_pdf",
        lambda path, **kw: InspectResult(
            input_path=path,
            pdf_info=PdfInfo(pages=1, encrypted=False),
            pdf_type="text",
            char_count=1,
            suggestion="ok",
            can_translate=True,
        ),
    )
    r = c.post(
        "/api/v1/inspect",
        files={"file": ("../../escape.pdf", b"%PDF-1.4\n", "application/pdf")},
    )
    assert r.status_code == 200
    assert (uploads / "escape.pdf").exists()
    assert not (uploads.parent.parent / "escape.pdf").exists()


def test_inspect_upload_invalid_pdf_content_removed(client):
    c, uploads = client
    r = c.post(
        "/api/v1/inspect",
        files={"file": ("fake.pdf", b"not-a-pdf", "application/pdf")},
    )
    assert r.status_code == 400
    assert not list(uploads.glob("fake.pdf"))


def test_inspect_upload_missing_file_field(client):
    c, _ = client
    r = c.post("/api/v1/inspect")
    assert r.status_code == 422


# ── inspect 路径 ──────────────────────────────────────────────


def test_inspect_path_missing_file(client):
    c, _ = client
    r = c.post("/api/v1/inspect/path", json={"path": "/no/such/file.pdf"})
    assert r.status_code == 404
    assert "不存在" in r.json()["detail"]


def test_inspect_path_not_pdf(client, tmp_path: Path):
    c, _ = client
    bad = tmp_path / "bad.pdf"
    bad.write_text("hello", encoding="utf-8")
    r = c.post("/api/v1/inspect/path", json={"path": str(bad)})
    assert r.status_code == 400
    assert "不是有效的 PDF" in r.json()["detail"]


# ── translate 提交 ────────────────────────────────────────────


def test_translate_missing_file(client):
    c, _ = client
    r = c.post("/api/v1/translate", json={"path": "/missing/doc.pdf"})
    assert r.status_code == 404


def test_translate_not_pdf(client, tmp_path: Path):
    c, _ = client
    bad = tmp_path / "x.pdf"
    bad.write_text("x", encoding="utf-8")
    r = c.post("/api/v1/translate", json={"path": str(bad)})
    assert r.status_code == 400


def test_translate_invalid_engine(client, tmp_path: Path):
    c, _ = client
    pdf = tmp_path / "ok.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    r = c.post("/api/v1/translate", json={"path": str(pdf), "engine": "unknown"})
    assert r.status_code == 400
    assert "babeldoc" in r.json()["detail"]


def test_translate_job_reports_error(client, monkeypatch, tmp_path: Path):
    c, _ = client
    pdf = tmp_path / "fail.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    def boom(*a, **k):
        raise PdfTraError("模拟翻译失败", ExitCode.EXTERNAL_CMD_FAILED)

    monkeypatch.setattr("pdf_tra.web.server.translate_pdf", boom)
    r = c.post("/api/v1/translate", json={"path": str(pdf)})
    assert r.status_code == 200
    job_id = r.json()["job_id"]

    for _ in range(40):
        status = c.get(f"/api/v1/jobs/{job_id}").json()
        if status["status"] in {"done", "error"}:
            break
        time.sleep(0.05)
    assert status["status"] == "error"
    assert "模拟翻译失败" in status["error"]


# ── jobs / download ───────────────────────────────────────────


def test_job_not_found(client):
    c, _ = client
    r = c.get("/api/v1/jobs/does-not-exist")
    assert r.status_code == 404


def test_download_before_ready(client, monkeypatch, tmp_path: Path):
    c, _ = client
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(
        "pdf_tra.web.server.translate_pdf",
        lambda *a, **k: type("R", (), {"mono_pdf": None, "dual_pdf": None})(),
    )
    job_id = c.post("/api/v1/translate", json={"path": str(pdf)}).json()["job_id"]
    r = c.get(f"/api/v1/jobs/{job_id}/download/mono")
    assert r.status_code == 404


def test_download_invalid_kind(client, monkeypatch, tmp_path: Path):
    c, _ = client
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    mono = tmp_path / "m.pdf"
    mono.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "pdf_tra.web.server.translate_pdf",
        lambda *a, **k: type("R", (), {"mono_pdf": mono, "dual_pdf": None})(),
    )
    job_id = c.post("/api/v1/translate", json={"path": str(pdf)}).json()["job_id"]
    for _ in range(40):
        if c.get(f"/api/v1/jobs/{job_id}").json()["status"] == "done":
            break
        time.sleep(0.05)
    r = c.get(f"/api/v1/jobs/{job_id}/download/triple")
    assert r.status_code == 404


def test_job_done_flags_mono_only(client, monkeypatch, tmp_path: Path):
    c, _ = client
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    mono = tmp_path / "m.pdf"
    mono.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "pdf_tra.web.server.translate_pdf",
        lambda *a, **k: type("R", (), {"mono_pdf": mono, "dual_pdf": None})(),
    )
    job_id = c.post("/api/v1/translate", json={"path": str(pdf)}).json()["job_id"]
    for _ in range(40):
        body = c.get(f"/api/v1/jobs/{job_id}").json()
        if body["status"] == "done":
            break
        time.sleep(0.05)
    assert body["has_mono"] is True
    assert body["has_dual"] is False


# ── settings ──────────────────────────────────────────────────


def test_settings_api_key_too_short(client):
    c, _ = client
    r = c.put("/api/v1/settings", json={"api_key": "short"})
    assert r.status_code == 422


def test_settings_invalid_engine(client):
    c, _ = client
    r = c.put("/api/v1/settings", json={"translate_engine": "gpt"})
    assert r.status_code == 400
    assert "babeldoc" in r.json()["detail"]


def test_settings_missing_config_creates_on_save(client, tmp_path: Path):
    cfg = tmp_path / "new_config.json"
    uploads = tmp_path / "uploads"
    app = create_app(config_path=cfg, upload_dir=uploads)
    c = TestClient(app)
    r = c.put("/api/v1/settings", json={"api_key": "sk-brand-new-key12"})
    assert r.status_code == 200
    assert cfg.exists()
    assert r.json()["has_api_key"] is True


# ── 静态页 ────────────────────────────────────────────────────


def test_unknown_api_route(client):
    c, _ = client
    r = c.get("/api/v1/no-such-endpoint")
    assert r.status_code == 404
