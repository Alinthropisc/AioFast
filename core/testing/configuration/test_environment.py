from __future__ import annotations

from pathlib import Path

import pytest

from core.configuration import Environment
from core.exceptions import EnvironmentError, EnvironmentKeyError


class TestEnvironmentLoad:
    def test_loads_env_file(self, env: Environment):
        assert env.string("APP_NAME") == "TestApp"
        assert env.string("APP_ENV") == "local"

    def test_loaded_files(self, env: Environment):
        assert len(env.loaded_files()) == 1

    def test_len(self, env: Environment):
        assert len(env) > 0

    def test_repr(self, env: Environment):
        r = repr(env)
        assert "Environment" in r
        assert "keys=" in r


class TestEnvironmentTypedGetters:
    def test_string(self, env: Environment):
        assert env.string("APP_NAME") == "TestApp"
        assert env.string("MISSING", "default") == "default"

    def test_bool(self, env: Environment):
        assert env.bool("BOOL_TRUE") is True
        assert env.bool("BOOL_FALSE") is False
        assert env.bool("MISSING", True) is True

    def test_int(self, env: Environment):
        assert env.int("INT_VAR") == 42
        assert env.int("MISSING", 99) == 99

    def test_float(self, env: Environment):
        assert env.float("FLOAT_VAR") == pytest.approx(3.14)
        assert env.float("MISSING", 1.5) == pytest.approx(1.5)

    def test_list(self, env: Environment):
        assert env.list("LIST_VAR") == ["a", "b", "c"]
        # assert env.list("LIST_VAR") == []
        assert env.list("MISSING") == []

    def test_dict(self, env: Environment):
        result = env.dict("JSON_VAR")
        assert result == {"key": "value"}
        assert env.dict("MISSING") == {}

    def test_json(self, env: Environment):
        result = env.json("JSON_VAR")
        assert result == {"key": "value"}

    def test_secret(self, env: Environment):
        s = env.secret("SECRET_VAR")
        assert s.get_secret_value() == "secret"
        assert "super_secret" not in str(s)

    def test_path(self, env: Environment):
        env.set("MY_PATH", "/tmp/test")
        p = env.path("MY_PATH")
        assert p == Path("/tmp/test")
        assert env.path("MISSING") is None

    def test_url(self, env: Environment):
        env.set("API_URL", "https://api.example.com/")
        assert env.url("API_URL") == "https://api.example.com"

    def test_enum(self, env: Environment):
        assert env.enum("APP_ENV", ["local", "production"]) == "local"
        assert env.enum("APP_ENV", ["production"]) is None
        assert env.enum("APP_ENV", ["production"], "fallback") == "fallback"

    def test_int_list(self, env: Environment):
        env.set("PORTS", "80,443,8080")
        assert env.int_list("PORTS") == [80, 443, 8080]


class TestEnvironmentRequire:
    def test_require_existing(self, env: Environment):
        assert env.require("APP_NAME") == "TestApp"

    def test_require_missing_raises(self, env: Environment):
        with pytest.raises(EnvironmentKeyError, match="MISSING"):
            env.require("MISSING")


class TestEnvironmentMutations:
    def test_set(self, env: Environment):
        env.set("NEW_KEY", "new_value")
        assert env.string("NEW_KEY") == "new_value"

    def test_unset(self, env: Environment):
        env.set("TEMP", "val")
        assert env.unset("TEMP") is True
        assert env.has("TEMP") is False
        assert env.unset("NONEXISTENT") is False

    def test_clear(self, env: Environment):
        env.clear()
        assert len(env) == 0

    def test_has(self, env: Environment):
        assert env.has("APP_NAME") is True
        assert env.has("NONEXISTENT") is False

    def test_contains(self, env: Environment):
        assert "APP_NAME" in env
        assert "NONEXISTENT" not in env

    def test_getitem(self, env: Environment):
        assert env["APP_NAME"] == "TestApp"


