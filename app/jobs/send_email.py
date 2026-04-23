from core.queue import Job

class SendWelcomeEmail(Job):
    queue = "emails"
    retries = 3

    async def handle(self, user_id: int): ...






