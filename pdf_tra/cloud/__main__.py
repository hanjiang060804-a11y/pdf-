from __future__ import annotations

import uvicorn

from pdf_tra.cloud.app import create_cloud_app


def main() -> None:
    uvicorn.run(create_cloud_app(), host="0.0.0.0", port=8787)


if __name__ == "__main__":
    main()
