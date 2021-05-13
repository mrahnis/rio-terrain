import logging

from rio_terrain.core.terrain import *
from rio_terrain.core.statistics import *
from rio_terrain.core.windowing import *
from ._version import get_versions


__author__ = "Mike Rahnis"
__version__ = get_versions()['version']
del get_versions

logger = logging.getLogger(__name__)
