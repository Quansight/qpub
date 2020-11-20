"""deathbeds generalized automation framework."""
__version__ = __import__("datetime").date.today().strftime("%Y.%m.%d")

from . import util
from .util import File, merge, Module, Path, task, action
from . import template, files, converters  # noqa


def main():
    from . import tasks, docs

    __import__("doit").run({**vars(tasks), **vars(docs)})
