import logging

from rio_terrain.core.terrain import *
from rio_terrain.core.statistics import *
from rio_terrain.core.windowing import *

from ._version import get_versions

__version__ = get_versions()['version']
del get_versions

__author__ = "Mike Rahnis"

logger = logging.getLogger(__name__)
