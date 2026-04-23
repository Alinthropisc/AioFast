import platform as stdlib_platform
from unittest.mock import patch

import pytest

from core.foundation import ArchType, LoopType, OSType, Platform, PlatformInfo


class TestPlatformDetection:
    def test_os_type_detected(self, platform_obj):
        assert platform_obj.os_type in OSType

    def test_arch_detected(self, platform_obj):
        assert platform_obj.arch in ArchType

    def test_is_64bit(self, platform_obj):
        assert isinstance(platform_obj.is_64bit, bool)

    def test_python_version(self, platform_obj):
        assert platform_obj.python_version == stdlib_platform.python_version()

    def test_python_implementation(self, platform_obj):
        assert platform_obj.python_implementation == stdlib_platform.python_implementation()


class TestPlatformOS:
    def test_os_properties_are_bool(self, platform_obj):
        assert isinstance(platform_obj.is_windows, bool)
        assert isinstance(platform_obj.is_linux, bool)
        assert isinstance(platform_obj.is_macos, bool)
        assert isinstance(platform_obj.is_freebsd, bool)
        assert isinstance(platform_obj.is_unix, bool)
        assert isinstance(platform_obj.is_posix, bool)

    def test_mutual_exclusivity(self, platform_obj):
        """Only one specific OS should be True (or UNKNOWN none)."""
        specific = [
            platform_obj.is_windows,
            platform_obj.is_linux,
            platform_obj.is_macos,
            platform_obj.is_freebsd,
        ]
        true_count = sum(specific)
        assert true_count <= 1

    @patch("platform.system", return_value="Windows")
    def test_detect_windows(self, mock):
        p = Platform()
        assert p.os_type == OSType.WINDOWS
        assert p.is_windows
        assert not p.is_unix

    @patch("platform.system", return_value="Linux")
    def test_detect_linux(self, mock):
        p = Platform()
        assert p.os_type == OSType.LINUX
        assert p.is_linux
        assert p.is_unix

    @patch("platform.system", return_value="Darwin")
    def test_detect_macos(self, mock):
        p = Platform()
        assert p.os_type == OSType.MACOS
        assert p.is_macos
        assert p.is_unix

    @patch("platform.system", return_value="FreeBSD")
    def test_detect_freebsd(self, mock):
        p = Platform()
        assert p.os_type == OSType.FREEBSD
        assert p.is_freebsd
        assert p.is_unix

    @patch("platform.system", return_value="Solaris")
    def test_detect_unknown(self, mock):
        p = Platform()
        assert p.os_type == OSType.UNKNOWN


class TestPlatformArch:
    @patch("platform.machine", return_value="x86_64")
    def test_detect_x86_64(self, mock):
        p = Platform()
        assert p.arch == ArchType.X86_64

    @patch("platform.machine", return_value="amd64")
    def test_detect_amd64(self, mock):
        p = Platform()
        assert p.arch == ArchType.X86_64

    @patch("platform.machine", return_value="aarch64")
    def test_detect_arm64(self, mock):
        p = Platform()
        assert p.arch == ArchType.ARM64

    @patch("platform.machine", return_value="i686")
    def test_detect_x86(self, mock):
        p = Platform()
        assert p.arch == ArchType.X86

    @patch("platform.machine", return_value="armv7l")
    def test_detect_arm(self, mock):
        p = Platform()
        assert p.arch == ArchType.ARM

    @patch("platform.machine", return_value="sparc")
    def test_detect_unknown_arch(self, mock):
        p = Platform()
        assert p.arch == ArchType.UNKNOWN


class TestPlatformEventLoop:
    def test_asyncio_always_available(self, platform_obj):
        assert platform_obj.is_loop_available(LoopType.ASYNCIO)

    def test_get_available_loops(self, platform_obj):
        loops = platform_obj.get_available_loops()
        assert LoopType.ASYNCIO in loops

    def test_configure_default(self, platform_obj):
        result = platform_obj.configure_event_loop()
        assert result in LoopType

    def test_configure_asyncio_explicit(self, platform_obj):
        result = platform_obj.configure_event_loop(LoopType.ASYNCIO)
        assert result == LoopType.ASYNCIO

    def test_configure_force_unavailable_raises(self, platform_obj):
        # This test works if uvloop is NOT installed on Windows
        # or winloop is NOT installed on Linux
        if platform_obj.is_windows and not platform_obj.is_loop_available(LoopType.UVLOOP):
            with pytest.raises(RuntimeError):
                platform_obj.configure_event_loop(LoopType.UVLOOP, force=True)
        elif not platform_obj.is_windows and not platform_obj.is_loop_available(LoopType.WINLOOP):
            with pytest.raises(RuntimeError):
                platform_obj.configure_event_loop(LoopType.WINLOOP, force=True)

    def test_configure_idempotent(self, platform_obj):
        first = platform_obj.configure_event_loop()
        second = platform_obj.configure_event_loop()
        assert first == second

    @patch("platform.system", return_value="Linux")
    def test_best_loop_linux_with_uvloop(self, mock_sys):
        with patch.object(Platform, "_can_import", return_value=True):
            p = Platform()
            best = p._detect_best_loop()
            assert best == LoopType.UVLOOP

    @patch("platform.system", return_value="Linux")
    def test_best_loop_linux_without_uvloop(self, mock_sys):
        with patch.object(Platform, "_can_import", return_value=False):
            p = Platform()
            best = p._detect_best_loop()
            assert best == LoopType.ASYNCIO

    @patch("platform.system", return_value="Windows")
    def test_best_loop_windows_with_winloop(self, mock_sys):
        with patch.object(Platform, "_can_import", return_value=True):
            p = Platform()
            best = p._detect_best_loop()
            assert best == LoopType.WINLOOP

    @patch("platform.system", return_value="Windows")
    def test_best_loop_windows_without_winloop(self, mock_sys):
        with patch.object(Platform, "_can_import", return_value=False):
            p = Platform()
            best = p._detect_best_loop()
            assert best == LoopType.ASYNCIO


class TestPlatformInfo:
    def test_info_snapshot(self, platform_obj):
        info = platform_obj.info
        assert isinstance(info, PlatformInfo)
        assert info.os_name
        assert info.python_version
        assert info.os_type in OSType
        assert info.arch in ArchType
        assert info.loop_type in LoopType

    def test_info_frozen(self, platform_obj):
        info = platform_obj.info
        with pytest.raises(AttributeError):
            info.os_type = OSType.WINDOWS


class TestPlatformRepr:
    def test_repr(self, platform_obj):
        r = repr(platform_obj)
        assert "Platform" in r
        assert "os=" in r
        assert "loop=" in r
        assert "py=" in r
