import pytest

from pdf_tra.config.schema import DEFAULT_CONFIG, clamp_threads


def test_default_config_values():
    assert DEFAULT_CONFIG["threads"] == 4
    assert DEFAULT_CONFIG["max_threads"] == 8
    assert "PDF2ZH_LANG_FROM" in DEFAULT_CONFIG


def test_clamp_threads_boundary_min():
    assert clamp_threads(1, 8) == 1


def test_clamp_threads_boundary_max():
    assert clamp_threads(8, 8) == 8


def test_clamp_threads_above_max_clamped():
    assert clamp_threads(100, 8) == 8


@pytest.mark.parametrize("invalid", [0, -1, -100])
def test_clamp_threads_rejects_non_positive(invalid):
    with pytest.raises(ValueError):
        clamp_threads(invalid, 8)
