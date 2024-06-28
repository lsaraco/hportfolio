"""my_project - Brief description."""

import importlib.metadata

__maintainer__ = "Leandro Saraco"
__email__ = "leandrosaraco@gmail.com"
__status__ = "Development"

__author__ = "Leandro Saraco"
__copyright__ = __author__
__license__ = "GPL3.0"

__all__ = []

# Semantic release versioning
try:
    __version__ = importlib.metadata.version(__package__)
except importlib.metadata.PackageNotFoundError:
    __version__ = ""

__version__ = "1.0"
