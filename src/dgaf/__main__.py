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

from . import sessions

app = typer.Typer()
nox.options.sessions = []

from .__init__ import *

# from . import sessions

task_file = pathlib.Path(__file__).parent / "__init__.py"

_add_requirements = """doit GitPython depfinder aiofiles appdirs typer
json-e pathspec flit poetry requests-cache tomlkit""".split()
_interactive_requirements = """""".split()

_PATH = typer.Option("", help="the path to configure")
_PYTHON = typer.Option("infer", help="python package backend.")
_DOCS = typer.Option("infer", help="documentation backend.")
_VENV = typer.Option(True, help="run in a virtual environment.")
_CLEAN = typer.Option(False, help="use a clean venv")
_CONDA = typer.Option(False, help="run in a conda env")
_DGAF = typer.Option("dgaf", help="the version of dgaf to install", hidden=True)
_DRYRUN = typer.Option(True, help="don't write any files.")


@app.command()
def add(
    ctx: typer.Context,
    tasks: typing.List[str],
    dir: pathlib.Path = _PATH,
    python: str = _PYTHON,
    docs: str = _DOCS,
    venv: bool = _VENV,
    dry_run: bool = _DRYRUN,
    force: bool = typer.Option(False, help="force the task execution"),
    interactive: bool = typer.Option(False, help="don't write any files."),
    clean: bool = typer.Option(False, help="use a clean venv"),
    dgaf: str = _DGAF,
):
    """add or update the project configuration."""
    if not tasks:
        # defualt tasks
        tasks = list(
            map(str, [PRECOMMITCONFIG_YML, PYPROJECT_TOML, TOC, REQUIREMENTS_TXT])
        )

    if force:
        tasks = ("-s",) + tasks

    options.python = python
    options.docs = docs
    options.interactive = interactive
    options.dgaf = dgaf

    nox.session(reuse_venv=not clean, python=None if venv else False)(sessions.add)

    nox.options.sessions += ["add"]
    options.tasks += list(map(str, tasks))


@app.command()
def develop(
    ctx: typer.Context,
    dir: pathlib.Path = typer.Option("", help="the path to configure"),
    backend: str = typer.Option("infer", help="python package backend."),
    conda: bool = typer.Option(False),
    dgaf: str = _DGAF,
):
    """install the project in development mode."""

    options.conda = conda
    options.python = backend
    options.dgaf = dgaf

    nox.session(python=False, venv_backend=[None, "conda"][conda])(sessions.develop)

    nox.options.sessions += ["develop"]
    options.tasks += ["python"]


@app.command()
def install(ctx: typer.Context, conda: bool = _CONDA):
    """install the distribution."""
    options.conda = conda

    nox.session(python=False)(sessions.install)

    nox.options.sessions += ["install"]
    options.tasks += ["python"]


@app.command(context_settings=dict(allow_extra_args=True, ignore_unknown_options=True))
def test(
    ctx: typer.Context,
    dir: pathlib.Path = typer.Option(pathlib.Path()),
    venv: bool = typer.Option(True),
    conda: bool = typer.Option(False),
    clean: bool = typer.Option(False, help="use a clean venv"),
    types: bool = typer.Option(False, help="generate type stubs"),
):
    """test the distribution."""
    options.monkeytype = types
    nox.session(
        python=None if venv else False,
        venv_backend=[None, "conda"][conda],
        reuse_venv=not clean,
    )(sessions.test)
    options.posargs += ctx.args
    nox.options.sessions += ["test"]


@app.command()
def lint(ctx: typer.Context, venv: bool = typer.Option(True)):
    """format and lint the project"""
    if venv:
        session = nox.session(reuse_venv=True)
    else:
        session = nox.session(python=False)
    session(sessions.lint)

    nox.options.sessions += ["lint"]
    options.tasks += ["lint"]


@app.command()
def docs(
    ctx: typer.Context,
    dir: pathlib.Path = pathlib.Path(),
    backend: str = typer.Option("infer"),
    venv: bool = typer.Option(True),
    clean: bool = typer.Option(False),
    pdf: bool = typer.Option(False),
    serve: bool = typer.Option(False),
    watch: bool = typer.Option(False),
    dgaf: str = _DGAF,
):
    """build the html docs"""

    if venv:
        nox.session(reuse_venv=not clean)(sessions.docs)
    else:
        nox.session(python=False)(sessions.docs)

    options.pdf = pdf
    options.docs = backend
    options.watch = watch
    options.dgaf = dgaf
    options.serve = serve

    nox.options.sessions += ["docs"]
    options.tasks += ["docs"]


@app.command()
def uninstall(
    ctx: typer.Context,
    dir: pathlib.Path = pathlib.Path(),
    proceed: bool = typer.Option(False, "--proceed", "-y"),
):
    """uninstall the project"""
    options.confirm = proceed

    nox.session(python=False)(sessions.uninstall)

    nox.options.sessions += ["uninstall"]


@app.command()
def binder():
    """bootstrap a development environment on binder."""
    nox.options.sessions = "lint develop docs test".split()
    options.tasks = "python docs lint"


def main():
    try:
        # run the typer application to configure the nox sessions
        # some commands may raise to indicate completed.
        app()
    except SystemExit as exception:
        # run the nox sessions that were configured.
        if nox.options.sessions:
            from . import sessions

            # piptions.sessions += ["add"]

            nox.options.sessions = sorted(nox.options.sessions)
            raise SystemExit(util.nox_runner(vars(sessions)))
        raise exception


if __name__ == "__main__":
    main()

# ███████╗██╗███╗   ██╗
# ██╔════╝██║████╗  ██║
# █████╗  ██║██╔██╗ ██║
# ██╔══╝  ██║██║╚██╗██║
# ██║     ██║██║ ╚████║
# ╚═╝     ╚═╝╚═╝  ╚═══╝
