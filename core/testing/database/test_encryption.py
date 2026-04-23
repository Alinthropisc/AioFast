from __future__ import annotations

import pytest
from sqlalchemy import insert

from core.testing.database.conftest import Base as DatabaseBase
from core.testing.database.conftest import SecureRecord


@pytest.fixture(autouse=True)
async def _create_secure_table(db_manager):
    engine = db_manager.engine()
    async with engine.begin() as conn:
        await conn.run_sync(DatabaseBase.metadata.create_all)


class TestEncryptedString:
    @pytest.mark.asyncio
    async def test_encrypt_decrypt(self, session):
        record = SecureRecord(
            label="test",
            secret_data="my-secret-value",
            hashed_value="password",
        )
        session.add(record)
        await session.flush()
        await session.refresh(record)

        assert record.secret_data == "my-secret-value"

    @pytest.mark.asyncio
    async def test_stored_encrypted(self, session):
        record = SecureRecord(
            label="test2",
            secret_data="sensitive-info",
            hashed_value="pass",
        )
        session.add(record)
        await session.flush()

        from sqlalchemy import text

        result = await session.execute(text("SELECT secret_data FROM test_secure_records WHERE label = 'test2'"))
        raw = result.scalar_one()
        assert raw != "sensitive-info"
        assert len(raw) > len("sensitive-info")

    @pytest.mark.asyncio
    async def test_null_value(self, session):
        # Используем модель напрямую, без __table__
        await session.execute(
            insert(SecureRecord).values(
                label="null_test",
                secret_data=None,
                hashed_value="x",
            )
        )
        await session.flush()

    @pytest.mark.asyncio
    async def test_different_records_different_ciphertext(self, session):
        r1 = SecureRecord(label="r1", secret_data="same-value", hashed_value="a")
        r2 = SecureRecord(label="r2", secret_data="same-value", hashed_value="b")
        session.add_all([r1, r2])
        await session.flush()

        from sqlalchemy import text

        result = await session.execute(text("SELECT secret_data FROM test_secure_records WHERE label IN ('r1', 'r2')"))
        rows = result.fetchall()
        assert rows[0][0] != rows[1][0]


class TestHashedString:
    @pytest.mark.asyncio
    async def test_hash_stored(self, session):
        record = SecureRecord(
            label="hash_test",
            secret_data="x",
            hashed_value="my_password",
        )
        session.add(record)
        await session.flush()
        await session.refresh(record)

        assert record.hashed_value != "my_password"
        assert len(record.hashed_value) == 64

    @pytest.mark.asyncio
    async def test_hash_deterministic(self, session):
        import hashlib

        expected = hashlib.sha256(b"test123").hexdigest()

        record = SecureRecord(
            label="det_test",
            secret_data="x",
            hashed_value="test123",
        )
        session.add(record)
        await session.flush()
        await session.refresh(record)

        assert record.hashed_value == expected
