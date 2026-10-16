
"""Local Docker smoke tests for Retail Intelligence Platform."""

import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]

VIEWS = [
    "analytics.vw_sales_detail",
    "analytics.vw_inventory_intelligence",
    "analytics.vw_customer_segments",
    "analytics.vw_monthly_sales",
]


def check_streamlit():
    url = "http://localhost:8501/_stcore/health"

    with urlopen(url, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(
                f"Streamlit returned HTTP {response.status}"
            )

    print("PASS - Streamlit health endpoint")


def check_database_view(view):
    sql = f"SELECT COUNT(*) FROM {view};"

    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "postgres",
        "sh",
        "-c",
        (
            'psql -U "$POSTGRES_USER" '
            '-d "$POSTGRES_DB" '
            f'-t -A -c "{sql}"'
        ),
    ]

    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or result.stdout.strip()
        )

    count = int(result.stdout.strip())

    if count <= 0:
        raise RuntimeError(f"{view} contains no records")

    print(f"PASS - {view}: {count:,} rows")


def main():
    print("Retail Intelligence - Docker Smoke Test")
    print("-" * 45)

    try:
        check_streamlit()

        for view in VIEWS:
            check_database_view(view)

    except Exception as error:
        print(f"\nFAIL - {error}")
        sys.exit(1)

    print("-" * 45)
    print("SUCCESS - All 5 smoke checks passed!")


if __name__ == "__main__":
    main()
