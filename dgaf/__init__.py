"""deathbeds generalized automation framework."""
__version__ = __import__("datetime").date.today().strftime("%Y.%m.%d")

from . import util
from .util import File, merge, Module, Path
from . import files, template, converters

with __import__("tingle").Markdown():
    from . import readme


def main():
    with __import__("tingle").Markdown():
        from . import readme
    readme.app()
