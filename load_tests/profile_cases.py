from getpass import getpass
from time import perf_counter

from sqlalchemy import text

from app import create_app
from app.extensions.extensions import db
from load_tests.query_profiler import measure_sql


app = create_app()

with app.app_context():

    # Safety: verify Flask's actual database connection
    with db.engine.connect() as connection:
        identity = tuple(
            connection.execute(
                text("SELECT current_user, current_database()")
            ).one()
        )

        total_cases = connection.execute(
            text("SELECT COUNT(*) FROM cases")
        ).scalar_one()

    if identity != ("client_perf_user", "client_intake_perf"):
        raise SystemExit(f"Wrong database or role: {identity}")

    if total_cases != 1000:
        raise SystemExit(
            f"Expected 1000 synthetic cases, found {total_cases}"
        )

    print("Performance database verified.")

    email = input("Performance admin email: ")
    password = getpass("Performance admin password: ")

    with app.test_client() as client:

        login = client.post(
            "/login",
            json={
                "user_email": email,
                "user_password": password,
            },
        )

        if login.status_code != 200:
            raise SystemExit("Performance admin login failed.")

        token = login.get_json()["access_token"]

        scenarios = [
            (1, 10),
            (1, 100),
            (50, 10),
        ]

        for page, limit in scenarios:

            # Clear ORM session state between scenarios
            db.session.remove()

            with measure_sql(db.engine) as metrics:
                start = perf_counter()

                response = client.get(
                    f"/cases?page={page}&limit={limit}",
                    headers={
                        "Authorization": f"Bearer {token}"
                    },
                )

                request_ms = (perf_counter() - start) * 1000

            if response.status_code != 200:
                raise SystemExit(
                    f"Unexpected HTTP status: {response.status_code}"
                )

            data = response.get_json()

            assert len(data["items"]) == limit
            assert data["pagination"]["total_items"] == 1000

            print(f"\nPage: {page}, Limit: {limit}")
            print(f"SQL statements: {metrics['query_count']}")
            print("SQL categories:")

            for category, count in sorted(metrics["by_category"].items()):
                print(f"  {category}: {count}")
                
            print(f"SQL execution: {metrics['sql_time_ms']:.2f} ms")
            print(f"Full request: {request_ms:.2f} ms")