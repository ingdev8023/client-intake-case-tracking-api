from contextlib import contextmanager
from time import perf_counter

from sqlalchemy import event


@contextmanager
def measure_sql(engine):
    metrics = {
        "query_count": 0,
        "sql_time_ms": 0.0,
    }

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