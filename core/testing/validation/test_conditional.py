from __future__ import annotations

from core.validation.conditional import (
    Different,
    RequiredIf,
    RequiredUnless,
    RequiredWith,
    RequiredWithAll,
    RequiredWithout,
    Same,
    When,
)
from core.validation.rules import MinLength


class TestRequiredIf:
    def test_required_when_condition_met(self):
        r = RequiredIf("type", "business")
        r.set_data({"type": "business"})
        assert r.passes("tax_id", None) is False
        assert r.passes("tax_id", "123") is True

    def test_not_required_when_condition_not_met(self):
        r = RequiredIf("type", "business")
        r.set_data({"type": "personal"})
        assert r.passes("tax_id", None) is True


class TestRequiredUnless:
    def test_required_when_condition_not_met(self):
        r = RequiredUnless("role", "guest")
        r.set_data({"role": "admin"})
        assert r.passes("email", None) is False

    def test_not_required_when_condition_met(self):
        r = RequiredUnless("role", "guest")
        r.set_data({"role": "guest"})
        assert r.passes("email", None) is True


class TestRequiredWith:
    def test_required_when_other_present(self):
        r = RequiredWith("password")
        r.set_data({"password": "abc"})
        assert r.passes("password_confirmation", None) is False
        assert r.passes("password_confirmation", "abc") is True

    def test_not_required_when_other_absent(self):
        r = RequiredWith("password")
        r.set_data({})
        assert r.passes("password_confirmation", None) is True


class TestRequiredWithout:
    def test_required_when_other_absent(self):
        r = RequiredWithout("email")
        r.set_data({})
        assert r.passes("phone", None) is False

    def test_not_required_when_other_present(self):
        r = RequiredWithout("email")
        r.set_data({"email": "a@b.com"})
        assert r.passes("phone", None) is True


class TestRequiredWithAll:
    def test_required_when_all_present(self):
        r = RequiredWithAll("first_name", "last_name")
        r.set_data({"first_name": "A", "last_name": "B"})
        assert r.passes("middle_name", None) is False

    def test_not_required_when_some_missing(self):
        r = RequiredWithAll("first_name", "last_name")
        r.set_data({"first_name": "A"})
        assert r.passes("middle_name", None) is True


class TestSame:
    def test_matches(self):
        r = Same("password")
        r.set_data({"password": "abc"})
        assert r.passes("confirm", "abc") is True

    def test_not_matches(self):
        r = Same("password")
        r.set_data({"password": "abc"})
        assert r.passes("confirm", "xyz") is False


class TestDifferent:
    def test_different(self):
        r = Different("old_password")
        r.set_data({"old_password": "old"})
        assert r.passes("new_password", "new") is True

    def test_same(self):
        r = Different("old_password")
        r.set_data({"old_password": "same"})
        assert r.passes("new_password", "same") is False


class TestWhen:
    def test_condition_met(self):
        r = When(lambda d: d.get("type") == "business", MinLength(5))
        r.set_data({"type": "business"})
        assert r.passes("name", "AB") is False
        assert r.passes("name", "ABCDE") is True

    def test_condition_not_met(self):
        r = When(lambda d: d.get("type") == "business", MinLength(5))
        r.set_data({"type": "personal"})
        assert r.passes("name", "AB") is True  # skipped
