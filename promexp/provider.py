from typing import TYPE_CHECKING, Any

from promexp.metrics import Metric

if TYPE_CHECKING:
    from promexp.promexp import Promexp


class BaseProvider:
    name = "base"
    exported_metrics: list[Metric] = []

    def __init__(
        self,
        parent: "Promexp",
        settings: dict[str, Any] | None = None,
    ) -> None:
        self.parent = parent
        self.enabled = settings is not None
        self.settings = settings or {}

        # Directory the host root filesystem is mounted to. Empty unless
        # promexp runs in a container. See Promexp.host_root
        self.host_root = str(self.settings.get("host_root") or "").rstrip("/")

        for metric in self.exported_metrics:
            parent.metrics.describe(metric)

    def __getitem__(self, key: str) -> Any:
        return self.settings.get(key, None)

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def disable(self) -> None:
        self.enabled = False

    def enable(self) -> None:
        self.enabled = True

    def add(self, metric_name: str, value: Any, **tags: str) -> None:
        self.parent.metrics.add(metric_name, value, **tags)

    def collect(self) -> None:
        pass
