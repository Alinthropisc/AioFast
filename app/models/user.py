"""Example User model.

Extends :class:`~core.database.BaseModel`, which provides an auto-increment
``id`` plus ``created_at`` / ``updated_at`` timestamps.
"""

from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from core.database import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column()
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password: Mapped[str] = mapped_column()

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
