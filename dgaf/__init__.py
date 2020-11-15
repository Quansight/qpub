"""deathbeds generalized automation framework."""
__version__ = __import__("datetime").date.today().strftime("%Y.%m.%d")
from . import util
from .util import File, merge, Module, Path
from . import template


def main():
    with __import__("tingle").Markdown():
        from . import readme

    import sys

    readme.app()
    util.typer_to_doit(readme.app).run(sys.argv[1:])
