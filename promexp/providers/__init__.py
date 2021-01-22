from .psutil import PSUtilProvider
from .nvidia import NVIDIAProvider
from .storage import StorageProvider
from .network import NetworkProvider

registry = [
    PSUtilProvider,
    NVIDIAProvider,
    StorageProvider,
    NetworkProvider
]
