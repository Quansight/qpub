"""the cli & nox session for the qpub application"""
#  ██████╗██╗     ██╗
# ██╔════╝██║     ██║
# ██║     ██║     ██║
# ██║     ██║     ██║
# ╚██████╗███████╗██║
#  ╚═════╝╚══════╝╚═╝


import typer
import nox
import pathlib

app = typer.Typer(chain=True)
init = typer.Typer(name="init")
gist = typer.Typer(name="gist")
app.add_typer(init)
nox.options.sessions = []

from .__init__ import *

task_file = pathlib.Path(__file__).parent / "__init__.py"


class Complete(Exception):
    """an exception to signify the program is complete"""


@app.command()
def add(ctx: typer.Context):
    """add something to project"""
    # i don't know what this does yet, but it is git stuff likely
    nox.options.session += ["add"]


@app.command()
def configure(
    ctx: typer.Context, lint: bool = True, python: str = "infer", venv: bool = True
):
    """write/update configuration files for a project."""
    options.python = python
    nox.options.sessions += ["configure"]
    if not venv:
        nox.session(python=False)(configure)


@app.command()
def develop(
    ctx: typer.Context,
    conda: bool = False,
):
    """develop a project"""
    __import__("nox").options.sessions += ["develop"]
    conda and nox.session(venv_backend="conda")(develop)


@app.command()
def install(ctx: typer.Context, conda: bool = False):
    """install a project"""
    nox.options.sessions += ["install"]
    conda and nox.session(venv_backend="conda")(install)


@app.command()
def build(ctx: typer.Context, conda: bool = False):
    """build a project"""
    nox.options.sessions += ["build"]
    conda and nox.session(venv_backend="conda")(build)


@app.command()
def docs(ctx: typer.Context, watch: bool = False, serve: bool = False):
    """build the documentation"""
    options.watch = watch
    options.serve = serve
    options.docs = "infer"
    nox.options.sessions += ["docs"]


@app.command()
def lint(ctx: typer.Context):
    """lint the project"""
    nox.options.sessions += ["lint"]


@app.command()
def test(ctx: typer.Context, stubs: bool = False):
    """test the project"""
    options.generate_types = stubs
    nox.options.sessions += ["test"]


@app.command()
def blog(ctx: typer.Context):
    """transform the blog to html"""
    nox.options.sessions += ["blog"]


@app.command()
def doit(ctx: typer.Context, file: pathlib.Path = ""):
    "run a file of doit tasks in a closed nox environment."
    nox.options.session += ["doit"]
    # need to pass extra arguments through the cli.


def main():
    try:
        # run the typer application to configure the nox sessions
        # some commands may raise to indicate completed.
        app()
    except SystemExit as exception:
        # run the nox sessions that were configured.
        if nox.options.sessions:
            from . import sessions

            if "configure" not in nox.options.sessions:
                nox.options.sessions.insert(0, "configure")
            raise SystemExit(sessions.nox_runner(vars(sessions)))
        raise exception


if __name__ == "__main__":
    main()
    assert (
        False
    ), "We should never have reached here, because the program will have raised."

# ███████╗██╗███╗   ██╗
# ██╔════╝██║████╗  ██║
# █████╗  ██║██╔██╗ ██║
# ██╔══╝  ██║██║╚██╗██║
# ██║     ██║██║ ╚████║
# ╚═╝     ╚═╝╚═╝  ╚═══╝
