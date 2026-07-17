from .casparcg import CasparCGProvider
from .network import NetworkProvider
from .nvidia import NVIDIAProvider
from .psutil import PSUtilProvider
from .storage import StorageProvider
from .storagespaces import StorageSpacesProvider

registry = [
    PSUtilProvider,
    NVIDIAProvider,
    StorageProvider,
    NetworkProvider,
    StorageSpacesProvider,
    CasparCGProvider,
]
