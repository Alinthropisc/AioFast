from locust import HttpUser, task, between, SequentialTaskSet


class AuthFlow(SequentialTaskSet):

    @task
    def register(self):
        self.client.post("/api/v1/auth/register", json={
            "email": f"user_{self.user.user_id}@test.com",  # ty:ignore[unresolved-attribute]
            "password": "Test123!",
        })

    @task
    def login(self):
        resp = self.client.post("/api/v1/auth/login", json={
            "email": f"user_{self.user.user_id}@test.com",  # ty:ignore[unresolved-attribute]
            "password": "Test123!",
        })
        if resp.status_code == 200:
            self.user.token = resp.json().get("token")  # ty:ignore[unresolved-attribute]

    @task
    def protected_endpoint(self):
        token = getattr(self.user, "token", None)
        if token:
            self.client.get(
                "/api/v1/me",
                headers={"Authorization": f"Bearer {token}"},
            )


class AuthUser(HttpUser):
    wait_time = between(1, 3)
    tasks = [AuthFlow]
    host = "http://localhost:8000"
    user_id = 0

    def on_start(self):
        AuthUser.user_id += 1
        self.user_id = AuthUser.user_id