from statistics import median
from time import perf_counter

from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload

from app import create_app
from app.extensions.extensions import db
from app.models.models import Case
from load_tests.query_profiler import measure_sql


def fetch_cases(strategy):
    # Prevent previously loaded ORM objects from affecting results.
    db.session.remove()

    query = (
        select(Case)
        .where(Case.is_deleted.is_(False))
        .order_by(Case.created_at.desc())
        .limit(100)
        .offset(0)
    )

    if strategy == "eager":
        query = query.options(
            selectinload(Case.client),
            selectinload(Case.assigned_users),
        )

    try:
        with measure_sql(db.engine) as metrics:
            start = perf_counter()

            total = db.session.scalar(
                select(func.count())
                .select_from(Case)
                .where(Case.is_deleted.is_(False))
            )

            cases = db.session.scalars(query).all()

            # Same serialization code in both experiments.
            items = [case.serialize() for case in cases]

            elapsed_ms = (perf_counter() - start) * 1000

        assert total == 1000
        assert len(items) == 100

        return {
            "items": items,
            "queries": metrics["query_count"],
            "sql_ms": metrics["sql_time_ms"],
            "elapsed_ms": elapsed_ms,
        }

    finally:
        db.session.remove()


def main():
    app = create_app()

    with app.app_context():
        # Safety guard: refuse to profile the original database.
        with db.engine.connect() as conn:
            identity = tuple(
                conn.execute(
                    text("SELECT current_user, current_database()")
                ).one()
            )

        if identity != ("client_perf_user", "client_intake_perf"):
            raise SystemExit(f"Wrong database: {identity}")

        print("Performance database verified.")

        measurements = {"lazy": [], "eager": []}

        # First pair is a warm-up; five subsequent pairs are measured.
        for trial in range(6):
            order = (
                ("lazy", "eager")
                if trial % 2 == 0
                else ("eager", "lazy")
            )

            results = {}

            for strategy in order:
                results[strategy] = fetch_cases(strategy)

            # Ensure optimization does not change the returned records.
            assert results["lazy"]["items"] == results["eager"]["items"]

            if trial == 0:
                print("Warm-up completed.")
                continue

            print(f"\nTrial {trial}")

            for strategy in ("lazy", "eager"):
                result = results[strategy]
                measurements[strategy].append(result)

                print(
                    f"{strategy}: "
                    f"{result['queries']} queries | "
                    f"{result['sql_ms']:.2f} ms SQL | "
                    f"{result['elapsed_ms']:.2f} ms total"
                )

        print("\nMEDIAN RESULTS")

        for strategy, readings in measurements.items():
            print(
                f"{strategy}: "
                f"{median(r['queries'] for r in readings)} queries | "
                f"{median(r['sql_ms'] for r in readings):.2f} ms SQL | "
                f"{median(r['elapsed_ms'] for r in readings):.2f} ms total"
            )


if __name__ == "__main__":
    main()