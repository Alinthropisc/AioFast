from locust import HttpUser, task, between, events


class APIUser(HttpUser):
    wait_time = between(0.1, 0.5)
    host = "http://localhost:8000"

    @task(10)
    def health_check(self):
        self.client.get("/health")

    @task(5)
    def api_list(self):
        self.client.get("/api/v1/items")

    @task(3)
    def api_create(self):
        self.client.post("/api/v1/items", json={
            "name": "test",
            "value": 42,
        })

    @task(1)
    def api_detail(self):
        self.client.get("/api/v1/items/1")






