from .psutil import PSUtilProvider
from .nvidia import NVIDIAProvider
from .storage import StorageProvider
from .network import NetworkProvider
from .storagespaces import StorageSpacesProvider
from .casparcg import CasparCGProvider

registry = [
    PSUtilProvider,
    NVIDIAProvider,
    StorageProvider,
    NetworkProvider,
    StorageSpacesProvider,
    CasparCGProvider
]
