from __future__ import annotations

import pytest

from core.database.model import BaseModel
from core.database.relationships import EagerLoader
from core.testing.database.conftest import Author, Book

# ── Models with relationships ─────────────────────────────


@pytest.fixture(autouse=True)
async def _create_rel_tables(db_manager):
    engine = db_manager.engine()
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)


class TestEagerLoader:
    @pytest.mark.asyncio
    async def test_load_with_relation(self, session):
        author = Author(name="Tolkien")
        session.add(author)
        await session.flush()

        book1 = Book(title="LOTR", author_id=author.id)
        book2 = Book(title="Hobbit", author_id=author.id)
        session.add_all([book1, book2])
        await session.flush()

        loader = EagerLoader(session)

        loaded = await loader.load(Author, author.id, with_=["books"])
        assert loaded is not None
        assert loaded.name == "Tolkien"
        assert len(loaded.books) == 2

    @pytest.mark.asyncio
    async def test_load_many_with_relation(self, session):
        a1 = Author(name="Author1")
        a2 = Author(name="Author2")
        session.add_all([a1, a2])
        await session.flush()

        session.add_all(
            [
                Book(title="Book1", author_id=a1.id),
                Book(title="Book2", author_id=a1.id),
                Book(title="Book3", author_id=a2.id),
            ]
        )
        await session.flush()

        loader = EagerLoader(session)

        authors = await loader.load_many(Author, with_=["books"])
        assert len(authors) == 2
        total_books = sum(len(a.books) for a in authors)
        assert total_books == 3

    @pytest.mark.asyncio
    async def test_load_with_where(self, session):
        a1 = Author(name="FilterMe")
        a2 = Author(name="SkipMe")
        session.add_all([a1, a2])
        await session.flush()

        loader = EagerLoader(session)
        result = await loader.load_many(Author, where={"name": "FilterMe"})
        assert len(result) == 1
        assert result[0].name == "FilterMe"

    @pytest.mark.asyncio
    async def test_load_with_limit(self, session):
        for i in range(5):
            session.add(Author(name=f"Author{i}"))
        await session.flush()

        loader = EagerLoader(session)
        result = await loader.load_many(Author, limit=2)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_load_missing(self, session):
        loader = EagerLoader(session)
        result = await loader.load(Author, 9999)
        assert result is None

    @pytest.mark.asyncio
    async def test_load_with_dict_strategy(self, session):
        author = Author(name="Strategy")
        session.add(author)
        await session.flush()

        session.add(Book(title="SBook", author_id=author.id))
        await session.flush()

        loader = EagerLoader(session)
        loaded = await loader.load(
            Author,
            author.id,
            with_={"books": "selectin"},
        )
        assert loaded is not None
        assert len(loaded.books) == 1

    def test_repr(self, session):
        loader = EagerLoader(session)
        assert "EagerLoader" in repr(loader)
