from pkg_resources import get_distribution

from clients import *
from exceptions import *

__version__ = get_distribution('py-heimdallr-client').version
