"""Entrypoint dos containers `api` e `worker`.

Escrito em Python (em vez de shell) para nao depender de line endings LF, que
se perdem com facilidade em checkouts feitos no Windows.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time


def _run(cmd: list[str]) -> None:
    print(f"[entrypoint] $ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)


def _exec(cmd: list[str]) -> None:
    print(f"[entrypoint] exec: {' '.join(cmd)}", flush=True)
    os.execvp(cmd[0], cmd)


def _wait_for_database(attempts: int = 60, delay: float = 1.0) -> None:
    """Aguarda o Postgres aceitar conexoes antes de migrar."""
    import asyncio

    import asyncpg

    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")

    async def _probe() -> None:
        conn = await asyncpg.connect(url)
        await conn.close()

    for attempt in range(1, attempts + 1):
        try:
            asyncio.run(_probe())
            print("[entrypoint] banco de dados disponivel", flush=True)
            return
        except Exception as exc:  # noqa: BLE001 - qualquer falha aqui e "ainda nao pronto"
            if attempt == attempts:
                raise
            print(f"[entrypoint] aguardando banco ({attempt}/{attempts}): {exc}", flush=True)
            time.sleep(delay)


def main() -> None:
    role = sys.argv[1] if len(sys.argv) > 1 else "api"

    if role == "api":
        _wait_for_database()
        _run(["alembic", "upgrade", "head"])
        cmd = [
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ]
        if os.getenv("UVICORN_RELOAD", "true").lower() in {"1", "true", "yes"}:
            cmd.append("--reload")
        _exec(cmd)

    elif role == "worker":
        _wait_for_database()
        _exec(
            [
                "celery",
                "-A",
                "app.workers.celery_app.celery_app",
                "worker",
                "--loglevel=info",
                f"--concurrency={os.getenv('CELERY_CONCURRENCY', '2')}",
            ]
        )

    elif role == "migrate":
        _wait_for_database()
        _exec(["alembic", "upgrade", "head"])

    elif role == "seed":
        _wait_for_database()
        _exec(["python", "-m", "scripts.seed"])

    elif role == "test":
        _wait_for_database()
        _exec(["pytest", "-q", *sys.argv[2:]])

    else:
        _exec(sys.argv[1:])


if __name__ == "__main__":
    main()
