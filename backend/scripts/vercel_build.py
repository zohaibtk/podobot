import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    public_dir = Path("public")
    public_dir.mkdir(parents=True, exist_ok=True)
    (public_dir / "vercel-build.txt").write_text(
        "PodoBot backend static output placeholder for Vercel.\n",
        encoding="utf-8",
    )

    if os.getenv("RUN_DB_MIGRATIONS", "0") != "1":
        print("Skipping database migrations. Set RUN_DB_MIGRATIONS=1 to run them during build.")
        return 0

    if not os.getenv("DATABASE_URL_OVERRIDE"):
        print(
            "Skipping database migrations because DATABASE_URL_OVERRIDE is not set. "
            "Set it in Vercel env vars to run migrations during build."
        )
        return 0

    subprocess.check_call([sys.executable, "-m", "alembic", "upgrade", "head"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
