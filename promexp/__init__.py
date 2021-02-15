import logging

from .metrics import Metrics
from .providers import registry

class Promexp():
    def __init__(self, prefix="", tags={}, provider_settings={}, logger=None):
        self.prefix = prefix
        self.tags = tags
        self.providers = {}
        self._logger = logger
        self.metrics = Metrics()
        for pclass in registry:
            self.add_provider(pclass, provider_settings.get(pclass.name, {}))

    def add_provider(self, pclass, psettings={}):
        if psettings is None:
            return False

        if pclass.name in self.providers:
            self.logger.warning(f"Duplicate provider name {pclass.name}. Skipping initialization.")
            return False

        self.providers[pclass.name] = pclass(self, psettings)

        if self.providers[pclass.name].enabled:
            self.logger.info(f"Enabling {pclass.name} provider")

    @property
    def logger(self):
        if self._logger == None:
            self._logger = logging.getLogger("promexp")
        return self._logger

    def collect(self):
        for name, provider in self.providers.items():
            if provider.enabled:
                provider.collect()

    def render(self):
        self.collect()
        return self.metrics.render(prefix=self.prefix, **self.tags)
