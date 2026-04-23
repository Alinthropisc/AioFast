from __future__ import annotations

from core.auth.mfa import TOTP, BackupCodes, MFAManager


class TestTOTP:
    def test_generate_and_verify(self):
        totp = TOTP()
        secret = totp.generate_secret()
        code = totp.generate_code(secret)
        assert totp.verify(secret, code)

    def test_wrong_code(self):
        totp = TOTP()
        secret = totp.generate_secret()
        assert not totp.verify(secret, "000000")

    def test_provisioning_uri(self):
        totp = TOTP()
        secret = totp.generate_secret()
        uri = totp.provisioning_uri(secret, "user@app.com", "MyApp")
        assert uri.startswith("otpauth://totp/")
        assert "MyApp" in uri


class TestBackupCodes:
    def test_generate(self):
        bc = BackupCodes()
        codes = bc.generate(10)
        assert len(codes) == 10

    def test_verify_and_consume(self):
        bc = BackupCodes()
        codes = bc.generate(5)
        hashed = bc.hash_codes(codes)

        valid, remaining = bc.verify(codes[0], hashed)
        assert valid is True
        assert len(remaining) == 4

        valid2, _ = bc.verify(codes[0], remaining)
        assert valid2 is False


class TestMFAManager:
    def test_setup_and_confirm(self):
        mfa = MFAManager()
        secret = mfa.setup("user_1")
        assert secret

        totp = TOTP()
        code = totp.generate_code(secret)
        assert mfa.confirm_setup("user_1", code)
        assert mfa.is_enabled("user_1")

    def test_verify(self):
        mfa = MFAManager()
        secret = mfa.setup("user_1")
        totp = TOTP()
        code = totp.generate_code(secret)
        mfa.confirm_setup("user_1", code)

        new_code = totp.generate_code(secret)
        assert mfa.verify("user_1", new_code)

    def test_backup_codes(self):
        mfa = MFAManager()
        mfa.setup("user_1")
        codes = mfa.get_backup_codes("user_1")
        assert codes and len(codes) > 0

        assert mfa.verify_backup("user_1", codes[0])
        assert not mfa.verify_backup("user_1", codes[0])

    def test_disable(self):
        mfa = MFAManager()
        mfa.setup("user_1")
        mfa.disable("user_1")
        assert not mfa.is_enabled("user_1")
