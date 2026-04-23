import pytest

from core.foundation import Container


class TestContextualBinding:
    @pytest.mark.asyncio
    async def test_contextual_gives_different_implementations(self):
        class Filesystem:
            name: str = "base"

        class S3Filesystem(Filesystem):
            name = "s3"

        class LocalFilesystem(Filesystem):
            name = "local"

        class PhotoController:
            def __init__(self, fs: Filesystem):
                self.fs = fs

        class VideoController:
            def __init__(self, fs: Filesystem):
                self.fs = fs

        container = Container()
        container.bind(Filesystem, LocalFilesystem)

        container.when(PhotoController).needs(Filesystem).give(S3Filesystem)

        photo = await container.make(PhotoController)
        video = await container.make(VideoController)

        assert photo.fs.name == "s3"
        assert video.fs.name == "local"

        await container.close()

    @pytest.mark.asyncio
    async def test_contextual_with_instance(self):
        class Config:
            def __init__(self, dsn: str = "default"):
                self.dsn = dsn

        class ServiceA:
            def __init__(self, config: Config):
                self.config = config

        special_config = Config(dsn="special")

        container = Container()
        container.bind(Config)
        container.when(ServiceA).needs(Config).give(special_config)

        svc = await container.make(ServiceA)
        assert svc.config.dsn == "special"

        await container.close()
