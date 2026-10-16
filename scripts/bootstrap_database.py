
"""Safely initialize a NEW Retail Intelligence PostgreSQL database.

Default behavior is read-only.
Existing application schemas are never overwritten.
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")


def database_engine():
    required = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]

    missing = [key for key in required if not os.getenv(key)]

    if missing:
        raise ValueError(
            "Missing database settings: " + ", ".join(missing)
        )

    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        database=os.environ["POSTGRES_DB"],
    )

    return create_engine(url)


def find_application_schemas(engine):
    """Read-only check: does application data already exist?"""

    query = text("""
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name IN (
            'staging', 'warehouse', 'analytics'
        )
        ORDER BY schema_name
    """)

    with engine.connect() as connection:
        return connection.execute(query).scalars().all()


def run_sql_file(engine, filename):
    """Execute an existing SQL script as one transaction."""

    path = ROOT / "database" / "sql" / filename

    sql = path.read_text(encoding="utf-8")

    with engine.begin() as connection:
        connection.exec_driver_sql(sql)

    print(f"PASS - {filename}")


def check_required_files():
    files = [
        "data/raw/products.csv",
        "data/raw/stores.csv",
        "data/raw/customers.csv",
        "data/raw/sales.csv",
        "data/raw/inventory.csv",
        "models/customer_segments.csv",
        "models/reorder_recommendations.csv",
        "database/sql/01_create_schema.sql",
        "database/sql/02_load_warehouse.sql",
        "database/sql/05_powerbi_views.sql",
    ]

    missing = [
        file for file in files
        if not (ROOT / file).is_file()
    ]

    if missing:
        raise FileNotFoundError(
            "Required files missing:\n" + "\n".join(missing)
        )

    print("PASS - All bootstrap input files available")


def initialize_database(engine):
    from etl.load_to_postgres import (
        read_raw_datasets,
        validate_datasets,
        load_staging_tables,
    )
    from etl.load_analytics_to_postgres import (
        load_analytics_data,
        load_to_postgres,
    )

    print("\nInitializing NEW database...")

    datasets = read_raw_datasets()
    validate_datasets(datasets)

    print("\n1. Loading staging tables")
    load_staging_tables(engine, datasets)

    print("\n2. Creating warehouse tables")
    run_sql_file(engine, "01_create_schema.sql")

    print("\n3. Loading dimensional warehouse")
    run_sql_file(engine, "02_load_warehouse.sql")

    print("\n4. Loading analytics tables")
    segments, reorder = load_analytics_data()
    load_to_postgres(engine, segments, reorder)

    print("\n5. Creating analytics views")
    run_sql_file(engine, "05_powerbi_views.sql")

    print("\nSUCCESS - Database initialization completed")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--initialize",
        action="store_true",
        help="Initialize a fresh database only",
    )

    args = parser.parse_args()

    check_required_files()

    engine = database_engine()

    try:
        existing = find_application_schemas(engine)

        if existing:
            print(
                "\nExisting application schemas:",
                ", ".join(existing),
            )

            if args.initialize:
                raise SystemExit(
                    "REFUSED: Existing database detected. "
                    "No changes were made."
                )

            print("SAFE CHECK - Database left unchanged.")
            return

        print("\nNo application schemas found.")

        if not args.initialize:
            print(
                "SAFE CHECK - Fresh database detected. "
                "Use --initialize only for a new database."
            )
            return

        initialize_database(engine)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
