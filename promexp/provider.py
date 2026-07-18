from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from promexp.promexp import Promexp


class BaseProvider:
    name = "base"

    def __init__(
        self,
        parent: "Promexp",
        settings: dict[str, Any] | None = None,
    ) -> None:
        self.parent = parent
        self.enabled = settings is not None
        self.settings = settings or {}

    def __getitem__(self, key):
        return self.settings.get(key, None)

    def get(self, key, default):
        return self.settings.get(key, default)

    def disable(self):
        self.enabled = False

    def enable(self):
        self.enabled = True

    def add(self, metric_name, value, **tags):
        self.parent.metrics.add(metric_name, value, **tags)

    def collect(self):
        pass
