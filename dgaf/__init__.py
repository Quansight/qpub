"""deathbeds generalized automation framework."""
__version__ = __import__("datetime").date.today().strftime("%Y.%m.%d")

from . import util
from . import base
from . import tasks
from .base import File
from . import converters  # noqa


def main():
    import typer

    def main(**kwargs):
        base.Distribution(**kwargs).main().run([])

    main.__signature__ = __import__("inspect").signature(base.Distribution)
    typer.run(main)
