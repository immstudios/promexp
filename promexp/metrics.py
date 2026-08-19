__all__ = ["FrozenDict", "Metric", "Metrics"]

import collections.abc
from typing import Any, NamedTuple


class FrozenDict(collections.abc.Mapping):
    dict_cls = dict

    def __init__(self, *args, **kwargs):
        self._dict = self.dict_cls(*args, **kwargs)
        self._hash = None

    def dict(self):
        return self._dict

    def __getitem__(self, key):
        return self._dict[key]

    def __contains__(self, key):
        return key in self._dict

    def copy(self, **add_or_replace):
        return self.__class__(self, **add_or_replace)

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self._dict!r}>"

    def __hash__(self):
        if self._hash is None:
            h = 0
            for key, value in self._dict.items():
                h ^= hash((key, value))
            self._hash = h
        return self._hash


class Metric(NamedTuple):
    """Description of a metric exported by a provider.

    Metric names follow the Prometheus naming conventions: a base unit
    suffix (`_bytes`, `_seconds`, `_celsius`, ...) and, for counters,
    a `_total` suffix after it.
    """

    name: str
    type: str = "gauge"
    description: str = ""


def escape(value: str, quotes: bool = False) -> str:
    result = value.replace("\\", "\\\\").replace("\n", "\\n")
    if quotes:
        result = result.replace('"', '\\"')
    return result


class Metrics:
    def __init__(self):
        self.data = {}
        self.descriptions: dict[str, Metric] = {}

    def describe(self, metric: Metric) -> None:
        """Store the type and the description of a metric"""
        self.descriptions[metric.name] = metric

    def add(self, metric_name: str, value: float, **tags) -> bool:
        """Add a metric to the pool"""
        if type(value) not in [int, float]:
            return False
        key = (metric_name, FrozenDict(**tags))
        self.data[key] = value
        return True

    def dump(self):
        """Returns json-serializable list of the stored metrics pool"""
        return [[key[0], key[1].dict(), value] for key, value in self.data.items()]

    def load(self, data):
        """Loads data from a list created previously using dump method"""
        for name, tags, value in data:
            self.add(name, value, **tags)

    def render(self, prefix: str = "", **kwargs):
        """Returns metrics in Prometheus format"""
        if prefix:
            prefix += "_"

        # Samples of one metric must be grouped together and preceded
        # by the HELP and TYPE comments of the metric.

        families: dict[str, list[tuple[dict[str, Any], float]]] = {}
        for (name, tags), value in self.data.items():
            families.setdefault(name, []).append((tags.dict(), value))

        result = ""
        for name, samples in families.items():
            metric = self.descriptions.get(name)
            if metric is not None:
                if metric.description:
                    result += f"# HELP {prefix}{name} {escape(metric.description)}\n"
                result += f"# TYPE {prefix}{name} {metric.type}\n"

            for tags, value in samples:
                tstring = ",".join(
                    f'{k}="{escape(str(v), quotes=True)}"'
                    for k, v in {**tags, **kwargs}.items()
                )
                if tstring:
                    tstring = f"{{{tstring}}}"
                result += f"{prefix}{name}{tstring} {value}\n"
        return result
