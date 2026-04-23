from __future__ import annotations

from core.validation.rules import (
    DateAfter,
    DateBefore,
    DateFormat,
    IpAddress,
    Json,
    Password,
    Uuid,
)


class TestPassword:
    def test_min_length(self):
        r = Password(min_length=8)
        assert r.passes("f", "12345678") is True
        assert r.passes("f", "1234567") is False

    def test_uppercase(self):
        r = Password(uppercase=True)
        assert r.passes("f", "abcdefgh") is False
        assert r.passes("f", "Abcdefgh") is True

    def test_numbers(self):
        r = Password(numbers=True)
        assert r.passes("f", "abcdefgh") is False
        assert r.passes("f", "abcdefg1") is True

    def test_symbols(self):
        r = Password(symbols=True)
        assert r.passes("f", "abcdefgh") is False
        assert r.passes("f", "abcdefg!") is True

    def test_full(self):
        r = Password(min_length=8, uppercase=True, numbers=True, symbols=True)
        assert r.passes("f", "Abcdef1!") is True
        assert r.passes("f", "abcdef1!") is False  # no uppercase
        assert r.passes("f", "Abcdefg!") is False  # no number


class TestDateFormat:
    def test_valid(self):
        assert DateFormat().passes("f", "2024-01-15") is True
        assert DateFormat("%d/%m/%Y").passes("f", "15/01/2024") is True

    def test_invalid(self):
        assert DateFormat().passes("f", "not-a-date") is False
        assert DateFormat().passes("f", "15/01/2024") is False


class TestDateBefore:
    def test_before(self):
        r = DateBefore("2025-01-01")
        assert r.passes("f", "2024-12-31") is True
        assert r.passes("f", "2025-01-02") is False


class TestDateAfter:
    def test_after(self):
        r = DateAfter("2024-01-01")
        assert r.passes("f", "2024-01-02") is True
        assert r.passes("f", "2023-12-31") is False


class TestIpAddress:
    def test_valid_ipv4(self):
        assert IpAddress().passes("f", "192.168.1.1") is True
        assert IpAddress().passes("f", "10.0.0.1") is True

    def test_valid_ipv6(self):
        assert IpAddress().passes("f", "::1") is True
        assert IpAddress().passes("f", "2001:db8::1") is True

    def test_invalid(self):
        assert IpAddress().passes("f", "999.999.999.999") is False
        assert IpAddress().passes("f", "not-an-ip") is False


class TestUuid:
    def test_valid(self):
        assert Uuid().passes("f", "550e8400-e29b-41d4-a716-446655440000") is True

    def test_invalid(self):
        assert Uuid().passes("f", "not-a-uuid") is False
        assert Uuid().passes("f", "550e8400") is False


class TestJson:
    def test_valid(self):
        assert Json().passes("f", '{"key": "value"}') is True
        assert Json().passes("f", "[1, 2, 3]") is True
        assert Json().passes("f", '"hello"') is True

    def test_invalid(self):
        assert Json().passes("f", "not json") is False
        assert Json().passes("f", "{bad}") is False