class TestEnvironmentInterpolation:
    def test_interpolation(self, env: Environment):
        assert env.string("INTERPOLATED") == "MyApp_suffix"

    def test_nested_interpolation(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("BASE=hello\nDERIVED=${BASE}_world\n")
        e = Environment(env_file=env_file, load_system_env=False, base_path=tmp_path)
        assert e.string("DERIVED") == "hello_world"


class TestEnvironmentFreeze:
    def test_freeze(self, env: Environment):
        env.freeze()
        assert env.is_frozen is True

        with pytest.raises(EnvironmentError, match="frozen"):
            env.set("X", "Y")

        with pytest.raises(EnvironmentError, match="frozen"):
            env.unset("APP_NAME")

        with pytest.raises(EnvironmentError, match="frozen"):
            env.clear()

    def test_unfreeze(self, env: Environment):
        env.freeze()
        env.unfreeze()
        env.set("X", "Y")  # should not raise
        assert env.string("X") == "Y"


class TestEnvironmentSnapshot:
    def test_snapshot_rollback(self, env: Environment):
        snap = env.snapshot()
        env.set("NEW", "value")
        assert env.has("NEW")

        env.rollback(snap)
        assert not env.has("NEW")
        assert env.string("APP_NAME") == "TestApp"


class TestEnvironmentPrefix:
    def test_prefix_filter(self, env: Environment):
        db_vars = env.prefix("DB_")
        assert "HOST" in db_vars
        assert "PORT" in db_vars
        assert "PASSWORD" in db_vars


class TestEnvironmentDump:
    def test_dump_masks_secrets(self, env: Environment):
        dumped = env.dump(mask_secrets=True)
        assert dumped["DB_PASSWORD"] == "***MASKED***"
        assert dumped["APP_KEY"] == "***MASKED***"
        assert dumped["APP_NAME"] == "TestApp"

    def test_dump_no_mask(self, env: Environment):
        dumped = env.dump(mask_secrets=False)
        assert dumped["DB_PASSWORD"] == "my_db_pass"


class TestEnvironmentGet:
    def test_get_with_type_cast(self, env: Environment):
        assert env.get("INT_VAR", 0) == 42
        assert env.get("BOOL_TRUE", False) is True
        assert env.get("FLOAT_VAR", 0.0) == pytest.approx(3.14)

    def test_callable(self, env: Environment):
        assert env("APP_NAME") == "TestApp"
        assert env("MISSING", "default") == "default"


class TestEnvironmentReload:
    def test_reload(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=original\n")
        e = Environment(env_file=env_file, load_system_env=False, base_path=tmp_path)
        assert e.string("KEY") == "original"

        env_file.write_text("KEY=updated\n")
        e.reload()
        assert e.string("KEY") == "updated"


class TestEnvironmentValidation:
    def test_validate(self, env: Environment):
        missing = env.validate(["APP_NAME", "NONEXISTENT"])
        assert missing == ["NONEXISTENT"]

    def test_assert_required_passes(self, env: Environment):
        env.assert_required(["APP_NAME", "APP_ENV"])  # should not raise

    def test_assert_required_fails(self, env: Environment):
        with pytest.raises(EnvironmentError, match="Missing"):
            env.assert_required(["APP_NAME", "DOES_NOT_EXIST"])


class TestEnvironmentEdgeCases:
    def test_export_prefix(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("export MY_VAR=exported_value\n")
        e = Environment(env_file=env_file, load_system_env=False, base_path=tmp_path)
        assert e.string("MY_VAR") == "exported_value"

    def test_quoted_values(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("DOUBLE=\"double quoted\"\nSINGLE='single quoted'\n")
        e = Environment(env_file=env_file, load_system_env=False, base_path=tmp_path)
        assert e.string("DOUBLE") == "double quoted"
        assert e.string("SINGLE") == "single quoted"

    def test_inline_comments(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value # this is a comment\n")
        e = Environment(env_file=env_file, load_system_env=False, base_path=tmp_path)
        assert e.string("KEY") == "value"

    def test_empty_file(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("")
        e = Environment(env_file=env_file, load_system_env=False, base_path=tmp_path)
        assert len(e) == 0

    def test_missing_file(self, tmp_path: Path):
        e = Environment(
            env_file=tmp_path / "nonexistent.env",
            load_system_env=False,
            base_path=tmp_path,
        )
        assert len(e) == 0
