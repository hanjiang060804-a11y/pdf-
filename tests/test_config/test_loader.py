import json
from pathlib import Path

import pytest

from pdf_tra.config.loader import load_config, merge_env, validate_config
from pdf_tra.config.schema import clamp_threads
from pdf_tra.core.errors import ExitCode, PdfTraError


def test_load_config_from_file(fixtures_dir: Path):
    path = fixtures_dir / "config_valid.json"
    config = load_config(path)
    assert config["threads"] == 4
    assert config["translators"][0]["name"] == "deepseek"


def test_load_config_missing_file(tmp_path: Path):
    with pytest.raises(PdfTraError) as exc:
        load_config(tmp_path / "missing.json")
    assert exc.value.exit_code is ExitCode.CONFIG_ERROR


def test_load_config_invalid_json(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{invalid", encoding="utf-8")
    with pytest.raises(PdfTraError):
        load_config(bad)


def test_merge_env_overrides_api_key(monkeypatch, sample_config):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-env")
    merged = merge_env(sample_config)
    envs = merged["translators"][0]["envs"]
    assert envs["DEEPSEEK_API_KEY"] == "sk-from-env"


def test_validate_config_accepts_valid_key(sample_config):
    validate_config(sample_config)


def test_validate_config_rejects_placeholder_key(sample_config):
    bad = dict(sample_config)
    bad["translators"] = [
        {
            "name": "deepseek",
            "envs": {"DEEPSEEK_API_KEY": "sk-your-api-key-here"},
        }
    ]
    with pytest.raises(PdfTraError) as exc:
        validate_config(bad)
    assert exc.value.exit_code is ExitCode.CONFIG_ERROR


def test_validate_config_requires_api_key():
    with pytest.raises(PdfTraError) as exc:
        validate_config({"translators": [], "threads": 4, "max_threads": 8})
    assert exc.value.exit_code is ExitCode.CONFIG_ERROR


def test_validate_config_threads_range(sample_config):
    bad = dict(sample_config)
    bad["threads"] = 99
    with pytest.raises(PdfTraError):
        validate_config(bad)


def test_clamp_threads():
    assert clamp_threads(4, 8) == 4
    assert clamp_threads(16, 8) == 8
    with pytest.raises(ValueError):
        clamp_threads(0, 8)
