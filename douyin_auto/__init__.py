# douyin-auto package
from .douyin import Douyin

# Load positions configuration
try:
    from .positions import POSITIONS
except ImportError:
    POSITIONS = {}

VERSION = "0.1.0"

__all__ = ["Douyin", "VERSION", "POSITIONS"]
