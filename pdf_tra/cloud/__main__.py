from __future__ import annotations

import os

import uvicorn

from pdf_tra.cloud.app import create_cloud_app


def main() -> None:
    port = int(os.environ.get("PDF_TRA_PORT", "8787"))
    uvicorn.run(create_cloud_app(), host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
