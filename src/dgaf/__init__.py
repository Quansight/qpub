"""q(uick) p(ubishing) configures python Project and documentaton tools.

"""
__version__ = __import__("datetime").date.today().strftime("%Y.%m.%d")
#    ___    ____      _   _    ____
#   / " \ U|  _"\ uU |"|u| |U | __")u
#  | |"| |\| |_) |/ \| |\| | \|  _ \/
# /| |_| |\|  __/    | |_| |  | |_) |
# U \__\_\u|_|      <<\___/   |____/
#    \\//  ||>>_   (__) )(   _|| \\_
#   (_(__)(__)__)      (__) (__) (__)

import collections
import dataclasses
import functools
import io
import itertools

DOIT_CONFIG = dict(verbosity=2, default_tasks=[])
from .base import *
from .files import *


def load_ipython_extension(shell):
    import doit

    from . import __main__

    shell.run_line_magic("reload_ext", "doit")
    shell.user_ns.update(__main__.load_tasks("all"))


def unload_ipython_extension(shell):
    pass
