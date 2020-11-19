"""deathbeds generalized automation framework."""
__version__ = __import__("datetime").date.today().strftime("%Y.%m.%d")
import typer

app = typer.Typer()
from . import util
from .util import File, merge, Module, Path, task
from . import template, files, converters

__import__("xonsh.main").main.setup()
def main():
    from . import tasks, docs

    __import__("doit").run({**vars(tasks), **vars(docs)})
