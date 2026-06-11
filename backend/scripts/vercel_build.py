import os
import subprocess
import sys


def main() -> int:
    if os.getenv("RUN_DB_MIGRATIONS", "0") != "1":
        print("Skipping database migrations. Set RUN_DB_MIGRATIONS=1 to run them during build.")
        return 0

    if not os.getenv("DATABASE_URL_OVERRIDE"):
        print("DATABASE_URL_OVERRIDE is required to run Vercel database migrations.")
        return 1

    subprocess.check_call([sys.executable, "-m", "alembic", "upgrade", "head"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
