import collections.abc

class frozendict(collections.abc.Mapping):
    dict_cls = dict

    def __init__(self, *args, **kwargs):
        self._dict = self.dict_cls(*args, **kwargs)
        self._hash = None

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


class Metrics():
    def __init__(self):
        self.data = {}

    def add(self, metric_name:str, value:float, **tags) -> bool:
        """Add a metric to the pool"""
        if type(value) not in [int, float]:
            return False
        key = (metric_name, frozendict(**tags))
        self.data[key] = value
        return True

    def dump(self):
        """Returns json-serializable list of the stored metrics pool"""
        return [[key[0], key[1]._dict, value] for key, value in self.data.items()]

    def load(self, data):
        """Loads data from a list created previously using dump method"""
        for name, tags, value in data:
            self.add(name, value, **tags)

    def render(self, prefix:str="", **kwargs):
        """Returns metrics in Prometheus format"""
        if prefix:
            prefix += "_"
        result = ""
        for key, value in self.data.items():
            name, tags = key
            tstring = ", ".join(f"{k}=\"{v}\"" for k, v in {**tags._dict, **kwargs}.items())
            result += f"{prefix}{name}{{{tstring}}} {value}\n"
        return result

