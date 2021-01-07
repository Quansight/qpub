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

from .dodo import PYPROJECT_TOML, options, PRECOMMITCONFIG_YML, TOC, REQUIREMENTS_TXT

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

    nox.session(reuse_venv=not clean, python=None if venv else False)(noxfile.add)

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

    nox.session(python=False, venv_backend=[None, "conda"][conda])(noxfile.develop)

    nox.options.sessions += ["develop"]
    options.tasks += ["python"]


@app.command()
def install(ctx: typer.Context, conda: bool = _CONDA):
    """install the distribution."""
    options.conda = conda

    nox.session(python=False)(noxfile.install)

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
    )(noxfile.test)
    options.posargs += ctx.args
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
        if nox.options.sessions:
            from . import noxfile

            # piptions.sessions += ["add"]

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
