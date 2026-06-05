from __future__ import unicode_literals

import migra._compat_pkg_resources  # noqa: F401  (ensure pkg_resources available for schemainspect)

__version__ = "1.5.2"


from .changes import Changes
from .command import do_command
from .migra import Migration
from .statements import Statements, UnsafeMigrationException

__all__ = [
    "Migration",
    "Changes",
    "Statements",
    "UnsafeMigrationException",
    "do_command",
]
