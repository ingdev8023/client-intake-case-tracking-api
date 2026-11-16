from contextlib import contextmanager
from time import perf_counter

from sqlalchemy import event


@contextmanager
def measure_sql(engine):
    metrics = {
        "query_count": 0,
        "sql_time_ms": 0.0,
        "by_category": {},
    }

    def classify_sql(statement):
        """Classify SQL by referenced tables without exposing parameters."""

        sql = " ".join(statement.lower().split())

        if "users_cases" in sql:
            return "assigned_users"

        if "from client" in sql or "join client" in sql:
            return "clients"

        if 'from "user"' in sql or "from user" in sql:
            return "users"

        if "from cases" in sql or "join cases" in sql:
            return "cases"

        return "other"

    def before_execute(
        conn, cursor, statement,
        parameters, context, executemany
    ):
        context._query_start = perf_counter()

    def after_execute(
        conn, cursor, statement,
        parameters, context, executemany
    ):
        elapsed = perf_counter() - context._query_start

        metrics["query_count"] += 1
        metrics["sql_time_ms"] += elapsed * 1000
        category = classify_sql(statement)

        metrics["by_category"][category] = (
            metrics["by_category"].get(category, 0) + 1
        )   

    event.listen(
        engine, "before_cursor_execute", before_execute
    )
    event.listen(
        engine, "after_cursor_execute", after_execute
    )

    try:
        yield metrics
    finally:
        event.remove(
            engine, "before_cursor_execute", before_execute
        )
        event.remove(
            engine, "after_cursor_execute", after_execute
        )