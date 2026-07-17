__all__ = ["registry"]

from .casparcg import CasparCGProvider
from .network import NetworkProvider
from .nvidia import NVIDIAProvider
from .psutil import PSUtilProvider
from .storage import StorageProvider

registry = [
    PSUtilProvider,
    NVIDIAProvider,
    StorageProvider,
    NetworkProvider,
    CasparCGProvider,
]
