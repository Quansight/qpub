"""deathbeds generalized automation framework."""
__version__ = __import__("datetime").date.today().strftime("%Y.%m.%d")
import typer

app = typer.Typer()
from . import util
from .util import File, merge, Module, Path
from . import template, files, converters


def main():
    __import__("tingle").loaders.XO.extensions += [".md"]
    with __import__("tingle").loaders.XO():
        from . import readme
    cmd = typer.main.get_command(app)
    cmd.chain = True
    cmd()
