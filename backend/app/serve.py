"""Production entrypoint: apply migrations, then serve, in a single Python process.

Importing the app takes ~5 s on the 1 vCPU server. Running Alembic and then the `fastapi` CLI
paid that twice, plus the CLI's own libraries; one process pays it once, which shortens the
downtime of every deploy (ADR 0010).
"""

from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def main() -> None:
    command.upgrade(Config(ALEMBIC_INI), "head")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # noqa: S104 (inside the container; only Caddy can reach it)
        port=8000,
        # The client IP comes from Caddy's X-Forwarded-For (login throttling, ADR 0008). Any
        # forwarder is trusted because no port is published and Caddy overwrites the header.
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
