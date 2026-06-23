import json
from pathlib import Path

import pytest

from pdf_tra.config.loader import load_config, merge_env, validate_config
from pdf_tra.core.errors import ExitCode, PdfTraError


def test_load_config_none_uses_defaults(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    config = load_config(None)
    assert config["threads"] == 4
    assert config["max_threads"] == 8


def test_load_config_non_object_root(tmp_path: Path):
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(PdfTraError) as exc:
        load_config(path)
    assert exc.value.exit_code is ExitCode.CONFIG_ERROR


def test_load_config_empty_file(tmp_path: Path):
    path = tmp_path / "empty.json"
    path.write_text("", encoding="utf-8")
    with pytest.raises(PdfTraError):
        load_config(path)


def test_merge_env_creates_deepseek_translator_when_missing(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-new")
    merged = merge_env({"translators": []})
    assert len(merged["translators"]) == 1
    assert merged["translators"][0]["name"] == "deepseek"
    assert merged["translators"][0]["envs"]["DEEPSEEK_API_KEY"] == "sk-new"


def test_merge_env_only_model(monkeypatch, sample_config):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    merged = merge_env(sample_config)
    envs = merged["translators"][0]["envs"]
    assert envs["DEEPSEEK_MODEL"] == "deepseek-reasoner"


def test_merge_env_no_vars_unchanged(sample_config, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    merged = merge_env(sample_config)
    assert merged["translators"][0]["envs"]["DEEPSEEK_API_KEY"] == "sk-test-key-12345"


def test_validate_config_threads_zero(sample_config):
    bad = dict(sample_config)
    bad["threads"] = 0
    with pytest.raises(PdfTraError) as exc:
        validate_config(bad)
    assert exc.value.exit_code is ExitCode.CONFIG_ERROR


def test_validate_config_threads_negative(sample_config):
    bad = dict(sample_config)
    bad["threads"] = -1
    with pytest.raises(PdfTraError):
        validate_config(bad)


def test_validate_config_threads_at_max(sample_config):
    ok = dict(sample_config)
    ok["threads"] = 8
    ok["max_threads"] = 8
    validate_config(ok)


def test_validate_config_invalid_translators_type(sample_config):
    bad = dict(sample_config)
    bad["translators"] = "not-a-list"
    with pytest.raises(PdfTraError):
        validate_config(bad)


def test_validate_config_invalid_threads_type(sample_config):
    bad = dict(sample_config)
    bad["threads"] = "four"
    with pytest.raises(PdfTraError):
        validate_config(bad)


def test_load_config_partial_override(tmp_path: Path, fixtures_dir: Path):
    base = json.loads((fixtures_dir / "config_valid.json").read_text(encoding="utf-8"))
    base["threads"] = 2
    path = tmp_path / "partial.json"
    path.write_text(json.dumps(base), encoding="utf-8")
    config = load_config(path)
    assert config["threads"] == 2
    assert config["max_threads"] == 8
