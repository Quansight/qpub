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
import sys


app = typer.Typer(name="add")
run = typer.Typer(name="run", chain=True)
app.add_typer(run)
nox.options.sessions = []

from .__init__ import *

task_file = pathlib.Path(__file__).parent / "__init__.py"


class Complete(Exception):
    """an exception to signify the program is complete"""


@app.command()
def add(
    ctx: typer.Context,
    tasks: typing.List[str],
    dir: pathlib.Path = typer.Option("", help="the path to configure"),
    venv: bool = typer.Option(True, help="run in a virtual environment."),
    pep517: bool = typer.Option(True, help="configure object in pyproject.toml"),
    dry_run: bool = typer.Option(True, help="don't write any files."),
    bootstrap: bool = typer.Option(
        False, hidden=True, help="bootstrap the installation of dgaf"
    ),
):
    """add something to project


    uses doit targets as commands for executing tasks meaning we add
    operations as aliases or file names.
    """
    # i don't know what this does yet, but it is git stuff likely
    if not tasks:
        tasks = "lint docs python".split()

    @nox.session(reuse_venv=True, python=None if venv else False)
    def add(session):
        # session.install(*"pip install --upgrade pip".split())
        session.install(f"""{bootstrap and "." or "dgaf"}[configure]""")
        if "build" in tasks:
            if pep517:
                session.install("pep517")
            else:
                session.install(*"setuptools wheel".split(), "doit")
        if interactive:
            session.install(f"""{bootstrap and "." or "dgaf"}[interactive]""")
            session.run(
                *"python -m dgaf.interactive".split(), *tasks, env=options.dump()
            )
        else:
            session.run(*"python -m dgaf.tasks".split(), *tasks, env=options.dump())

    util.nox_runner({"add": add}, _raise=True)


@run.command()
def develop(
    ctx: typer.Context,
    dir: pathlib.Path = typer.Option("", help="the path to configure"),
):
    # based on the build system, figure out how to develop the project.

    @nox.session(python=False)
    def develop(session):
        session.run(*"pip install -e .".split(), env=options.dump())


@run.command()
def install(ctx: typer.Context):
    """install the package."""

    @nox.session(python=False)
    def install(session):
        session.run(*"pip install .".split(), env=options.dump())


@run.command()
def test(ctx: typer.Context):
    """test the project"""


@run.command()
def lint(ctx: typer.Context):
    """run a linter"""


@run.command()
def html(ctx: typer.Context):
    ...


@run.command()
def pdf(ctx: typer.Context):
    ...


if __name__ == "__main__":
    app()


@app.command()
def configure(
    ctx: typer.Context,
    dir: pathlib.Path = None,
    lint: bool = True,
    python: str = "infer",
    venv: bool = True,
):
    """write/update configuration files for a project."""
    options.python = python
    nox.options.sessions += ["configure"]
    if dir is not None:
        import os

        os.chdir(dir)
    if not venv:
        from .sessions import configure

        nox.session(python=False, reuse_venv=None)(configure)


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
            raise SystemExit(util.nox_runner(vars(sessions)))
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
