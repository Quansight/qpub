"""deathbeds generalized automation framework."""
__version__ = __import__("datetime").date.today().strftime("%Y.%m.%d")

from . import util
from . import base
from . import tasks
from .base import File
from .util import task, merge
from . import converters  # noqa


def main():
    def main(**kwargs):
        base.Distribution(**kwargs).main().run([])

    main.__signature__ = __import__("inspect").signature(base.Distribution)
    __import__("typer").run(main)
