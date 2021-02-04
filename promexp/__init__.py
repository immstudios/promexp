import logging

from .metrics import Metrics
from .providers import registry

class Promexp():
    def __init__(self, prefix="", tags={}, provider_settings={}, logger=None):
        self.prefix = prefix
        self.tags = tags
        self.providers = []
        self._logger = logger
        for pclass in registry:
            self.providers.append(
                pclass(
                    self,
                    provider_settings.get(pclass.name, {})
                )
            )
            if self.providers[-1].enabled:
                self.logger.info(f"Enabling {self.providers[-1].name} provider")
        self.metrics = Metrics()

    @property
    def logger(self):
        if self._logger == None:
            self._logger = logging.getLogger("promexp")
        return self._logger

    def render(self):
        for provider in self.providers:
            if provider.enabled:
                provider.collect()
        return self.metrics.render(prefix=self.prefix, **self.tags)
