import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pdf_tra.cloud.app import create_cloud_app
from pdf_tra.cloud.settings import CloudSettings
from pdf_tra.core.models import InspectResult, PdfInfo


@pytest.fixture
def cloud_settings() -> CloudSettings:
    return CloudSettings(
        wechat_app_id="wx-test",
        wechat_app_secret="secret-test",
        jwt_secret="test-jwt-secret-key-32chars!!!!",
        daily_pages_per_user=100,
        dev_mode=True,
    )


@pytest.fixture
def cloud_client(tmp_path: Path, cloud_settings: CloudSettings):
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps(
            {
                "threads": 2,
                "translators": [
                    {"name": "deepseek", "envs": {"DEEPSEEK_API_KEY": "sk-test-key-12345678"}},
                ],
            }
        ),
        encoding="utf-8",
    )
    app = create_cloud_app(
        config_path=cfg,
        upload_dir=tmp_path / "uploads",
        settings=cloud_settings,
    )
    return TestClient(app)


def _auth_header(client: TestClient) -> dict[str, str]:
    r = client.post("/api/v2/auth/wechat", json={"code": "any-dev-code"})
    assert r.status_code == 200
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_wechat_dev_login(cloud_client: TestClient):
    r = cloud_client.post("/api/v2/auth/wechat", json={"code": "dev"})
    assert r.status_code == 200
    body = r.json()
    assert "token" in body
    assert body["openid_masked"] == "dev-****enid"


def test_inspect_requires_auth(cloud_client: TestClient):
    r = cloud_client.post(
        "/api/v1/inspect",
        files={"file": ("a.pdf", b"%PDF-1.4\n", "application/pdf")},
    )
    assert r.status_code == 401


def test_inspect_returns_file_id(cloud_client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "pdf_tra.cloud.app.inspect_pdf",
        lambda path, **kw: InspectResult(
            input_path=path,
            pdf_info=PdfInfo(pages=3, encrypted=False),
            pdf_type="text",
            char_count=50,
            suggestion="ok",
            can_translate=True,
        ),
    )
    headers = _auth_header(cloud_client)
    r = cloud_client.post(
        "/api/v1/inspect",
        headers=headers,
        files={"file": ("paper.pdf", b"%PDF-1.4\n", "application/pdf")},
    )
    assert r.status_code == 200
    body = r.json()
    assert "file_id" in body
    assert "path" not in body
    assert body["pages"] == 3


def test_job_isolation(cloud_client: TestClient, monkeypatch, tmp_path: Path):
    mono = tmp_path / "out-mono.pdf"
    mono.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "pdf_tra.cloud.app.inspect_pdf",
        lambda path, **kw: InspectResult(
            input_path=path,
            pdf_info=PdfInfo(pages=1, encrypted=False),
            pdf_type="text",
            char_count=10,
            suggestion="ok",
            can_translate=True,
        ),
    )
    monkeypatch.setattr(
        "pdf_tra.cloud.app.translate_pdf",
        lambda *a, **k: type("R", (), {"mono_pdf": mono, "dual_pdf": None})(),
    )

    h1 = _auth_header(cloud_client)
    inspect = cloud_client.post(
        "/api/v1/inspect",
        headers=h1,
        files={"file": ("a.pdf", b"%PDF-1.4\n", "application/pdf")},
    ).json()
    job_id = cloud_client.post(
        "/api/v1/translate",
        headers=h1,
        json={"file_id": inspect["file_id"]},
    ).json()["job_id"]

    # second user
    r2 = cloud_client.post("/api/v2/auth/wechat", json={"code": "dev"})
    # dev mode always same openid - use different token from forged openid test instead
    # For isolation test, patch verify to return different users
    from pdf_tra.cloud import auth as auth_mod

    settings = CloudSettings(
        wechat_app_id="x",
        wechat_app_secret="y",
        jwt_secret="test-jwt-secret-key-32chars!!!!",
        dev_mode=False,
    )
    token_b = auth_mod.create_token(settings, "other-user")
    h2 = {"Authorization": f"Bearer {token_b}"}

    assert cloud_client.get(f"/api/v1/jobs/{job_id}", headers=h2).status_code == 404
    assert cloud_client.get(f"/api/v1/jobs/{job_id}", headers=h1).status_code == 200


def test_me_quota(cloud_client: TestClient):
    headers = _auth_header(cloud_client)
    r = cloud_client.get("/api/v2/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["pages_limit_today"] == 100
    assert body["pages_remaining_today"] == 100
