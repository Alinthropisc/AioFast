# core/testing/database/conftest.py
from __future__ import annotations

import pytest_asyncio
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, or_
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.pool import StaticPool

from core.database.encryption import EncryptedString, HashedString
from core.database.manager import DatabaseConfig, DatabaseManager
from core.database.model import SoftDeleteMixin
from core.database.scopes import ScopeMixin, scope

# ── Base ──────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


# ── Test models ───────────────────────────────────────────
# (без изменений — все твои модели)


class User(Base):
    __tablename__ = "test_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    is_active = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user")
    age: Mapped[int] = mapped_column(Integer, default=0)
    created_at = mapped_column(DateTime)
    updated_at = mapped_column(DateTime)


class SoftUser(SoftDeleteMixin, Base):
    __tablename__ = "test_soft_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    created_at = mapped_column(DateTime)
    updated_at = mapped_column(DateTime)


class Product(Base):
    __tablename__ = "test_products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[float] = mapped_column(Float, default=0.0)
    category: Mapped[str] = mapped_column(String(50), default="general")
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at = mapped_column(DateTime)
    updated_at = mapped_column(DateTime)


class AuditedUser(Base):
    __tablename__ = "test_audited_users"
    __audit_exclude__ = {"secret"}  # пример
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    secret: Mapped[str | None] = mapped_column(String(255))
    created_at = mapped_column(DateTime)
    updated_at = mapped_column(DateTime)


class SecureRecord(Base):
    __tablename__ = "test_secure_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(100))
    secret_data: Mapped[str | None] = mapped_column(EncryptedString(key="test-encryption-key-123"), nullable=True)
    hashed_value: Mapped[str] = mapped_column(HashedString(algorithm="sha256"))
    created_at = mapped_column(DateTime)
    updated_at = mapped_column(DateTime)


class ObsUser(Base):
    __tablename__ = "test_obs_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    created_at = mapped_column(DateTime)
    updated_at = mapped_column(DateTime)


class Author(Base):
    __tablename__ = "test_authors"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    books: Mapped[list[Book]] = relationship(
        back_populates="author",
        lazy="noload",
    )
    created_at = mapped_column(DateTime)
    updated_at = mapped_column(DateTime)


class Book(Base):
    __tablename__ = "test_books"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("test_authors.id"),
    )
    author: Mapped[Author] = relationship(
        back_populates="books",
        lazy="noload",
    )
    created_at = mapped_column(DateTime)
    updated_at = mapped_column(DateTime)


class Post(Base):
    __tablename__ = "test_posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author_id: Mapped[int] = mapped_column(Integer)
    created_at = mapped_column(DateTime)
    updated_at = mapped_column(DateTime)


class TenantPost(Base):
    __tablename__ = "test_tenant_posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    tenant_id: Mapped[int] = mapped_column(Integer)
    created_at = mapped_column(DateTime)
    updated_at = mapped_column(DateTime)


class ScopedUser(ScopeMixin, Base):
    __tablename__ = "test_scoped_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String(50), default="user")
    created_at = mapped_column(DateTime)
    updated_at = mapped_column(DateTime)

    @scope
    def active(cls, query, *args):
        return query.where(cls.is_active)

    @scope
    def admins(cls, query, *args):
        return query.where(cls.role == "admin")

    @scope
    def by_role(cls, query, role: str, *args):
        return query.where(cls.role == role)

    @scope
    def search(cls, query, term: str, *args):
        return query.where(
            or_(
                cls.name.ilike(f"%{term}%"),  # ty:ignore[unresolved-attribute]
                cls.email.ilike(f"%{term}%"),  # ty:ignore[unresolved-attribute]
            )
        )


# ── Fixtures ──────────────────────────────────────────────


@pytest_asyncio.fixture
async def async_engine():
    """Engine с StaticPool — одно соединение для всех операций."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,  # ← КЛЮЧЕВОЙ ФИКС
        connect_args={"check_same_thread": False},  # ← для SQLite
    )

    # создаём таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # чистим
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_manager(async_engine):
    """DatabaseManager с уже готовым engine (таблицы созданы)."""
    manager = DatabaseManager()
    manager.add_connection(
        DatabaseConfig(
            name="default",
            url="sqlite+aiosqlite:///:memory:",
            echo=False,
        )
    )
    # Подменяем engine на тот, где уже есть таблицы
    manager._engines["default"] = async_engine
    manager._session_factories["default"] = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    yield manager
    # dispose делает async_engine fixture


@pytest_asyncio.fixture
async def session(async_engine):
    """Чистая сессия с откатом после каждого теста."""
    factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as sess, sess.begin():
        yield sess
        # автоматический rollback при выходе из begin()


@pytest_asyncio.fixture
async def seeded_session(async_engine):
    """Сессия с предзагруженными данными."""
    factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as sess:
        users = [
            User(name="Alice", email="alice@test.com", is_active=True, role="admin", age=30),
            User(name="Bob", email="bob@test.com", is_active=True, role="user", age=25),
            User(name="Charlie", email="charlie@test.com", is_active=False, role="user", age=35),
            User(name="Diana", email="diana@test.com", is_active=True, role="editor", age=28),
            User(name="Eve", email="eve@test.com", is_active=True, role="admin", age=22),
        ]
        products = [
            Product(name="Laptop", price=999.99, category="electronics", in_stock=True),
            Product(name="Mouse", price=29.99, category="electronics", in_stock=True),
            Product(name="Book", price=19.99, category="books", in_stock=False),
            Product(name="Pen", price=2.99, category="stationery", in_stock=True),
            Product(name="Desk", price=299.99, category="furniture", in_stock=True),
        ]
        session.add_all(users + products)  # ty:ignore[unresolved-attribute]
        await sess.flush()
        for item in users + products:
            await sess.refresh(item)
        yield sess
        await sess.rollback()
