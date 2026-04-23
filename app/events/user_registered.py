from core.events import Event

class UserRegistered(Event):
    def __init__(self, user_id: int, email: str):
        self.user_id = user_id
        self.email = email