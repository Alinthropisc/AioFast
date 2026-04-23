from core.auth import Guard



class JWTGuard(Guard):
    async def authenticate(self, request) -> User | None:
        token = request.headers.get("Authorization")



