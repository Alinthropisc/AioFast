from __future__ import annotations

import pytest
from pydantic import Field

from core.validation.dto import DTO, UpdateDTO
from core.validation.errors import ValidationError


class CreateUserDTO(DTO):
    name: str = Field(min_length=2, max_length=50)
    email: str
    age: int = Field(default=18, ge=0)
    role: str = Field(default="user")


class UpdateUserDTO(UpdateDTO):
    name: str | None = None
    email: str | None = None
    age: int | None = None


class TestDTOCreate:
    def test_valid(self):
        dto = CreateUserDTO.create(
            {
                "name": "Alice",
                "email": "alice@test.com",
            }
        )
        assert dto.name == "Alice"
        assert dto.email == "alice@test.com"
        assert dto.age == 18  # default
        assert dto.role == "user"

    def test_invalid_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            CreateUserDTO.create({"name": "A", "email": "test@t.com"})
        assert exc_info.value.has("name")

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            CreateUserDTO.create({"age": 25})

    def test_extra_fields_ignored(self):
        dto = CreateUserDTO.create(
            {
                "name": "Alice",
                "email": "a@b.com",
                "unknown_field": "ignored",
            }
        )
        assert not hasattr(dto, "unknown_field")

    def test_strips_whitespace(self):
        dto = CreateUserDTO.create(
            {
                "name": "  Alice  ",
                "email": " a@b.com ",
            }
        )
        assert dto.name == "Alice"
        assert dto.email == "a@b.com"


class TestDTOCreateOrNone:
    def test_valid(self):
        dto = CreateUserDTO.create_or_none(
            {
                "name": "Alice",
                "email": "a@b.com",
            }
        )
        assert dto is not None

    def test_invalid(self):
        dto = CreateUserDTO.create_or_none({})
        assert dto is None


class TestDTOCreateMany:
    def test_valid(self):
        items = [
            {"name": "Alice", "email": "a@b.com"},
            {"name": "Bob", "email": "b@c.com"},
        ]
        dtos = CreateUserDTO.create_many(items)
        assert len(dtos) == 2
        assert dtos[0].name == "Alice"
        assert dtos[1].name == "Bob"


class TestDTOToDict:
    def test_to_dict(self):
        dto = CreateUserDTO.create({"name": "Alice", "email": "a@b.com"})
        d = dto.to_dict()
        assert d["name"] == "Alice"
        assert d["email"] == "a@b.com"
        assert d["age"] == 18
        assert d["role"] == "user"

    def test_to_dict_only(self):
        dto = CreateUserDTO.create({"name": "Alice", "email": "a@b.com"})
        d = dto.to_dict_only("name", "email")
        assert "name" in d
        assert "email" in d
        assert "age" not in d

    def test_to_dict_except(self):
        dto = CreateUserDTO.create({"name": "Alice", "email": "a@b.com"})
        d = dto.to_dict_except("role")
        assert "role" not in d
        assert "name" in d


class TestDTOFields:
    def test_fields(self):
        fields = CreateUserDTO.fields()
        assert "name" in fields
        assert "email" in fields
        assert "age" in fields

    def test_required_fields(self):
        required = CreateUserDTO.required_fields()
        assert "name" in required
        assert "email" in required
        assert "age" not in required  # has default


class TestDTORepr:
    def test_repr(self):
        dto = CreateUserDTO.create({"name": "Alice", "email": "a@b.com"})
        r = repr(dto)
        assert "CreateUserDTO" in r
        assert "Alice" in r


class TestUpdateDTO:
    def test_partial(self):
        dto = UpdateUserDTO.create({"name": "New Name"})
        assert dto.name == "New Name"
        assert dto.email is None
        assert dto.age is None

    def test_changes(self):
        dto = UpdateUserDTO.create({"name": "New", "age": 30})
        changes = dto.changes()
        assert changes == {"name": "New", "age": 30}
        assert "email" not in changes

    def test_has_changes(self):
        dto1 = UpdateUserDTO.create({"name": "X"})
        assert dto1.has_changes is True

        dto2 = UpdateUserDTO.create({})
        assert dto2.has_changes is False

    def test_empty_update(self):
        dto = UpdateUserDTO.create({})
        assert dto.changes() == {}
