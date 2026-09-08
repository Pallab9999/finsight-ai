"""Launch the team Streamlit UI (app/main.py)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "main.py")],
        check=True,
        cwd=str(ROOT),
    )


if __name__ == "__main__":
    main()
