import json
from pathlib import Path

import pytest

from pdf_tra.config.loader import read_settings, save_deepseek_settings, save_user_settings


def test_save_and_read_settings(tmp_path: Path):
    cfg = tmp_path / "config.json"
    save_deepseek_settings(cfg, "sk-test-key-abcdef12")
    assert cfg.exists()
    info = read_settings(cfg)
    assert info["has_api_key"] is True
    assert "****" in info["api_key_masked"]
    assert info["translate_engine"] == "babeldoc"
    assert info["layout_polish"] is True
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["translators"][0]["envs"]["DEEPSEEK_API_KEY"] == "sk-test-key-abcdef12"


def test_save_layout_settings_without_api_key(tmp_path: Path):
    cfg = tmp_path / "config.json"
    save_deepseek_settings(cfg, "sk-test-key-abcdef12")
    save_user_settings(cfg, translate_engine="classic", layout_polish=False)
    info = read_settings(cfg)
    assert info["translate_engine"] == "classic"
    assert info["layout_polish"] is False
    assert info["has_api_key"] is True
