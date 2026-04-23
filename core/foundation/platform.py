from __future__ import annotations

import asyncio
import logging
import os
import platform
import sys
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)


class OSType(Enum):
    WINDOWS = auto()
    LINUX = auto()
    MACOS = auto()
    FREEBSD = auto()
    UNKNOWN = auto()


class ArchType(Enum):
    X86_64 = auto()
    ARM64 = auto()
    X86 = auto()
    ARM = auto()
    UNKNOWN = auto()


class LoopType(Enum):
    ASYNCIO = "asyncio"
    UVLOOP = "uvloop"
    WINLOOP = "winloop"


@dataclass(frozen=True)
class PlatformInfo:
    os_type: OSType
    os_name: str
    os_version: str
    arch: ArchType
    arch_name: str
    python_version: str
    python_implementation: str
    is_64bit: bool
    loop_type: LoopType
    loop_name: str


class Platform:
    def __init__(self) -> None:
        self._os_type: OSType = self._detect_os()
        self._arch: ArchType = self._detect_arch()
        self._loop_type: LoopType | None = None
        self._loop_configured: bool = False

    @property
    def os_type(self) -> OSType:
        return self._os_type

    @property
    def is_windows(self) -> bool:
        return self._os_type == OSType.WINDOWS

    @property
    def is_linux(self) -> bool:
        return self._os_type == OSType.LINUX

    @property
    def is_macos(self) -> bool:
        return self._os_type == OSType.MACOS

    @property
    def is_freebsd(self) -> bool:
        return self._os_type == OSType.FREEBSD

    @property
    def is_unix(self) -> bool:
        """True for Linux, macOS, FreeBSD — any POSIX-like system."""
        return self._os_type in (OSType.LINUX, OSType.MACOS, OSType.FREEBSD)

    @property
    def is_posix(self) -> bool:
        return os.name == "posix"

    @property
    def arch(self) -> ArchType:
        return self._arch

    @property
    def is_64bit(self) -> bool:
        return sys.maxsize > 2**32

    @property
    def python_version(self) -> str:
        return platform.python_version()

    @property
    def python_implementation(self) -> str:
        return platform.python_implementation()

    @property
    def loop_type(self) -> LoopType:
        if self._loop_type is None:
            self._loop_type = self._detect_best_loop()
        return self._loop_type

    def configure_event_loop(self, preferred: LoopType | None = None, *, force: bool = False) -> LoopType:

        if self._loop_configured and not force:
            logger.debug("Event loop already configured: %s", self._loop_type)
            return self._loop_type  # ty:ignore[invalid-return-type]

        if preferred is not None:
            if self._try_set_loop(preferred):
                self._loop_type = preferred
                self._loop_configured = True
                logger.info("Event loop configured: %s (preferred)", preferred.value)
                return preferred
            elif force:
                raise RuntimeError(f"Cannot configure {preferred.value} event loop — package not installed")
            else:
                logger.warning("Preferred loop %s not available, auto-detecting...", preferred.value)
        best = self._detect_best_loop()
        self._try_set_loop(best)
        self._loop_type = best
        self._loop_configured = True
        logger.info("Event loop configured: %s (auto-detected)", best.value)
        return best

    def is_loop_available(self, loop_type: LoopType) -> bool:
        """Check if a specific loop implementation is available."""
        if loop_type == LoopType.ASYNCIO:
            return True
        elif loop_type == LoopType.UVLOOP:
            return self._can_import("uvloop")
        elif loop_type == LoopType.WINLOOP:
            return self._can_import("winloop")
        return False

    def get_available_loops(self) -> list[LoopType]:
        """Get all available loop implementations."""
        return [lt for lt in LoopType if self.is_loop_available(lt)]

    @property
    def info(self) -> PlatformInfo:
        return PlatformInfo(
            os_type=self._os_type,
            os_name=platform.system(),
            os_version=platform.version(),
            arch=self._arch,
            arch_name=platform.machine(),
            python_version=self.python_version,
            python_implementation=self.python_implementation,
            is_64bit=self.is_64bit,
            loop_type=self.loop_type,
            loop_name=self.loop_type.value,
        )

    @staticmethod
    def _detect_os() -> OSType:
        system = platform.system().lower()
        if system == "windows":
            return OSType.WINDOWS
        elif system == "linux":
            return OSType.LINUX
        elif system == "darwin":
            return OSType.MACOS
        elif system == "freebsd":
            return OSType.FREEBSD
        return OSType.UNKNOWN

    @staticmethod
    def _detect_arch() -> ArchType:
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return ArchType.X86_64
        elif machine in ("aarch64", "arm64"):
            return ArchType.ARM64
        elif machine in ("i386", "i686", "x86"):
            return ArchType.X86
        elif machine.startswith("arm"):
            return ArchType.ARM
        return ArchType.UNKNOWN

    def _detect_best_loop(self) -> LoopType:
        if self.is_windows:
            if self._can_import("winloop"):
                return LoopType.WINLOOP
        else:
            if self._can_import("uvloop"):
                return LoopType.UVLOOP
        return LoopType.ASYNCIO

    def _try_set_loop(self, loop_type: LoopType) -> bool:
        try:
            if loop_type == LoopType.UVLOOP:
                import uvloop  # ty:ignore[unresolved-import]  # pyright: ignore[reportMissingImports]

                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
                return True
            elif loop_type == LoopType.WINLOOP:
                import winloop  # ty:ignore[unresolved-import]  # pyright: ignore[reportMissingImports]

                asyncio.set_event_loop_policy(winloop.EventLoopPolicy())
                return True
            elif loop_type == LoopType.ASYNCIO:
                if self.is_windows:
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                else:
                    asyncio.set_event_loop_policy(None)
                return True
        except ImportError:
            return False
        except Exception as e:
            logger.warning("Failed to set %s loop: %s", loop_type.value, e)
            return False
        return False

    @staticmethod
    def _can_import(module_name: str) -> bool:
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False

    def __repr__(self) -> str:
        return f"<Platform os={self._os_type.name} arch={self._arch.name} loop={self.loop_type.value} py={self.python_version}>"
