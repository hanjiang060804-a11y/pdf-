from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

from pdf_tra.config.schema import DEFAULT_CONFIG
from pdf_tra.core.errors import ExitCode, PdfTraError


def load_config(path: Path | None) -> dict:
    config = deepcopy(DEFAULT_CONFIG)
    if path is None:
        return merge_env(config)
    if not path.exists():
        raise PdfTraError(f"配置文件不存在: {path}", ExitCode.CONFIG_ERROR)
    try:
        with path.open(encoding="utf-8") as f:
            file_config = json.load(f)
    except json.JSONDecodeError as exc:
        raise PdfTraError(f"配置文件 JSON 无效: {path}", ExitCode.CONFIG_ERROR) from exc
    if not isinstance(file_config, dict):
        raise PdfTraError("配置文件根节点必须是 JSON 对象", ExitCode.CONFIG_ERROR)
    config.update(file_config)
    config = _sanitize_config(config)
    return merge_env(config)


def _sanitize_config(config: dict) -> dict:
    cleaned = deepcopy(config)
    noto = cleaned.get("NOTO_FONT_PATH")
    if isinstance(noto, str) and noto.strip():
        if not Path(noto).exists():
            cleaned["NOTO_FONT_PATH"] = ""
    return cleaned


def merge_env(config: dict) -> dict:
    merged = deepcopy(config)
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    model = os.environ.get("DEEPSEEK_MODEL")
    base_url = os.environ.get("DEEPSEEK_BASE_URL")
    if not any([api_key, model, base_url]):
        return merged

    translators = merged.setdefault("translators", [])
    deepseek = _find_translator(translators, "deepseek")
    if deepseek is None:
        deepseek = {"name": "deepseek", "envs": {}}
        translators.append(deepseek)
    envs = deepseek.setdefault("envs", {})
    if api_key:
        envs["DEEPSEEK_API_KEY"] = api_key
    if model:
        envs["DEEPSEEK_MODEL"] = model
    if base_url:
        envs["DEEPSEEK_BASE_URL"] = base_url
    return merged


def validate_config(config: dict) -> None:
    translators = config.get("translators", [])
    if not isinstance(translators, list):
        raise PdfTraError("translators 必须是数组", ExitCode.CONFIG_ERROR)

    key = _resolve_deepseek_api_key(config)
    if not key or key.startswith("sk-your-"):
        raise PdfTraError(
            "未配置 DEEPSEEK_API_KEY，请编辑 config.json 或设置环境变量",
            ExitCode.CONFIG_ERROR,
        )

    threads = config.get("threads", DEFAULT_CONFIG["threads"])
    max_threads = config.get("max_threads", DEFAULT_CONFIG["max_threads"])
    if not isinstance(threads, int) or not isinstance(max_threads, int):
        raise PdfTraError("threads 与 max_threads 必须是整数", ExitCode.CONFIG_ERROR)
    if threads < 1 or threads > max_threads:
        raise PdfTraError(
            f"threads 必须在 1~{max_threads} 之间，当前为 {threads}",
            ExitCode.CONFIG_ERROR,
        )


def mask_api_key(key: str | None) -> str:
    if not key or len(key) < 8:
        return ""
    return f"{key[:3]}****{key[-4:]}"


def save_deepseek_settings(config_path: Path, api_key: str) -> None:
    save_user_settings(config_path, api_key=api_key)


def save_user_settings(
    config_path: Path,
    *,
    api_key: str | None = None,
    translate_engine: str | None = None,
    layout_polish: bool | None = None,
) -> None:
    if config_path.exists():
        with config_path.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise PdfTraError("配置文件根节点必须是 JSON 对象", ExitCode.CONFIG_ERROR)
    else:
        data = deepcopy(DEFAULT_CONFIG)

    if api_key is not None:
        translators = data.setdefault("translators", [])
        deepseek = _find_translator(translators, "deepseek")
        if deepseek is None:
            deepseek = {"name": "deepseek", "envs": {}}
            translators.append(deepseek)
        envs = deepseek.setdefault("envs", {})
        envs["DEEPSEEK_API_KEY"] = api_key.strip()
        if "DEEPSEEK_MODEL" not in envs:
            envs["DEEPSEEK_MODEL"] = "deepseek-chat"
        if "DEEPSEEK_BASE_URL" not in envs:
            envs["DEEPSEEK_BASE_URL"] = "https://api.deepseek.com/v1"

    if translate_engine is not None:
        if translate_engine not in {"babeldoc", "classic"}:
            raise PdfTraError("translate_engine 必须是 babeldoc 或 classic", ExitCode.CONFIG_ERROR)
        data["translate_engine"] = translate_engine
    if layout_polish is not None:
        data["layout_polish"] = layout_polish

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def read_settings(config_path: Path) -> dict:
    if config_path.exists():
        config = load_config(config_path)
    else:
        config = load_config(None)
    key = _resolve_deepseek_api_key(config)
    deepseek = _find_translator(config.get("translators", []), "deepseek") or {}
    envs = deepseek.get("envs", {}) if isinstance(deepseek, dict) else {}
    model = envs.get("DEEPSEEK_MODEL", "deepseek-chat") if isinstance(envs, dict) else "deepseek-chat"
    return {
        "has_api_key": bool(key and not key.startswith("sk-your-")),
        "api_key_masked": mask_api_key(key),
        "model": model,
        "config_path": str(config_path),
        "translate_engine": config.get("translate_engine", "babeldoc"),
        "translate_fallback": bool(config.get("translate_fallback", True)),
        "layout_polish": bool(config.get("layout_polish", True)),
        "translate_engines": ["babeldoc", "classic"],
    }


def _find_translator(translators: list, name: str) -> dict | None:
    for item in translators:
        if isinstance(item, dict) and item.get("name") == name:
            return item
    return None


def _resolve_deepseek_api_key(config: dict) -> str | None:
    env_key = os.environ.get("DEEPSEEK_API_KEY")
    if env_key:
        return env_key
    translators = config.get("translators", [])
    deepseek = _find_translator(translators, "deepseek")
    if not deepseek:
        return None
    envs = deepseek.get("envs", {})
    if isinstance(envs, dict):
        value = envs.get("DEEPSEEK_API_KEY")
        return value if isinstance(value, str) else None
    return None
