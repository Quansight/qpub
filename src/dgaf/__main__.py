"""the cli & nox session for the qpub application"""
#  ██████╗██╗     ██╗
# ██╔════╝██║     ██║
# ██║     ██║     ██║
# ██║     ██║     ██║
# ╚██████╗███████╗██║
#  ╚═════╝╚══════╝╚═╝


import typer
import typing
import nox
import pathlib
import sys

from . import noxfile

app = typer.Typer()
nox.options.sessions = []

from .dodo import (
    PYPROJECT_TOML,
    options,
    PRECOMMITCONFIG_YML,
    TOC,
    REQUIREMENTS_TXT,
    ENVIRONMENT_YAML,
)

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


@app.command(context_settings=dict(allow_extra_args=True, ignore_unknown_options=True))
def add(
    ctx: typer.Context,
    dir: pathlib.Path = _PATH,
    python: str = _PYTHON,
    docs: str = _DOCS,
    venv: bool = _VENV,
    watch: bool = typer.Option(False),
    force: bool = typer.Option(False, help="force the task execution"),
    interactive: bool = typer.Option(False, help="don't write any files."),
    clean: bool = typer.Option(False, help="use a clean venv"),
    dgaf: str = _DGAF,
):
    """add or update the project configuration."""
    tasks = ctx.args
    if not tasks:
        # defualt tasks
        tasks = list(
            map(str, [PRECOMMITCONFIG_YML, PYPROJECT_TOML, TOC, REQUIREMENTS_TXT])
        )
        if nox.options.default_venv_backend == "conda":
            tasks += [str(ENVIRONMENT_YAML)]

    if force:
        tasks = ("-s",) + tasks

    if watch:
        tasks = ("auto",) + tasks

    options.python = python
    options.docs = docs

    nox.session(reuse_venv=not clean, python=None if venv else False)(noxfile.tasks)

    nox.options.sessions += ["tasks"]
    options.tasks += list(map(str, tasks))


@app.command(context_settings=dict(allow_extra_args=True, ignore_unknown_options=True))
def tasks(
    ctx: typer.Context,
    venv: bool = _VENV,
    clean: bool = typer.Option(False, help="use a clean venv"),
):
    """add or update the project configuration."""
    nox.session(reuse_venv=not clean, python=None if venv else False)(noxfile.tasks)

    nox.options.sessions += ["tasks"]
    options.tasks += ctx.args


@app.command(context_settings=dict(allow_extra_args=True, ignore_unknown_options=True))
def sessions(
    ctx: typer.Context,
):
    """add or update the project configuration."""
    options.posargs += ctx.args


@app.command()
def install(
    ctx: typer.Context,
    dir: pathlib.Path = typer.Option("", help="the path to configure"),
    conda: bool = typer.Option(False),
    backend: str = _PYTHON,
    dev: bool = typer.Option(True),
    pip: bool = typer.Option(False),
):
    """install the distribution."""
    options.python_backend = backend
    options.conda = conda
    options.pip = pip
    options.dev = dev

    nox.session(python=False)(noxfile.install)

    nox.options.sessions += ["install"]


@app.command(context_settings=dict(allow_extra_args=True, ignore_unknown_options=True))
def test(
    ctx: typer.Context,
    dir: pathlib.Path = typer.Option(pathlib.Path()),
    venv: bool = typer.Option(True),
    conda: bool = typer.Option(False),
    clean: bool = typer.Option(False, help="use a clean venv"),
    types: bool = typer.Option(False, help="generate type stubs"),
    dev: bool = typer.Option(True),
    pip: bool = typer.Option(False),
    install: bool = typer.Option(True),
):
    """test the distribution."""
    options.monkeytype = types
    nox.session(
        python=None if venv else False,
        reuse_venv=not clean,
    )(noxfile.test)
    options.posargs += ctx.args
    options.pip = pip
    options.dev = dev
    options.conda = conda
    options.install = install

    nox.options.sessions += ["test"]


@app.command()
def lint(ctx: typer.Context, venv: bool = typer.Option(True)):
    """format and lint the project"""
    if venv:
        session = nox.session(reuse_venv=True)
    else:
        session = nox.session(python=False)
    session(noxfile.lint)

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
        nox.session(reuse_venv=not clean)(noxfile.docs)
    else:
        nox.session(python=False)(noxfile.docs)

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

    nox.session(python=False)(noxfile.uninstall)

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
        if nox.options.sessions or options.tasks:
            from . import noxfile

            nox.options.sessions = sorted(nox.options.sessions)
            raise SystemExit(nox_runner(vars(noxfile)))
        raise exception


def nox_runner(module, _raise=True):
    """a wrapped nox runner specifically for qpub.

    it works off a module loaded into the namespace already
    rather than a static file.
    """

    import sys, nox

    argv = sys.argv
    sys.argv = [__file__]
    ns = nox._options.options.parse_args()
    sys.argv = argv
    # run the tasks ourselves to avoid switching directories

    nox.tasks.merge_noxfile_options(module, ns)
    manifest = nox.tasks.discover_manifest(module, ns)
    nox.tasks.filter_manifest(manifest, ns)
    nox.tasks.verify_manifest_nonempty(manifest, ns)
    results = nox.tasks.run_manifest(manifest, ns)
    nox.tasks.print_summary(results, ns)
    nox.tasks.create_report(results, ns)

    object = nox.tasks.final_reduce(results, ns)
    if _raise:
        raise sys.exit(object)
    return object


if __name__ == "__main__":
    main()

# ███████╗██╗███╗   ██╗
# ██╔════╝██║████╗  ██║
# █████╗  ██║██╔██╗ ██║
# ██╔══╝  ██║██║╚██╗██║
# ██║     ██║██║ ╚████║
# ╚═╝     ╚═╝╚═╝  ╚═══╝
