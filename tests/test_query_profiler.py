from sqlalchemy import create_engine, text

from load_tests.query_profiler import measure_sql


def test_measure_sql_counts_queries():
    engine = create_engine("sqlite:///:memory:")

    try:
        with engine.connect() as connection:

            with measure_sql(engine) as metrics:
                connection.execute(text("SELECT 1"))
                connection.execute(text("SELECT 2"))
                connection.execute(text("SELECT 3"))

            assert metrics["query_count"] == 3
            assert metrics["sql_time_ms"] >= 0

            # Verify that the profiler stopped listening.
            connection.execute(text("SELECT 4"))

            assert metrics["query_count"] == 3

    finally:
        engine.dispose()