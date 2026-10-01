from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]

MODEL_DIR = ROOT_DIR / "models"

load_dotenv(
    ROOT_DIR / ".env"
)


# ---------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------

def create_database_engine():

    host = os.getenv(
        "POSTGRES_HOST"
    )

    port = os.getenv(
        "POSTGRES_PORT"
    )

    database = os.getenv(
        "POSTGRES_DB"
    )

    user = os.getenv(
        "POSTGRES_USER"
    )

    password = os.getenv(
        "POSTGRES_PASSWORD"
    )

    connection_url = (
        f"postgresql+psycopg2://"
        f"{user}:{password}@"
        f"{host}:{port}/{database}"
    )

    return create_engine(
        connection_url
    )


# ---------------------------------------------------------
# LOAD ANALYTICS FILES
# ---------------------------------------------------------

def load_analytics_data():

    customer_segments = pd.read_csv(
        MODEL_DIR
        / "customer_segments.csv"
    )

    reorder_recommendations = pd.read_csv(
        MODEL_DIR
        / "reorder_recommendations.csv"
    )

    return (
        customer_segments,
        reorder_recommendations
    )


# ---------------------------------------------------------
# LOAD TO POSTGRESQL
# ---------------------------------------------------------

def load_to_postgres(
    engine,
    customer_segments,
    reorder_recommendations
):

    with engine.begin() as connection:

        connection.execute(
            text(
                """
                CREATE SCHEMA
                IF NOT EXISTS analytics;
                """
            )
        )

    customer_segments.to_sql(
        name="customer_segments",
        con=engine,
        schema="analytics",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000
    )

    reorder_recommendations.to_sql(
        name="reorder_recommendations",
        con=engine,
        schema="analytics",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000
    )


# ---------------------------------------------------------
# VERIFY
# ---------------------------------------------------------

def verify(engine):

    queries = {
        "customer_segments":
            """
            SELECT COUNT(*)
            FROM analytics.customer_segments
            """,

        "reorder_recommendations":
            """
            SELECT COUNT(*)
            FROM analytics.reorder_recommendations
            """
    }

    print()
    print(
        "Analytics table row counts:"
    )

    with engine.connect() as connection:

        for table, query in queries.items():

            count = connection.execute(
                text(query)
            ).scalar()

            print(
                f"{table:<28} "
                f"{count:,}"
            )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print(
        "Connecting to PostgreSQL..."
    )

    engine = (
        create_database_engine()
    )

    with engine.connect() as connection:

        connection.execute(
            text("SELECT 1")
        )

    print(
        "Database connection successful."
    )

    (
        customer_segments,
        reorder_recommendations
    ) = load_analytics_data()

    print(
        "Loading analytics datasets..."
    )

    load_to_postgres(
        engine,
        customer_segments,
        reorder_recommendations
    )

    verify(
        engine
    )

    print()
    print(
        "Analytics layer loaded successfully."
    )


if __name__ == "__main__":
    main()