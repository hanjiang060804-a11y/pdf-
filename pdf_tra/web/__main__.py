from __future__ import annotations

import uvicorn

from pdf_tra.web.server import create_app

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7860


def main() -> None:
    app = create_app()
    uvicorn.run(app, host=DEFAULT_HOST, port=DEFAULT_PORT, log_level="info")


if __name__ == "__main__":
    main()
