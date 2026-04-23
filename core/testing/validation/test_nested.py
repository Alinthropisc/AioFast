from __future__ import annotations

from core.validation.nested import NestedValidator


class TestNestedBasic:
    def test_simple_nested(self):
        data = {"address": {"city": "NYC", "zip": "10001"}}
        v = NestedValidator(
            data,
            {
                "address.city": "required|string",
                "address.zip": "required|string",
            },
        )
        assert v.passes() is True

    def test_nested_missing(self):
        v = NestedValidator(
            {},
            {
                "address.city": "required",
            },
        )
        assert v.fails() is True
        assert v.errors.has_errors


class TestNestedWildcard:
    def test_array_validation(self):
        data = {
            "items": [
                {"name": "Widget", "quantity": 5},
                {"name": "Gadget", "quantity": 3},
            ],
        }
        v = NestedValidator(
            data,
            {
                "items.*.name": "required|string",
                "items.*.quantity": "required|integer",
            },
        )
        assert v.passes() is True

    def test_array_validation_fails(self):
        data = {
            "items": [
                {"name": "Widget", "quantity": 5},
                {"name": "", "quantity": -1},
            ],
        }
        v = NestedValidator(
            data,
            {
                "items.*.name": "required|string",
                "items.*.quantity": "required|integer|positive",
            },
        )
        assert v.fails() is True
        errors = v.errors.errors
        assert "items.1.name" in errors or "items.1.quantity" in errors

    def test_deep_nesting(self):
        data = {
            "orders": [
                {"items": [{"sku": "A1"}, {"sku": "B2"}]},
                {"items": [{"sku": "C3"}]},
            ],
        }
        v = NestedValidator(
            data,
            {
                "orders.*.items.*.sku": "required|string",
            },
        )
        assert v.passes() is True

    def test_validates_and_returns_data(self):
        data = {"items": [{"name": "A"}, {"name": "B"}]}
        v = NestedValidator(
            data,
            {
                "items.*.name": "required|string|min_length:1",
            },
        )
        clean = v.validate()
        assert "items.0.name" in clean or "0" in str(clean)


class TestNestedEmpty:
    def test_empty_array(self):
        data = {"items": []}
        v = NestedValidator(
            data,
            {
                "items.*.name": "required",
            },
        )
        # Empty array — no items to validate, passes
        assert v.passes() is True
