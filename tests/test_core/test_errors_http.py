"""Tests for http_status_for_exit_code."""

from pdf_tra.core.errors import ExitCode, http_status_for_exit_code


def test_file_not_found_is_404():
    assert http_status_for_exit_code(ExitCode.FILE_NOT_FOUND) == 404


def test_tool_not_found_is_503():
    assert http_status_for_exit_code(ExitCode.TOOL_NOT_FOUND) == 503


def test_config_error_is_400():
    assert http_status_for_exit_code(ExitCode.CONFIG_ERROR) == 400
