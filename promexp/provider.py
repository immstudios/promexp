class BaseProvider():
    name = "base"

    def __init__(self, parent, settings):
        self.parent = parent
        self.logger = parent.logger
        self.enabled = settings is not None
        if type(settings) == dict:
            self.settings = settings
        else:
            self.logger.warning(f"Incorrect settings for {self.name} provider. Ignoring")
            self.settings = {}

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



