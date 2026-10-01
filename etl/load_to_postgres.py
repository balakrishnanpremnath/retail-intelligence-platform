from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"

load_dotenv(ROOT_DIR / ".env")


# ---------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------

def create_database_engine():

    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    database = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")

    connection_url = (
        f"postgresql+psycopg2://"
        f"{user}:{password}@{host}:{port}/{database}"
    )

    return create_engine(connection_url)


# ---------------------------------------------------------
# LOAD RAW DATA
# ---------------------------------------------------------

def read_raw_datasets():

    datasets = {
        "stg_products": pd.read_csv(
            RAW_DATA_DIR / "products.csv"
        ),

        "stg_stores": pd.read_csv(
            RAW_DATA_DIR / "stores.csv"
        ),

        "stg_customers": pd.read_csv(
            RAW_DATA_DIR / "customers.csv"
        ),

        "stg_sales": pd.read_csv(
            RAW_DATA_DIR / "sales.csv"
        ),

        "stg_inventory": pd.read_csv(
            RAW_DATA_DIR / "inventory.csv"
        )
    }

    return datasets


# ---------------------------------------------------------
# BASIC DATA QUALITY CHECKS
# ---------------------------------------------------------

def validate_datasets(datasets):

    required_datasets = [
        "stg_products",
        "stg_stores",
        "stg_customers",
        "stg_sales",
        "stg_inventory"
    ]

    for dataset_name in required_datasets:

        if dataset_name not in datasets:
            raise ValueError(
                f"Missing dataset: {dataset_name}"
            )

        if datasets[dataset_name].empty:
            raise ValueError(
                f"{dataset_name} is empty."
            )

    print("Data validation passed.")


# ---------------------------------------------------------
# LOAD INTO POSTGRESQL STAGING
# ---------------------------------------------------------

def load_staging_tables(engine, datasets):

    with engine.begin() as connection:

        connection.execute(
            text(
                "CREATE SCHEMA IF NOT EXISTS staging;"
            )
        )

    for table_name, dataframe in datasets.items():

        dataframe.to_sql(
            name=table_name,
            con=engine,
            schema="staging",
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=1000
        )

        print(
            f"{table_name}: "
            f"{len(dataframe):,} rows loaded"
        )


# ---------------------------------------------------------
# VERIFY ROW COUNTS
# ---------------------------------------------------------

def verify_staging_tables(engine):

    table_names = [
        "stg_products",
        "stg_stores",
        "stg_customers",
        "stg_sales",
        "stg_inventory"
    ]

    print()
    print("PostgreSQL staging row counts:")

    with engine.connect() as connection:

        for table_name in table_names:

            query = text(
                f"""
                SELECT COUNT(*)
                FROM staging.{table_name}
                """
            )

            count = connection.execute(
                query
            ).scalar()

            print(
                f"{table_name:<20} {count:,}"
            )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print(
        "Connecting to PostgreSQL..."
    )

    engine = create_database_engine()

    with engine.connect() as connection:

        connection.execute(
            text("SELECT 1")
        )

    print(
        "Database connection successful."
    )

    datasets = read_raw_datasets()

    validate_datasets(
        datasets
    )

    print()
    print(
        "Loading raw datasets into staging..."
    )

    load_staging_tables(
        engine,
        datasets
    )

    verify_staging_tables(
        engine
    )

    print()
    print(
        "Staging ETL completed successfully."
    )


if __name__ == "__main__":
    main()