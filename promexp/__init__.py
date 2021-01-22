from .metrics import Metrics
from .providers import registry

class Promexp():
    def __init__(self, prefix="", tags={}):
        self.prefix = prefix
        self.tags = tags
        self.providers = []
        for pclass in registry:
            self.providers.append(pclass(self, {}))
        self.metrics = Metrics()

    def render(self):
        for provider in self.providers:
            if provider.enabled:
                provider.collect()
        return self.metrics.render(prefix=self.prefix, **self.tags)
