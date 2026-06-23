import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pdf_tra.core.models import InspectResult, PdfInfo
from pdf_tra.web.server import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps(
            {
                "threads": 4,
                "translators": [
                    {
                        "name": "deepseek",
                        "envs": {"DEEPSEEK_API_KEY": "sk-test-key-12345678"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    app = create_app(config_path=cfg, upload_dir=tmp_path / "uploads")
    return TestClient(app)


def test_settings_get(client: TestClient):
    r = client.get("/api/v1/settings")
    assert r.status_code == 200
    assert r.json()["has_api_key"] is True


def test_settings_put(client: TestClient):
    r = client.put("/api/v1/settings", json={"api_key": "sk-new-key-abcdefgh"})
    assert r.status_code == 200
    assert r.json()["has_api_key"] is True


def test_spa_index(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_inspect_path(client: TestClient, monkeypatch, tmp_path: Path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    def fake_inspect(path, **kwargs):
        return InspectResult(
            input_path=path,
            pdf_info=PdfInfo(pages=3, encrypted=False),
            pdf_type="text",
            char_count=100,
            suggestion="可直接翻译",
            detected_lang="English",
            detected_lang_label="英语",
            can_translate=True,
        )

    monkeypatch.setattr("pdf_tra.web.server.inspect_pdf", fake_inspect)
    r = client.post("/api/v1/inspect/path", json={"path": str(pdf)})
    assert r.status_code == 200
    body = r.json()
    assert body["pages"] == 3
    assert body["can_translate"] is True


def test_capabilities(client: TestClient):
    r = client.get("/api/v1/capabilities")
    assert r.status_code == 200
    body = r.json()
    assert "ocr" in body
    assert "poppler" in body
    assert body["translate_engines"] == ["babeldoc", "classic"]
    assert "default_translate_engine" in body
    assert body["layout_polish_available"] is True


def test_translate_engine_and_polish_payload(client: TestClient, monkeypatch, tmp_path: Path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    captured = {}

    def fake_translate(path, out_dir, **kwargs):
        opts = kwargs.get("options")
        captured["engine"] = opts.translate_engine if opts else None
        captured["polish"] = opts.layout_polish if opts else None
        return type("R", (), {"mono_pdf": tmp_path / "m.pdf", "dual_pdf": tmp_path / "d.pdf"})()

    monkeypatch.setattr("pdf_tra.web.server.translate_pdf", fake_translate)
    r = client.post(
        "/api/v1/translate",
        json={"path": str(pdf), "engine": "classic", "polish": False},
    )
    assert r.status_code == 200
    assert captured["engine"] == "classic"
    assert captured["polish"] is False


def test_settings_put_layout_only(client: TestClient):
    r = client.put(
        "/api/v1/settings",
        json={"translate_engine": "classic", "layout_polish": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["translate_engine"] == "classic"
    assert body["layout_polish"] is False
    assert body["has_api_key"] is True


def test_translate_with_ocr_flag(client: TestClient, monkeypatch, tmp_path: Path):
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    captured = {}

    def fake_translate(path, out_dir, **kwargs):
        captured["ocr_mode"] = kwargs.get("options").ocr_mode if kwargs.get("options") else None
        return type("R", (), {"mono_pdf": tmp_path / "m.pdf", "dual_pdf": tmp_path / "d.pdf"})()

    monkeypatch.setattr("pdf_tra.web.server.translate_pdf", fake_translate)
    monkeypatch.setattr(
        "pdf_tra.web.server.inspect_pdf",
        lambda path, **kwargs: InspectResult(
            input_path=path,
            pdf_info=PdfInfo(pages=5, encrypted=False),
            pdf_type="scanned",
            char_count=0,
            suggestion="OCR",
            can_translate=True,
            needs_ocr=True,
            ocr_available=True,
        ),
    )

    r = client.post("/api/v1/translate", json={"path": str(pdf), "ocr": True})
    assert r.status_code == 200
    assert captured.get("ocr_mode") == "auto"


def test_translate_creates_job(client: TestClient, monkeypatch, tmp_path: Path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "pdf_tra.web.server.translate_pdf",
        lambda *a, **k: type("R", (), {"mono_pdf": tmp_path / "m.pdf", "dual_pdf": tmp_path / "d.pdf"})(),
    )
    monkeypatch.setattr(
        "pdf_tra.web.server.inspect_pdf",
        lambda path, **kwargs: InspectResult(
            input_path=path,
            pdf_info=PdfInfo(pages=1, encrypted=False),
            pdf_type="text",
            char_count=20,
            suggestion="ok",
            can_translate=True,
        ),
    )

    r = client.post("/api/v1/translate", json={"path": str(pdf)})
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    status = client.get(f"/api/v1/jobs/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] in {"pending", "running", "done", "error"}
