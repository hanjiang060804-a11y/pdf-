from enum import IntEnum


class ExitCode(IntEnum):
    OK = 0
    FILE_NOT_FOUND = 1
    CONFIG_ERROR = 2
    EXTERNAL_CMD_FAILED = 3
    NOT_PDF = 4
    PDF_CORRUPT = 5
    PDF_ENCRYPTED = 6
    SCANNED_PDF = 7
    INVALID_LANGUAGE = 8
    IO_ERROR = 9
    TOOL_NOT_FOUND = 10
    CONFIRMATION_REQUIRED = 11


class PdfTraError(Exception):
    """Application error mapped to a process exit code."""

    def __init__(self, message: str, exit_code: ExitCode = ExitCode.EXTERNAL_CMD_FAILED):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


def http_status_for_exit_code(code: ExitCode) -> int:
    """Map domain exit codes to HTTP status for Web API."""
    if code == ExitCode.FILE_NOT_FOUND:
        return 404
    if code == ExitCode.TOOL_NOT_FOUND:
        return 503
    return 400
