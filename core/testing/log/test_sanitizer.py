from __future__ import annotations

from core.log import Sanitizer


class TestSanitizerKeys:
    def test_masks_password(self):
        s = Sanitizer()
        result = s.clean("user login password=secret123")
        assert "secret123" not in result
        assert "******" in result

    def test_masks_token(self):
        s = Sanitizer()
        result = s.clean("auth token=eyJhbGciOiJ")
        assert "eyJhbGciOiJ" not in result

    def test_masks_api_key(self):
        s = Sanitizer()
        result = s.clean("api_key=sk_live_12345")
        assert "sk_live_12345" not in result

    def test_custom_keys(self):
        s = Sanitizer(use_defaults=False)
        s.add_keys("my_secret")
        result = s.clean("my_secret=hidden_value")
        assert "hidden_value" not in result
        # Default keys NOT masked
        result2 = s.clean("password=visible")
        assert "visible" in result2

    def test_case_insensitive(self):
        s = Sanitizer()
        result = s.clean("PASSWORD=secret")
        assert "secret" not in result


class TestSanitizerPatterns:
    def test_credit_card(self):
        s = Sanitizer()
        result = s.clean("card: 4111-1111-1111-1111")
        assert "4111" not in result
        assert "****" in result

    def test_bearer_token(self):
        s = Sanitizer()
        result = s.clean("Authorization: Bearer eyJtoken123")
        assert "eyJtoken123" not in result
        assert "Bearer" in result

    def test_email_masking(self):
        s = Sanitizer()
        result = s.clean("email is john.doe@example.com")
        assert "john.doe@example.com" not in result
        assert "@example.com" in result  # domain visible

    def test_custom_pattern(self):
        s = Sanitizer(use_defaults=False)
        s.add_pattern(r"SSN:\s*\d{3}-\d{2}-\d{4}", "SSN: ***-**-****")
        result = s.clean("SSN: 123-45-6789")
        assert "123-45-6789" not in result
        assert "***-**-****" in result


class TestSanitizerDict:
    def test_cleans_dict(self):
        s = Sanitizer()
        data = {
            "username": "john",
            "password": "secret",
            "token": "abc123",
        }
        cleaned = s.clean_dict(data)
        assert cleaned["username"] == "john"
        assert cleaned["password"] == "******"
        assert cleaned["token"] == "******"

    def test_nested_dict(self):
        s = Sanitizer()
        data = {
            "user": {
                "name": "John",
                "credentials": {
                    "password": "secret",
                },
            },
        }
        cleaned = s.clean_dict(data)
        assert cleaned["user"]["credentials"]["password"] == "******"
        assert cleaned["user"]["name"] == "John"

    def test_list_in_dict(self):
        s = Sanitizer()
        data = {
            "items": [
                {"password": "a"},
                {"password": "b"},
            ],
        }
        cleaned = s.clean_dict(data)
        assert cleaned["items"][0]["password"] == "******"
        assert cleaned["items"][1]["password"] == "******"


class TestSanitizerToggle:
    def test_disable(self):
        s = Sanitizer()
        s.disable()
        result = s.clean("password=visible")
        assert "visible" in result

    def test_enable(self):
        s = Sanitizer()
        s.disable()
        s.enable()
        result = s.clean("password=hidden")
        assert "hidden" not in result


class TestSanitizerPatcher:
    def test_patcher_cleans_record(self):
        s = Sanitizer()
        record = {"message": "login password=secret123"}
        s.patcher(record)
        assert "secret123" not in record["message"]
