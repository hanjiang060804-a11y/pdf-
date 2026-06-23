from pdf_tra.core.errors import ExitCode, PdfTraError


def test_exit_code_values():
    assert ExitCode.OK == 0
    assert ExitCode.FILE_NOT_FOUND == 1
    assert ExitCode.SCANNED_PDF == 7
    assert ExitCode.TOOL_NOT_FOUND == 10


def test_pdf_tra_error_carries_exit_code():
    err = PdfTraError("missing file", ExitCode.FILE_NOT_FOUND)
    assert err.message == "missing file"
    assert err.exit_code is ExitCode.FILE_NOT_FOUND
    assert str(err) == "missing file"
