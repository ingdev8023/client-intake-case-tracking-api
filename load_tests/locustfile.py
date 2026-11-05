from locust import HttpUser, task, between


class APIUser(HttpUser):

    wait_time = between(1, 3)

    
    def on_start(self):
        response = self.client.post("/login", json={"user_email": "xxxxxxxxxx","user_password": "xxxxxxxxxxx"})
        response.raise_for_status()
        self.token = response.json()["access_token"]
        
    @task
    def cases(self):
        self.client.get("/cases?page=1&limit=10", headers={"Authorization": f"Bearer {self.token}" },)
    