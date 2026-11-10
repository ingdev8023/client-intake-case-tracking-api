from locust import HttpUser, task, between
import os

PERF_EMAIL = os.environ["PERF_EMAIL"]
PERF_PASSWORD = os.environ["PERF_PASSWORD"]
PAGE = int(os.getenv("PERF_PAGE", "1"))
LIMIT = int(os.getenv("PERF_LIMIT", "10"))

WAIT_MIN = float(os.getenv("PERF_WAIT_MIN", "1"))
WAIT_MAX = float(os.getenv("PERF_WAIT_MAX", "3"))

class APIUser(HttpUser):

    wait_time = between(WAIT_MIN, WAIT_MAX)

    
    def on_start(self):
        response = self.client.post("/login", json={"user_email": PERF_EMAIL,
        "user_password": PERF_PASSWORD})
        response.raise_for_status()
        self.token = response.json()["access_token"]
        
    @task
    def cases(self):
         self.client.get(
        f"/cases?page={PAGE}&limit={LIMIT}",
        headers={"Authorization": f"Bearer {self.token}"},
        )
    