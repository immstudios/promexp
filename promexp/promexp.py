from typing import Any

from .logger import logger
from .metrics import Metrics
from .providers import registry


class Promexp:
    def __init__(
        self,
        prefix: str = "",
        tags: dict[str, Any] | None = None,
        provider_settings: dict[str, Any] | None = None,
        host_root: str = "",
    ):
        if provider_settings is None:
            provider_settings = {}
        if tags is None:
            tags = {}

        self.prefix = prefix
        self.tags = tags
        self.providers = {}
        self.metrics = Metrics()

        # When promexp runs in a container, host_root is the directory the
        # host filesystems are bind mounted to. Providers use it to report
        # the host state instead of the container state.
        self.host_root = host_root.rstrip("/")

        for pclass in registry:
            psettings = provider_settings.get(pclass.name, {})
            if self.host_root:
                psettings = {"host_root": self.host_root, **psettings}
            self.add_provider(pclass, psettings)

    def add_provider(self, pclass, psettings=None):
        if psettings is None:
            psettings = {}
        if psettings is None:
            return False

        if pclass.name in self.providers:
            logger.warning(
                f"Duplicate provider name {pclass.name}. Skipping initialization."
            )
            return False

        self.providers[pclass.name] = pclass(self, psettings)

        if self.providers[pclass.name].enabled:
            logger.info(f"Enabling {pclass.name} provider")
        return None

    def collect(self):
        for provider in self.providers.values():
            if provider.enabled:
                provider.collect()

    def render(self):
        self.collect()
        return self.metrics.render(prefix=self.prefix, **self.tags)
